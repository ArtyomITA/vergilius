r"""Banco comportamentale COMPLETO su Q6_K con la configurazione candidata all'adozione.

Cosa fa, da solo e senza internet:
  1. avvia un llama-server STANDALONE (porta 5899, la produzione llama-swap non viene toccata)
     con la config candidata: Q6_K + ctx 49152 + ub 1024 + KV q8_0 + --metrics + --slot-save-path;
  2. warmup in due passi (32 token + prefill lungo): la prima richiesta grande compila i kernel
     PTX al volo (lezione T03, onda 0) e non deve sporcare il primo caso;
  3. esegue TUTTE le suite dell'harness comportamentale (prova_ling_behavior, repeats=2,
     ~263 casi) UN caso alla volta, con:
       - gate termico PRIMA di ogni caso: si aspetta che la GPU scenda a 76 °C (onda 1: metà
         dei giri partiva a 79-83 °C già in throttling e la varianza copriva il segnale);
       - PAUSA DI 60 SECONDI dopo ogni caso (richiesta utente);
       - salvataggio incrementale dopo OGNI caso (già nell'harness: un crash conserva tutto);
       - le guardie proprie dell'harness restano attive (trim del working set, RAM minima,
         raffreddamento a 84 °C, abort);
  4. FASE 2 (aggiunta, i test della fase 1 restano intatti): riavvia il server con la STESSA
     config + speculativa ngram-map-k (draft 3, sotto la soglia MMVQ di Q6_K) e riesegue le
     suite piu' sensibili — schema e communication (tool call = regime copia, dove la
     speculativa rende) e baseline (controllo) — con repeats=1, per vedere se cambia qualcosa
     nel comportamento e quanto cambia `elapsed_s` caso per caso;
  5. a fine corsa spegne il server e stampa i riepiloghi di entrambe le fasi.

Il preflight dell'harness interroga llama-swap (/running): qui viene sostituito con uno stub
perche' il server e' standalone — e' l'unico adattamento, i casi e i giudizi restano identici.

USO (PowerShell, dalla cartella d:\assistenteeee) — SERVE il python del venv di Odysseus
(l'harness importa la catena Odysseus: col python di sistema manca bcrypt):
  odysseus\venv\Scripts\python.exe scripts\banco-comportamentale-q6.py

I log si salvano DA SOLI (niente Tee necessario), pensati per una corsa senza nessuno davanti:
  logs\banco-q6-<data>.log         tutto l'output a schermo, riga per riga
  logs\banco-q6-casi-<data>.jsonl  una riga JSON per OGNI caso chiuso (ora, suite, caso,
                                   esito, secondi, temperatura/clock GPU) — se qualcosa muore
                                   a meta', qui c'e' la cronaca esatta fino all'ultimo caso
  logs\server-<fase>-<data>.log    stdout/stderr del llama-server di ogni fase

Esito in: ricerche\ling-behavior-q6k-<data>.json (+ .md riepilogo + .manifest.json).
Confronto con la baseline Q5_K_M gia' su disco (ricerche\ling-behavior-all-parziale*.json):
  python odysseus\scripts\rivaluta_ling_behavior.py <vecchio.json> <nuovo.json>
"""

from __future__ import annotations

import ctypes
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(r"d:\assistenteeee")
LOGS = WORKSPACE / "logs"
MARCA = f"{datetime.now():%Y%m%d-%H%M%S}"
SERVER = WORKSPACE / "llama-cuda124-new" / "llama-server.exe"
MODELLO = WORKSPACE / "models" / "Ling-3.0-tiny-Q6_K.gguf"
HARNESS = WORKSPACE / "odysseus" / "scripts" / "prova_ling_behavior.py"
SLOTSAVE = WORKSPACE / "ricerche" / "opt-1080" / "misure" / "slotsave"
PORTA = 5899
ENDPOINT = f"http://127.0.0.1:{PORTA}/v1/chat/completions"

PAUSA_TRA_CASI_S = 0           # pausa tolta su richiesta utente (25 ago); il gate termico resta
GATE_TERMICO_C = 76            # onda 1: ogni caso parte dallo stesso stato termico
GATE_TERMICO_ATTESA_MAX_S = 600
ABORT_TEMP_C = 90              # oltre: qualcosa non va (ventola?), fermarsi

