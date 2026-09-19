r"""Pre-Wave-4 live probe for Ling Q6 slot/cache orchestration.

This script starts an isolated llama-server on port 5899. It never touches
llama-swap or the production config. One server variant runs at a time, with
RAM/VRAM/temperature guards and deterministic cleanup.

Default run (np=2, then np=4):
  odysseus\venv\Scripts\python.exe scripts\preflight_onda4.py

Static/self-test only:
  odysseus\venv\Scripts\python.exe scripts\preflight_onda4.py --self-test
"""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


ROOT = Path(r"D:\assistenteeee")
DEFAULT_SERVER = ROOT / "llama-cuda124-new" / "llama-server.exe"
DEFAULT_MODEL = ROOT / "models" / "Ling-3.0-tiny-Q6_K.gguf"
DEFAULT_RESULTS = ROOT / "ricerche" / "opt-1080" / "misure" / "pre4"
DEFAULT_SLOT_DIR = DEFAULT_RESULTS / "slots"
PRODUCTION_CONFIG = ROOT / "llama-swap" / "config.yaml"
DEFAULT_PORT = 5899


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_phys", ctypes.c_ulonglong),
        ("avail_phys", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("avail_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("avail_virtual", ctypes.c_ulonglong),
        ("avail_extended_virtual", ctypes.c_ulonglong),
    ]


def host_memory() -> dict[str, float]:
    status = _MemoryStatus()
    status.length = ctypes.sizeof(_MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    gib = 1024**3
    return {
        "ram_total_gib": round(status.total_phys / gib, 3),
        "ram_available_gib": round(status.avail_phys / gib, 3),
        "page_available_gib": round(status.avail_page_file / gib, 3),
    }


def gpu_snapshot() -> dict[str, float | str]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total,memory.used,memory.free,temperature.gpu,pstate",
        "--format=csv,noheader,nounits",
    ]
    raw = subprocess.check_output(command, text=True, encoding="utf-8").strip()
    fields = [item.strip() for item in raw.split(",")]
    if len(fields) != 7:
        raise RuntimeError(f"unexpected nvidia-smi output: {raw}")
    return {
        "gpu": fields[0],
        "driver_version": fields[1],
        "vram_total_mib": float(fields[2]),
        "vram_used_mib": float(fields[3]),
        "vram_free_mib": float(fields[4]),
        "temperature_c": float(fields[5]),
        "pstate": fields[6],
    }


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _json_request(method: str, url: str, payload: dict | None = None, timeout: int = 300):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def _wait_ready(base: str, proc: subprocess.Popen, timeout_s: int = 360) -> None:
    deadline = time.monotonic() + timeout_s
    next_beat = 0.0
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited during startup: {proc.returncode}")
        now = time.monotonic()
        if now >= next_beat:
            snap = gpu_snapshot()
            print(
                f"heartbeat startup: temp={snap['temperature_c']:.0f}C "
                f"free_vram={snap['vram_free_mib']:.0f}MiB",
                flush=True,
            )
            if float(snap["temperature_c"]) >= 91:
                raise RuntimeError("thermal guard during startup (>=91C)")
            next_beat = now + 10
        try:
            state = _json_request("GET", base + "/health", timeout=2)
            if state.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError("llama-server startup timeout")


def _stop_process(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )


def _erase(base: str, slot: int) -> dict:
    return _json_request("POST", f"{base}/slots/{slot}?action=erase", {}, timeout=60)


def _completion(base: str, prompt: str, slot: int | None, *, session_id: str | None = None) -> dict:
    payload: dict[str, object] = {
        "prompt": prompt,
        "n_predict": 0,
        "cache_prompt": True,
        "temperature": 0,
    }
    if slot is not None:
        payload["id_slot"] = slot
    if session_id is not None:
        payload["session_id"] = session_id
    return _json_request("POST", base + "/completion", payload, timeout=360)


def _timing(result: dict) -> dict[str, float]:
    timings = result.get("timings") or {}
    return {
        "id_slot": int(result.get("id_slot", -1)),
        "cache_n": int(timings.get("cache_n", 0)),
        "prompt_n": int(timings.get("prompt_n", 0)),
        "predicted_n": int(timings.get("predicted_n", 0)),
        "prompt_ms": round(float(timings.get("prompt_ms", 0)), 3),
        "prompt_tps": round(float(timings.get("prompt_per_second", 0)), 3),
    }


def _reuse_ratio(timing: dict) -> float:
    total = timing["cache_n"] + timing["prompt_n"]
    return round(timing["cache_n"] / total, 6) if total else 0.0


def classify_slot_result(isolated: dict, contaminated: dict) -> dict[str, object]:
    isolated_ratio = _reuse_ratio(isolated)
    contaminated_ratio = _reuse_ratio(contaminated)
    passed = isolated_ratio >= 0.80 and isolated_ratio >= contaminated_ratio + 0.50
    return {
        "passed": passed,
        "isolated_reuse_ratio": isolated_ratio,
        "contaminated_reuse_ratio": contaminated_ratio,
        "reuse_ratio_delta": round(isolated_ratio - contaminated_ratio, 6),
    }


def _make_prompt(lines: int) -> str:
    rows = ["PRE4-CACHE-ANCHOR-BEGIN"]
    for index in range(lines):
        rows.append(
            f"record-{index:04d}: alpha beta gamma delta epsilon; immutable prefix probe."
        )
    rows.append("PRE4-CACHE-ANCHOR-END")
    return "\n".join(rows)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_variant(args: argparse.Namespace, parallel: int, run_dir: Path) -> dict:
    before = {**host_memory(), **gpu_snapshot()}
    if before["ram_available_gib"] < args.min_ram_gib:
        raise RuntimeError(f"RAM guard: {before['ram_available_gib']} GiB available")
    if before["vram_free_mib"] < args.min_vram_mib:
        raise RuntimeError(f"VRAM guard: {before['vram_free_mib']} MiB free")
    if before["temperature_c"] > args.max_start_temp:
        raise RuntimeError(f"thermal start guard: {before['temperature_c']}C")
    if _port_open(args.port):
        raise RuntimeError(f"port {args.port} already in use")

    slot_dir = run_dir / f"slots-np{parallel}"
    slot_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"server-np{parallel}.log"
    command = [
        str(args.server),
        "-m", str(args.model),
        "--host", "127.0.0.1",
        "--port", str(args.port),
        "--ctx-size", "49152",
        "--parallel", str(parallel),
        "--batch-size", "2048",
        "--ubatch-size", "1024",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "-fa", "on",
        "--metrics",
        "--slot-save-path", str(slot_dir),
        "--n-gpu-layers", "all",
        "--no-warmup",
    ]
    base = f"http://127.0.0.1:{args.port}"
    proc = None
    started = time.time()
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            proc = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=str(args.server.parent),
            )
            _wait_ready(base, proc)
            print(f"np={parallel}: server ready", flush=True)

            for slot in range(parallel):
                _erase(base, slot)

            prefix = _make_prompt(args.prompt_lines)
            suffix = prefix + "\nUSER-SUFFIX: preserve the complete prefix and answer later."
            service_slot = parallel - 1

            main_seed = _timing(_completion(base, prefix, 0))
            service = _timing(
                _completion(base, "SERVICE-TITLE: return a three word title.", service_slot)
            )
            erase_service = _erase(base, service_slot)
            isolated = _timing(_completion(base, suffix, 0))
            isolated["reuse_ratio"] = _reuse_ratio(isolated)
            print(
                f"np={parallel}: isolated cache={isolated['cache_n']} "
                f"prompt={isolated['prompt_n']} ratio={isolated['reuse_ratio']:.3f}",
                flush=True,
            )

            for slot in range(parallel):
                _erase(base, slot)
            control_seed = _timing(_completion(base, prefix, 0))
            overwrite = _timing(
                _completion(base, "SERVICE-OVERWRITE: unrelated short service prompt.", 0)
            )
            contaminated = _timing(_completion(base, suffix, 0))
            contaminated["reuse_ratio"] = _reuse_ratio(contaminated)
            verdict = classify_slot_result(isolated, contaminated)
            print(
                f"np={parallel}: control cache={contaminated['cache_n']} "
                f"prompt={contaminated['prompt_n']} pass={verdict['passed']}",
                flush=True,
            )

            for slot in range(parallel):
                _erase(base, slot)
            session_a = _timing(
                _completion(base, "SESSION-ID-PROBE-A", None, session_id="pre4-same")
            )
            session_b = _timing(
                _completion(base, "SESSION-ID-PROBE-A\nB", None, session_id="pre4-same")
            )

            _erase(base, service_slot)
            max_zero = _json_request(
                "POST",
                base + "/v1/completions",
                {
                    "model": "ling",
                    "prompt": "MAX-TOKENS-ZERO-PREFILL",
                    "max_tokens": 0,
                    "cache_prompt": True,
                    "id_slot": service_slot,
                },
                timeout=120,
            )
            max_zero_timing = _timing(max_zero)
            max_zero_ok = max_zero_timing["predicted_n"] == 0

            after = {**host_memory(), **gpu_snapshot()}
            if after["temperature_c"] >= args.abort_temp:
                raise RuntimeError(f"thermal abort guard: {after['temperature_c']}C")
            return {
                "status": "usable" if verdict["passed"] and max_zero_ok else "failed",
                "parallel": parallel,
                "started_at": dt.datetime.fromtimestamp(started).astimezone().isoformat(),
                "elapsed_s": round(time.time() - started, 3),
                "command": command,
                "snapshot_before": before,
                "snapshot_after": after,
                "main_seed": main_seed,
                "service": service,
                "erase_service": erase_service,
                "isolated_append": isolated,
                "control_seed": control_seed,
                "same_slot_service_overwrite": overwrite,
                "contaminated_append": contaminated,
                "slot_isolation": verdict,
                "session_id_probe": {
                    "first": session_a,
                    "second": session_b,
                    "note": "session_id is sent without id_slot; server-selected slots are observed only",
                },
                "max_tokens_zero": {
                    "timing": max_zero_timing,
                    "passed": max_zero_ok,
                    "meaning": "OpenAI max_tokens=0 performs prefill with zero decode",
                },
                "log": str(log_path),
            }
    finally:
        _stop_process(proc)


