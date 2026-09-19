r"""Generic Odysseus E2E regression harness for Wave 4.

The existing Financial harness remains unchanged. This one adds deterministic
chat/history, agent-schema and browser progressive-disclosure cases, while
recording SSE usage/tool events and the Odysseus log tail.

Examples:
  odysseus\venv\Scripts\python.exe scripts\prova_e2e_onda4.py --suite core
  odysseus\venv\Scripts\python.exe scripts\prova_e2e_onda4.py --suite all
  odysseus\venv\Scripts\python.exe scripts\prova_e2e_onda4.py --list-cases
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.cookiejar
import json
from pathlib import Path
import sys
import time
import urllib.request


ROOT = Path(r"D:\assistenteeee")
DEFAULT_BASE = "http://127.0.0.1:7000"
CREDENTIALS = ROOT / "scripts" / ".credenziali_odysseus"
DEFAULT_RESULTS = ROOT / "ricerche" / "opt-1080" / "misure" / "pre4-e2e"
DEFAULT_LOG = ROOT / "odysseus" / "logs" / "startup-odysseus.log"


CORE_CASES = [
    {
        "id": "chat-seed-history",
        "mode": "chat",
        "prompt": (
            "Regression test isolato: ricorda nel solo contesto di questa chat "
            "il nonce CERULEAN-417. Rispondi solo STORED."
        ),
        "contains": ["STORED"],
        "min_chars": 6,
    },
    {
        "id": "chat-read-history",
        "mode": "chat",
        "prompt": "Qual era il nonce del messaggio precedente? Rispondi solo col nonce.",
        "contains": ["CERULEAN-417"],
        "min_chars": 12,
    },
    {
        "id": "agent-schema-stability",
        "mode": "agent",
        "prompt": "Calcola 17 moltiplicato 23. Rispondi solo col numero.",
        "contains": ["391"],
        "min_chars": 3,
    },
    {
        "id": "chat-history-after-agent",
        "mode": "chat",
        "prompt": (
            "Scrivi in una riga il nonce del primo turno e il risultato numerico "
            "del turno precedente."
        ),
        "contains": ["CERULEAN-417", "391"],
        "min_chars": 16,
    },
]

BROWSER_CASES = [
    {
        "id": "browser-progressive-disclosure",
        "mode": "agent",
        "prompt": (
            "Apri https://example.com usando i tool browser e dimmi il titolo "
            "visibile della pagina."
        ),
        "tool_prefix": "browser_",
        "contains": ["Example"],
        "min_chars": 15,
    },
]


def _client():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _credentials() -> tuple[str, str]:
    rows = [
        row.strip()
        for row in CREDENTIALS.read_text(encoding="utf-8").splitlines()
        if row.strip()
    ]
    if len(rows) < 2:
        raise RuntimeError(f"invalid credentials file: {CREDENTIALS}")
    return rows[0], rows[1]


def _json_request(opener, method: str, url: str, payload: dict | None = None, timeout=60):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _form_request(opener, url: str, fields: dict[str, str], timeout=900):
    boundary = "----pre4OdysseusBoundary"
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="{name}"\r\n\r\n{value}\r\n'
        )
    body = ("".join(parts) + f"--{boundary}--\r\n").encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    return opener.open(request, timeout=timeout)


def parse_sse_line(line: str, state: dict) -> bool:
    line = line.strip()
    if not line.startswith("data:"):
        return False
    payload = line[5:].strip()
    if payload == "[DONE]":
        return True
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        state["malformed_sse"] += 1
        return False
    event_type = event.get("type") or ""
    if event_type == "tool_start":
        state["tools"].append(event.get("tool") or event.get("name") or "?")
    elif event_type == "usage":
        state["usage"].append(event.get("data") or {})
    elif event_type == "model_actual":
        state["actual_models"].append(event)
    elif event_type in {
        "rounds_exhausted",
        "intent_nudge_exhausted",
        "budget_exceeded",
        "error",
    }:
        state["notable_events"].append(event_type)
    delta = event.get("delta")
    if isinstance(delta, str):
        if event.get("thinking"):
            state["thinking_chars"] += len(delta)
        else:
            state["text_parts"].append(delta)
    return False


def _new_stream_state() -> dict:
    return {
        "tools": [],
        "usage": [],
        "actual_models": [],
        "notable_events": [],
        "text_parts": [],
        "thinking_chars": 0,
        "malformed_sse": 0,
    }


def run_turn(opener, base: str, session_id: str, case: dict) -> dict:
    state = _new_stream_state()
    started = time.perf_counter()
    fields = {
        "message": case["prompt"],
        "session": session_id,
        "mode": case["mode"],
        "plan_mode": "false",
        "vista_mode": "false",
        "osint_mode": "false",
        "financial_mode": "false",
        "allow_bash": "false",
        "use_rag": "false",
        "allow_web_search": "false",
    }
    with _form_request(opener, base + "/api/chat_stream", fields) as response:
        for raw in response:
            if parse_sse_line(raw.decode("utf-8", errors="replace"), state):
                break
    text = "".join(state.pop("text_parts")).strip()
    required = case.get("contains") or []
    contains_ok = all(item.lower() in text.lower() for item in required)
    tool_prefix = case.get("tool_prefix")
    tool_ok = not tool_prefix or any(
        str(tool).startswith(tool_prefix) for tool in state["tools"]
    )
    no_terminal_failure = not any(
        event in state["notable_events"]
        for event in ("rounds_exhausted", "intent_nudge_exhausted", "budget_exceeded", "error")
    )
    passed = (
        len(text) >= int(case.get("min_chars", 1))
        and contains_ok
        and tool_ok
        and no_terminal_failure
    )
    return {
        "id": case["id"],
        "mode": case["mode"],
        "prompt": case["prompt"],
        "passed": passed,
        "elapsed_s": round(time.perf_counter() - started, 3),
        "response": text,
        "response_chars": len(text),
        **state,
    }


def select_endpoint(raw, requested_model: str | None) -> tuple[dict, str]:
    endpoints = raw if isinstance(raw, list) else (raw.get("endpoints") or raw.get("items") or [])
    selected = next(
        (
            endpoint
            for endpoint in endpoints
            if isinstance(endpoint, dict) and (endpoint.get("is_default") or endpoint.get("default"))
        ),
        None,
    )
    if selected is None and endpoints:
        selected = endpoints[0]
    if not isinstance(selected, dict):
        raise RuntimeError(f"no model endpoint: {str(raw)[:300]}")
    model = requested_model or (
        selected.get("default_model")
        or selected.get("model")
        or selected.get("model_name")
        or "ling"
    )
    return selected, str(model)


def _read_log_tail(path: Path, offset: int) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as stream:
        stream.seek(min(offset, path.stat().st_size))
        return stream.read().decode("utf-8", errors="replace")


def _log_signals(text: str) -> dict[str, object]:
    lowered = text.lower()
    return {
        "bytes": len(text.encode("utf-8")),
        "llm_successes": lowered.count("llm async call") + lowered.count("llm call to"),
        "retry_mentions": lowered.count("retry") + lowered.count("attempt 2") + lowered.count("attempt 3"),
        "auto_title_mentions": lowered.count("auto-name") + lowered.count("auto title") + lowered.count("auto-title"),
        "memory_mentions": lowered.count("memory extract") + lowered.count("memory_extract") + lowered.count("bg-extract"),
        "agent_timing_mentions": lowered.count("[agent-timing]"),
        "slot_mentions": lowered.count("id_slot") + lowered.count("session_id"),
    }


def _cases(suite: str) -> list[dict]:
    if suite == "core":
        return list(CORE_CASES)
    if suite == "browser":
        return list(BROWSER_CASES)
    return list(CORE_CASES) + list(BROWSER_CASES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--model")
    parser.add_argument("--suite", choices=("core", "browser", "all"), default="core")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--background-wait", type=float, default=10.0)
    parser.add_argument("--list-cases", action="store_true")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    cases = _cases(args.suite)
    if args.list_cases:
        print(json.dumps(cases, indent=2, ensure_ascii=False))
        return 0

    opener = _client()
    username, password = _credentials()
    _json_request(
        opener,
        "POST",
        args.base + "/api/auth/login",
        {"username": username, "password": password},
    )
    endpoints = _json_request(opener, "GET", args.base + "/api/model-endpoints")
    endpoint, model = select_endpoint(endpoints, args.model)
    log_offset = args.log.stat().st_size if args.log.is_file() else 0

    with _form_request(
        opener,
        args.base + "/api/session",
        {
            "name": "pre4-e2e-" + dt.datetime.now().strftime("%H%M%S"),
            "endpoint_id": str(endpoint.get("id") or ""),
            "model": model,
        },
        timeout=60,
    ) as response:
        session = json.loads(response.read().decode("utf-8"))
    session_id = session.get("session_id") or session.get("id") or session.get("session")
    if not session_id:
        raise RuntimeError(f"session creation failed: {session}")

    print(f"endpoint={endpoint.get('id', '?')} model={model} session={session_id}")
    results = []
    for index, case in enumerate(cases, 1):
        print(f"[{index}/{len(cases)}] {case['id']} ...", flush=True)
        try:
            result = run_turn(opener, args.base, session_id, case)
        except Exception as exc:
            result = {
                "id": case["id"],
                "mode": case["mode"],
                "prompt": case["prompt"],
                "passed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        results.append(result)
        print(
            f"  {'ok' if result['passed'] else 'FAIL'} "
            f"{result.get('elapsed_s', 0):.1f}s tools={result.get('tools', [])}",
            flush=True,
        )

    if args.background_wait > 0:
        print(f"background observation: {args.background_wait:.0f}s", flush=True)
        time.sleep(min(args.background_wait, 60))
    log_tail = _read_log_tail(args.log, log_offset)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    args.results.mkdir(parents=True, exist_ok=True)
    output_path = args.results / f"e2e-{args.suite}-{stamp}.json"
    report = {
        "schema": "odysseus.pre4-e2e.v1",
        "created_at": dt.datetime.now().astimezone().isoformat(),
        "suite": args.suite,
        "base": args.base,
        "endpoint_id": endpoint.get("id"),
        "model": model,
        "session_id": session_id,
        "passed": all(result["passed"] for result in results),
        "cases": results,
        "log_signals": _log_signals(log_tail),
        "log_tail": log_tail,
        "financial_harness": str(ROOT / "scripts" / "prova_e2e_agente.py"),
    }
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"result={output_path}")
    print(f"E2E={'PASS' if report['passed'] else 'FAIL'}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