# Configurazione CANDIDATA ALL'ADOZIONE (esito onde 1-3, 25 ago 2026).
# KV f16 e ub 2048 su Q6_K sono rumore (misurato): restano q8_0 e 1024.
FLAGS_SERVER = [
    "-m", str(MODELLO),
    "--ctx-size", "49152",
    "--reasoning", "on",
    "--temp", "1.0", "--top-p", "0.95", "--top-k", "20",
    # ub 512 (non 1024): a ub 1024 il margine VRAM era ~170 MiB e un'app desktop qualunque
    # (Chrome/shell stanno sulla 1080) lo ha mangiato a meta' corsa (68 MiB -> guardia).
    # ub 512 dimezza il compute buffer (~165 MiB recuperati); correttezza identica.
    "--batch-size", "2048", "--ubatch-size", "512",
    "--n-gpu-layers", "999",
    "-fa", "on",
    "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
    "--cache-ram", "0",
    "--load-mode", "mmap",
    "--metrics",
    "--slot-save-path", str(SLOTSAVE),
]


class _Tee:
    """Duplica stdout/stderr su file: la corsa gira senza nessuno davanti, il log resta."""

    def __init__(self, originale, percorso: Path):
        self._orig = originale
        self._fh = open(percorso, "a", encoding="utf-8", errors="replace")

    def write(self, testo):
        try:
            self._orig.write(testo)
        except UnicodeEncodeError:
            # terminale cp1252: i simboli non rappresentabili (es. il ✓ dell'harness)
            # non devono MAI far morire la corsa — sul file restano intatti
            self._orig.write(testo.encode(self._orig.encoding or "ascii", "replace")
                             .decode(self._orig.encoding or "ascii", "replace"))
        self._fh.write(testo)
        self._fh.flush()
        return len(testo)

    def flush(self):
        self._orig.flush()
        self._fh.flush()


def _log_caso(riga: dict) -> None:
    """Una riga JSON per ogni caso chiuso: cronaca minima che sopravvive a qualunque crash."""
    try:
        with open(LOGS / f"banco-q6-casi-{MARCA}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(riga, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


# Fase 2: identica alla config candidata + speculativa n-gram (draft 3: la soglia MMVQ di
# Q6_K e' 4, e la curva batch dice che 3 token si verificano quasi al prezzo di 1).
FLAGS_NGRAM = [
    "--spec-type", "ngram-map-k",
    "--spec-ngram-map-k-size-n", "8",
    "--spec-ngram-map-k-size-m", "3",
    "--spec-ngram-map-k-min-hits", "1",
]


def _gpu() -> dict:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,clocks.sm,memory.used,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15).stdout.strip().split(",")
        return {"temp": float(out[0]), "clock": float(out[1]),
                "vram_usata": float(out[2]), "vram_libera": float(out[3])}
    except Exception:
        return {}