def _self_test() -> int:
    isolated = {"cache_n": 900, "prompt_n": 10}
    contaminated = {"cache_n": 0, "prompt_n": 910}
    assert classify_slot_result(isolated, contaminated)["passed"] is True
    assert classify_slot_result(contaminated, isolated)["passed"] is False
    assert _reuse_ratio({"cache_n": 0, "prompt_n": 0}) == 0.0
    print("self-test: ok")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", type=Path, default=DEFAULT_SERVER)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--parallel", type=int, nargs="+", default=[2, 4])
    parser.add_argument("--prompt-lines", type=int, default=400)
    parser.add_argument("--min-ram-gib", type=float, default=4.0)
    parser.add_argument("--min-vram-mib", type=float, default=7350.0)
    parser.add_argument("--max-start-temp", type=float, default=65.0)
    parser.add_argument("--abort-temp", type=float, default=91.0)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.self_test:
        return _self_test()
    if not args.server.is_file() or not args.model.is_file():
        print(f"missing server/model: {args.server} | {args.model}", file=sys.stderr)
        return 2
    if any(value < 2 for value in args.parallel):
        print("parallel must be >=2 for service-slot isolation", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    run_dir = args.results / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "odysseus.pre4-slot-probe.v1",
        "created_at": dt.datetime.now().astimezone().isoformat(),
        "server": str(args.server),
        "server_sha256": _hash(args.server),
        "binary_bundle_sha256": {
            name: _hash(args.server.parent / name)
            for name in (
                "llama-server.exe",
                "llama-server-impl.dll",
                "llama.dll",
                "ggml.dll",
                "ggml-cuda.dll",
            )
            if (args.server.parent / name).is_file()
        },
        "model": str(args.model),
        "model_size_bytes": args.model.stat().st_size,
        "model_sha256": _hash(args.model),
        "production_config": str(PRODUCTION_CONFIG),
        "production_config_sha256_before": (
            _hash(PRODUCTION_CONFIG) if PRODUCTION_CONFIG.is_file() else None
        ),
        "variants": [],
    }
    exit_code = 0
    try:
        for parallel in args.parallel:
            print(f"phase: np={parallel}", flush=True)
            try:
                result = run_variant(args, parallel, run_dir)
            except Exception as exc:
                result = {
                    "status": "guard_abort" if "guard" in str(exc).lower() else "error",
                    "parallel": parallel,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                exit_code = 1
            manifest["variants"].append(result)
            result_path = run_dir / f"np{parallel}.json"
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"np={parallel}: {result['status']} -> {result_path}", flush=True)
            if result["status"] != "usable":
                exit_code = 1
    finally:
        manifest["production_config_sha256_after"] = (
            _hash(PRODUCTION_CONFIG) if PRODUCTION_CONFIG.is_file() else None
        )
        manifest["production_config_unchanged"] = (
            manifest["production_config_sha256_before"]
            == manifest["production_config_sha256_after"]
        )
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"manifest: {manifest_path}", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