def _trim_ws(pid: int) -> None:
    """Svuota il working set del server: le pagine mmap del modello (6,8 GB) non servono coi
    pesi in VRAM, ma senza trim la RAM 'libera' crolla e le guardie scattano a vuoto (onda 1)."""
    try:
        h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
        if h:
            ctypes.windll.kernel32.SetProcessWorkingSetSize(h, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        pass


def _richiesta(prompt: str, max_tokens: int, timeout: int = 600) -> None:
    corpo = {"model": "ling", "messages": [{"role": "user", "content": prompt}],
             "max_tokens": max_tokens, "temperature": 0, "top_k": 1}
    req = urllib.request.Request(ENDPOINT, data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read()


def avvia_server(flags_extra: list[str] | None = None, nome: str = "fase") -> subprocess.Popen:
    SLOTSAVE.mkdir(parents=True, exist_ok=True)
    comando = [str(SERVER), "--host", "127.0.0.1", "--port", str(PORTA)] + FLAGS_SERVER + (flags_extra or [])
    print(f"[server] avvio: {' '.join(comando)}", flush=True)
    log_server = open(LOGS / f"server-{nome}-{MARCA}.log", "a", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(comando, stdout=log_server, stderr=subprocess.STDOUT,
                            creationflags=0x08000000)
    for _ in range(300):
        time.sleep(1)
        if proc.poll() is not None:
            raise SystemExit("[server] morto in avvio: controlla VRAM libera e il percorso del modello")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/health", timeout=2) as r:
                if r.status == 200:
                    _trim_ws(proc.pid)
                    print("[server] sano, working set ripulito", flush=True)
                    return proc
        except Exception:
            pass
    proc.kill()
    raise SystemExit("[server] non sano entro 300 s")


def warmup() -> None:
    """Due passi (lezione T03): il primo caso del banco non deve pagare i kernel freddi."""
    print("[warmup] passo 1: 32 token", flush=True)
    _richiesta("Warmup breve.", 32)
    print("[warmup] passo 2: prefill lungo (~7000 token)", flush=True)
    riempimento = ("Nota operativa di riscaldamento ripetuta per riempire il contesto. " * 320)
    _richiesta(riempimento + "\nRispondi con una parola.", 8)
    print("[warmup] fatto (entrambe le risposte scartate)", flush=True)


def gate_termico() -> None:
    t0 = time.time()
    while time.time() - t0 < GATE_TERMICO_ATTESA_MAX_S:
        g = _gpu()
        t = g.get("temp", 0)
        if t >= ABORT_TEMP_C:
            raise SystemExit(f"[guardia] GPU a {t:.0f} C: abort (ventola/pasta da controllare)")
        if t <= GATE_TERMICO_C:
            return
        time.sleep(10)
    print(f"[gate] GPU ancora sopra {GATE_TERMICO_C} C dopo {GATE_TERMICO_ATTESA_MAX_S} s: proseguo comunque", flush=True)


def main() -> int:
    if not SERVER.exists() or not MODELLO.exists() or not HARNESS.exists():
        print(f"manca uno tra:\n  {SERVER}\n  {MODELLO}\n  {HARNESS}")
        return 2

    # Log automatico di tutto l'output: la corsa gira senza nessuno davanti.
    for flusso in (sys.stdout, sys.stderr):
        if hasattr(flusso, "reconfigure"):
            flusso.reconfigure(encoding="utf-8", errors="replace")
    LOGS.mkdir(parents=True, exist_ok=True)
    sys.stdout = _Tee(sys.stdout, LOGS / f"banco-q6-{MARCA}.log")
    sys.stderr = _Tee(sys.stderr, LOGS / f"banco-q6-{MARCA}.log")
    print(f"[log] output completo in logs/banco-q6-{MARCA}.log; "
          f"cronaca per caso in logs/banco-q6-casi-{MARCA}.jsonl", flush=True)

    # ---- carica l'harness come modulo (i suoi import interni gestiscono sys.path) ----
    sys.path.insert(0, str(HARNESS.parent.parent))          # per `from src...` dentro l'harness
    os.chdir(HARNESS.parent.parent)
    spec = importlib.util.spec_from_file_location("prova_ling_behavior", HARNESS)
    harness = importlib.util.module_from_spec(spec)
    sys.modules["prova_ling_behavior"] = harness   # senza, i @dataclass esplodono su Py3.13
    spec.loader.exec_module(harness)

    # ---- stub del preflight (interroga llama-swap, qui il server e' standalone) ----
    def preflight_standalone(endpoint, model, *, allow_swap, allow_holo):
        return {
            "guard": harness.guard(),
            "swap_base": f"http://127.0.0.1:{PORTA}",
            "running": [{"model": "ling", "state": "ready", "note": "standalone Q6_K, no llama-swap"}],
            "holo_active": False,
            "props": None,
            "config_sha256": "standalone-q6k-adozione",
        }
    harness.preflight = preflight_standalone
    harness.wait_server_idle = lambda *a, **k: True
    # Con ub 512 il margine a regime e' ~243 MiB liberi; il server ngram della fase 2 ne
    # tiene ~47 in piu' (stato speculativo) e scende a 196: la soglia deve stare SOTTO i
    # regimi legittimi di entrambe le fasi ma sopra la zona pericolo. 150 MiB.
    harness.MIN_FREE_VRAM_MIB = 150

    # ---- RESUME (decisione utente 25 ago): i casi gia' fatti nelle corse precedenti
    # non si rifanno — si ricopiano nel nuovo esito e si prosegue dai mancanti.
    # NB: le corse precedenti giravano con ub 1024; ub tocca solo il compute buffer del
    # prefill, non i token prodotti, quindi i VERDETTI restano validi; gli elapsed_s
    # ripresi non vanno confrontati con quelli nuovi (riga marcata "ripreso_da").
    def carica_fatti(con_ngram: bool) -> dict:
        mappa: dict[tuple, dict] = {}
        for pf in sorted((WORKSPACE / "ricerche").glob("ling-behavior-q6k-*.json")):
            if "manifest" in pf.name or ("ngram" in pf.name) != con_ngram:
                continue
            try:
                for r in json.loads(pf.read_text(encoding="utf-8")):
                    k = (r.get("variant"), r.get("case"), r.get("repeat"))
                    if all(x is not None for x in k) and not r.get("error"):
                        mappa.setdefault(k, {**r, "ripreso_da": pf.name})
            except Exception:
                pass
        return mappa

    # mappa attiva: la fase() la sostituisce prima di partire (standard vs ngram:
    # stesse chiavi ma config server diverse, NON vanno mischiate)
    fatti = carica_fatti(con_ngram=False)
    if fatti:
        print(f"[resume] {len(fatti)} casi standard gia' fatti: non verranno rifatti", flush=True)

    # ---- avvolgi run_case: gate termico prima, pausa di 60 s dopo ----
    run_case_vero = harness.run_case
    contatore = {"n": 0}
    mappa_attiva = {"fatti": fatti}

    def run_case_con_pause(endpoint, model, **job):
        chiave = (job.get("variant"), getattr(job.get("case"), "case_id", None), job.get("repeat"))
        fatti = mappa_attiva["fatti"]
        if chiave in fatti:
            print(f"      [resume] salto {chiave[0]} {chiave[1]} rep{chiave[2]} (gia' fatto)", flush=True)
            return dict(fatti[chiave])
        gate_termico()
        row = run_case_vero(endpoint, model, **job)
        contatore["n"] += 1
        g = _gpu()
        row["gpu_dopo"] = g
        _log_caso({
            "quando": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
            "n": contatore["n"],
            "variant": row.get("variant"), "case": row.get("case"),
            "repeat": row.get("repeat"), "correct": row.get("correct"),
            "channel": row.get("channel"), "elapsed_s": row.get("elapsed_s"),
            "gpu": g,
        })
        print(f"      [pausa] {PAUSA_TRA_CASI_S}s (caso {contatore['n']} chiuso, "
              f"GPU {g.get('temp', 0):.0f} C)", flush=True)
        time.sleep(PAUSA_TRA_CASI_S)
        return row
    harness.run_case = run_case_con_pause

    # ---- due fasi: standard completa, poi varianti con ngram ----
    def fase(nome: str, flags_extra: list[str] | None, suite: str, repeats: int, uscita: Path) -> int:
        mappa_attiva["fatti"] = carica_fatti(con_ngram=flags_extra is not None)
        print(f"[resume] mappa attiva per {nome}: {len(mappa_attiva['fatti'])} casi gia' fatti", flush=True)
        proc = avvia_server(flags_extra, nome=nome.replace(" ", "-").replace("/", "-"))
        try:
            warmup()
            sys.argv = [
                "prova_ling_behavior",
                "--suite", suite,
                "--repeats", str(repeats),
                "--endpoint", ENDPOINT,
                "--model", "ling",
                "--output", str(uscita),
                "--request-timeout", "600",
                "--allow-swap", "--allow-holo",
            ]
            print(f"[{nome}] via: suite={suite} repeats={repeats}, pausa {PAUSA_TRA_CASI_S}s, "
                  f"gate {GATE_TERMICO_C} C -> {uscita}", flush=True)
            return harness.main()
        finally:
            try:
                proc.kill()
                proc.wait(timeout=20)
            except Exception:
                pass
            print(f"[{nome}] server spento. Esito (anche parziale): {uscita}", flush=True)

    marca = MARCA
    uscita1 = WORKSPACE / "ricerche" / f"ling-behavior-q6k-{marca}.json"
    codice = fase("fase 1 - standard", None, "all", 2, uscita1)

    # Fase 2 (AGGIUNTA: la fase 1 resta identica). Stesse domande, server con speculativa.
    # Suite scelte: schema+communication (tool call = regime copia) e baseline (controllo).
    codici2 = []
    for suite2 in ("schema", "communication", "baseline"):
        uscita2 = WORKSPACE / "ricerche" / f"ling-behavior-q6k-ngram-{suite2}-{marca}.json"
        codici2.append(fase(f"fase 2 - ngram/{suite2}", FLAGS_NGRAM, suite2, 1, uscita2))

    print("\n[confronti]", flush=True)
    print("  qualita' vs Q5_K_M:  python odysseus\\scripts\\rivaluta_ling_behavior.py "
          "ricerche\\ling-behavior-all-parziale1-rep2.json " + str(uscita1), flush=True)
    print("  ngram vs standard:   confrontare correct% ed elapsed_s per caso tra "
          f"ling-behavior-q6k-{marca}.json e i ling-behavior-q6k-ngram-*-{marca}.json", flush=True)
    return codice or max(codici2, default=0)


if __name__ == "__main__":
    raise SystemExit(main())
