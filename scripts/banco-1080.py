r"""Banco di misura A/B per llama.cpp sulla GTX 1080 (Vergilius).

Perche' esiste: le misure fatte a mano finora si sono rivelate ingannevoli due volte.
  - la PRIMA generazione dopo l'avvio e' sempre lenta (warmup dei kernel CUDA, prima toccata
    delle pagine mmap, clock che sale da P8): misurata da sola dava 35 tok/s invece di 46;
  - un banco lungo scalda la GPU fino al throttling (85 C -> 1632 MHz invece di 1936), quindi
    la configurazione misurata per SECONDA sembra peggiore di quella misurata per prima.
Questo banco elimina entrambi gli effetti: scarta il warmup, alterna le configurazioni (A B A B)
e registra clock/temperatura/utilizzo insieme al risultato, cosi' un numero sospetto si puo'
sempre spiegare.

Uso:
  # una sola configurazione
  python scripts\banco-1080.py singolo --nome baseline

  # confronto A/B (le due config si alternano, 3 giri ciascuna)
  python scripts\banco-1080.py ab --nome-a baseline --nome-b ub512 --flags-b "--ubatch-size 512"

  # con variabili d'ambiente (per le leve che non sono flag)
  python scripts\banco-1080.py ab --nome-a base --nome-b nopdl --env-b GGML_CUDA_PDL=0

Le configurazioni partono SEMPRE dalla riga di comando di produzione (vedi PRODUZIONE qui sotto),
cosi' si misura la differenza rispetto a cio' che gira davvero, non rispetto a un ideale.

Output: un JSONL in ricerche/opt-1080/misure/ con tutti i parametri e tutti i campioni, piu' un
riepilogo a schermo. Nessun file di progetto viene toccato.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE = Path(r"d:\assistenteeee")
SERVER = WORKSPACE / "llama-cuda124-new" / "llama-server.exe"
MODELLO = WORKSPACE / "models" / "Ling-3.0-tiny-Q5_K_M.gguf"
USCITE = WORKSPACE / "ricerche" / "opt-1080" / "misure"
PORTA = 5899  # porta di test: NON la 8012 di llama-swap, cosi' lo stack resta intatto

# Riga di comando di produzione (llama-swap/config.yaml, profilo `ling`), 23 ago 2026.
PRODUZIONE = [
    "-m", str(MODELLO),
    "--ctx-size", "131072",
    "--reasoning", "on",
    "--temp", "1.0", "--top-p", "0.95", "--top-k", "20",
    "--batch-size", "2048", "--ubatch-size", "1024",
    "--n-gpu-layers", "999",
    "-fa", "on",
    "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
    "--cache-ram", "0",
    "--load-mode", "mmap",
]

# Guardie: sotto/sopra questi valori il banco si ferma invece di produrre numeri falsi.
MIN_RAM_LIBERA_MB = 900
MIN_VRAM_LIBERA_MB = 250
MAX_TEMP_C = 88          # oltre: interrompe
TEMP_RAFFREDDA_C = 82    # oltre: aspetta che scenda prima del campione successivo
TEMP_RIPARTI_C = 74

PROMPT_LUNGO = (
    "Di seguito una nota operativa ripetuta serve solo a riempire il contesto in modo "
    "realistico, come farebbero le regole di sistema e gli schemi degli strumenti. "
)
DOMANDA = "Scrivi esattamente 150 parole sulla citta' di Roma, senza elenchi puntati."


# --------------------------------------------------------------------------- sistema

def _ps(comando: str) -> str:
    try:
        return subprocess.run(["powershell", "-NoProfile", "-Command", comando],
                              capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def ram_libera_mb() -> float:
    out = _ps("[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)")
    try:
        return float(out)
    except ValueError:
        return -1.0


def gpu_stato() -> dict:
    """VRAM usata/libera, utilizzo, clock e temperatura in un colpo solo."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free,utilization.gpu,clocks.sm,clocks.mem,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15).stdout.strip()
        v = [x.strip() for x in out.split(",")]
        return {"vram_usata_mb": float(v[0]), "vram_libera_mb": float(v[1]), "util_pct": float(v[2]),
                "clock_sm_mhz": float(v[3]), "clock_mem_mhz": float(v[4]), "temp_c": float(v[5]),
                "watt": float(v[6]) if v[6] not in ("[N/A]", "N/A") else None}
    except Exception:
        return {}


def guardia(fase: str) -> dict:
    stato = gpu_stato()
    ram = ram_libera_mb()
    stato["ram_libera_mb"] = ram
    if 0 <= ram < MIN_RAM_LIBERA_MB:
        raise SystemExit(f"STOP ({fase}): RAM libera {ram:.0f} MB sotto la soglia {MIN_RAM_LIBERA_MB}")
    if stato.get("temp_c", 0) >= MAX_TEMP_C:
        raise SystemExit(f"STOP ({fase}): GPU a {stato['temp_c']:.0f} C")
    if stato.get("temp_c", 0) >= TEMP_RAFFREDDA_C:
        print(f"    [attesa] GPU a {stato['temp_c']:.0f} C, aspetto che scenda sotto {TEMP_RIPARTI_C}")
        for _ in range(30):
            time.sleep(10)
            t = gpu_stato().get("temp_c", 0)
            if t <= TEMP_RIPARTI_C:
                break
        stato = gpu_stato()
        stato["ram_libera_mb"] = ram_libera_mb()
        stato["raffreddato"] = True
    return stato


# --------------------------------------------------------------------------- server

def _trim_ws(pid: int) -> None:
    """Svuota il working set del server: le pagine mmap del modello (5,5 GB) non servono
    quando i pesi sono in VRAM, ma senza questo la guardia RAM scatta a vuoto.
    Verificato in onda 0: velocita' invariata dopo il trim."""
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
        if h:
            ctypes.windll.kernel32.SetProcessWorkingSetSize(h, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        pass


SERVER_CORRENTE = None  # se valorizzato, sostituisce SERVER (confronto fra build diverse)


def avvia(flags: list[str], env_extra: dict[str, str]) -> subprocess.Popen:
    env = os.environ.copy()
    env.update(env_extra)
    # --slot-save-path abilita POST /slots/{id}?action=erase (senza: 501 Not Implemented).
    # Serve a svuota_slot(): identico per A e B, non tocca l'inferenza.
    (USCITE / "slotsave").mkdir(parents=True, exist_ok=True)
    comando = [str(SERVER_CORRENTE or SERVER), "--host", "127.0.0.1", "--port", str(PORTA),
               "--slot-save-path", str(USCITE / "slotsave")] + flags
    proc = subprocess.Popen(comando, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=0x08000000 if os.name == "nt" else 0)
    t0 = time.time()
    for _ in range(180):
        time.sleep(1)
        if proc.poll() is not None:
            raise SystemExit(f"il server e' morto in avvio. Comando: {' '.join(comando)}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/health", timeout=2) as r:
                if r.status == 200:
                    _trim_ws(proc.pid)
                    return proc, round(time.time() - t0, 1)
        except Exception:
            pass
    proc.kill()
    raise SystemExit("il server non e' diventato sano entro 180 s")


def ferma(proc: subprocess.Popen) -> None:
    try:
        proc.kill()
        proc.wait(timeout=20)
    except Exception:
        pass
    time.sleep(3)


def svuota_slot() -> None:
    """Cancella la KV di tutti gli slot: senza, i giri successivi al primo lavorano su una
    cache unificata frammentata dai giri precedenti e il prefill crolla (misurato:
    895 -> 397 -> 233 tok/s nello stesso avvio). Ogni giro deve partire da KV vuota."""
    for sid in range(8):
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{PORTA}/slots/{sid}?action=erase",
                                         data=b"", method="POST")
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            break


def aspetta_fresco(max_c: float = 76.0) -> None:
    """Gate termico PRIMA di ogni giro: ogni campione parte dallo stesso stato termico.
    Senza, meta' dei giri parte a 79-83 C gia' in throttling e la varianza copre il segnale."""
    for _ in range(60):
        t = gpu_stato().get("temp_c", 0)
        if t <= max_c:
            return
        time.sleep(10)


def richiesta(prompt: str, max_tokens: int, greedy: bool = True) -> dict:
    corpo = {"model": "test", "messages": [{"role": "user", "content": prompt}],
             "max_tokens": max_tokens}
    corpo.update({"temperature": 0, "top_k": 1} if greedy else {})
    req = urllib.request.Request(f"http://127.0.0.1:{PORTA}/v1/chat/completions",
                                 data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read().decode())
    t = d.get("timings", {}) or {}
    return {
        "wall_s": round(time.time() - t0, 3),
        "prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"),
        "pp_tok_s": round(t.get("prompt_per_second") or 0, 1),
        "predicted_n": t.get("predicted_n"),
        "tg_tok_s": round(t.get("predicted_per_second") or 0, 2),
    }


# --------------------------------------------------------------------------- misura

def misura(nome: str, flags: list[str], env_extra: dict, giri: int, token_prompt: int,
           exe_dir: str | None = None) -> dict:
    """Un giro completo: avvio, warmup scartato, `giri` campioni, spegnimento."""
    global SERVER_CORRENTE
    SERVER_CORRENTE = (Path(exe_dir) / "llama-server.exe") if exe_dir else None
    guardia(f"prima di {nome}")
    proc, t_avvio = avvia(flags, env_extra)
    try:
        riempimento = PROMPT_LUNGO * max(1, token_prompt // 22)
        # Warmup: SCARTATO. Il primo passaggio paga kernel freddi, pagine mmap non toccate
        # e clock ancora in P8; includerlo falsa la misura del 20-30 %.
        richiesta(DOMANDA, 32)
        campioni = []
        for i in range(giri):
            svuota_slot()
            aspetta_fresco()
            g = guardia(f"{nome} giro {i + 1}")
            # prompt lungo (misura pp) + generazione (misura tg) in un colpo solo
            # Prompt DIVERSO ad ogni giro. Riusando lo stesso, dal secondo giro in poi la prefix
            # cache lo riconosce, `prompt_n` scende a poche unita' e la misura di pp perde senso
            # (misurato: 70-85 tok/s invece di ~1600). Il prefisso variabile va in TESTA, perche'
            # e' li' che la cache confronta.
            r = richiesta(f"Variante {i + 1} del banco. " + riempimento + "\n\n" + DOMANDA, 200)
            r["gpu"] = g
            campioni.append(r)
            print(f"    {nome} giro {i + 1}/{giri}: pp {r['pp_tok_s']:>7.1f} tok/s | "
                  f"tg {r['tg_tok_s']:>6.2f} tok/s | {g.get('clock_sm_mhz', 0):.0f} MHz "
                  f"{g.get('temp_c', 0):.0f} C util {g.get('util_pct', 0):.0f}%")
        pp = [c["pp_tok_s"] for c in campioni]
        tg = [c["tg_tok_s"] for c in campioni]
        return {
            "nome": nome, "flags": flags, "env": env_extra, "avvio_s": t_avvio,
            "pp_mediana": statistics.median(pp), "tg_mediana": statistics.median(tg),
            "pp_tutti": pp, "tg_tutti": tg,
            "vram_mb": campioni[-1]["gpu"].get("vram_usata_mb"),
            "campioni": campioni,
        }
    finally:
        ferma(proc)


def stampa_confronto(a: dict, b: dict) -> None:
    print("\n" + "=" * 78)
    for metrica, chiave in (("prompt processing (pp)", "pp_mediana"), ("generazione (tg)", "tg_mediana")):
        va, vb = a[chiave], b[chiave]
        delta = (vb - va) / va * 100 if va else 0
        # Regola pratica: sotto il 3 % di differenza, con 3 campioni, non e' distinguibile
        # dal rumore di clock/termico. Serve piu' campioni o una differenza piu' grande.
        verdetto = "RUMORE (non distinguibile)" if abs(delta) < 3 else ("MEGLIO B" if delta > 0 else "MEGLIO A")
        print(f"  {metrica:<24} A {va:>8.2f}   B {vb:>8.2f}   {delta:+6.1f}%   {verdetto}")
    print(f"  VRAM                     A {a['vram_mb']:>8.0f}   B {b['vram_mb']:>8.0f} MiB")
    print(f"  avvio                    A {a['avvio_s']:>8.1f}   B {b['avvio_s']:>8.1f} s")
    print("=" * 78)


def salva(righe: list[dict], etichetta: str) -> Path:
    USCITE.mkdir(parents=True, exist_ok=True)
    percorso = USCITE / f"{etichetta}-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    with open(percorso, "w", encoding="utf-8") as fh:
        for r in righe:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return percorso


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("modo", choices=("singolo", "ab"))
    p.add_argument("--nome", default="config")
    p.add_argument("--nome-a", default="A")
    p.add_argument("--nome-b", default="B")
    p.add_argument("--flags", default="", help="flag AGGIUNTIVI o sostitutivi rispetto alla produzione")
    p.add_argument("--flags-a", default="")
    p.add_argument("--flags-b", default="")
    p.add_argument("--env", default="", help="VAR=val,VAR2=val2")
    p.add_argument("--env-a", default="")
    p.add_argument("--env-b", default="")
    p.add_argument("--giri", type=int, default=3, help="campioni per configurazione (default 3)")
    p.add_argument("--alternanze", type=int, default=2, help="quante volte alternare A e B (default 2)")
    p.add_argument("--token-prompt", type=int, default=7000, help="lunghezza del prompt, default = un round agente reale")
    p.add_argument("--domanda", default=None, help="sostituisce la domanda finale (es. compito di copia per la speculativa)")
    p.add_argument("--exe-a", default=None, help="cartella llama-server alternativa per A (confronto fra build)")
    p.add_argument("--exe-b", default=None, help="cartella llama-server alternativa per B")
    args = p.parse_args()
    if args.domanda:
        global DOMANDA
        DOMANDA = args.domanda

    def env_dict(s: str) -> dict:
        return dict(kv.split("=", 1) for kv in s.split(",") if "=" in kv)

    def flags(extra: str) -> list[str]:
        base = list(PRODUZIONE)
        toks = extra.split()
        i = 0
        while i < len(toks):
            if toks[i].startswith("-"):
                # sostituisce il valore se il flag c'e' gia', altrimenti lo aggiunge
                val = toks[i + 1] if i + 1 < len(toks) and not toks[i + 1].startswith("-") else None
                if toks[i] in base:
                    j = base.index(toks[i])
                    if val is not None and j + 1 < len(base):
                        base[j + 1] = val
                else:
                    base.append(toks[i])
                    if val is not None:
                        base.append(val)
                i += 2 if val is not None else 1
            else:
                i += 1
        return base

    if not SERVER.exists() or not MODELLO.exists():
        return print(f"manca {SERVER} o {MODELLO}") or 2

    righe = []
    if args.modo == "singolo":
        r = misura(args.nome, flags(args.flags), env_dict(args.env), args.giri, args.token_prompt)
        righe.append(r)
        print(f"\n  {args.nome}: pp {r['pp_mediana']:.1f} tok/s | tg {r['tg_mediana']:.2f} tok/s | "
              f"VRAM {r['vram_mb']:.0f} MiB | avvio {r['avvio_s']:.1f} s")
    else:
        # Alternanza A B A B: annulla la deriva termica e l'ordine di esecuzione.
        risultati = {args.nome_a: [], args.nome_b: []}
        for giro in range(args.alternanze):
            print(f"\n-- alternanza {giro + 1}/{args.alternanze}")
            for nome, fl, en in ((args.nome_a, args.flags_a, args.env_a), (args.nome_b, args.flags_b, args.env_b)):
                exe = args.exe_a if nome == args.nome_a else args.exe_b
                r = misura(nome, flags(fl or args.flags), env_dict(en or args.env), args.giri, args.token_prompt, exe)
                risultati[nome].append(r)
                righe.append(r)
        agg = {}
        for nome, lista in risultati.items():
            agg[nome] = {
                "nome": nome, "flags": lista[0]["flags"], "env": lista[0]["env"],
                "pp_mediana": statistics.median([x for r in lista for x in r["pp_tutti"]]),
                "tg_mediana": statistics.median([x for r in lista for x in r["tg_tutti"]]),
                "vram_mb": lista[-1]["vram_mb"], "avvio_s": statistics.median([r["avvio_s"] for r in lista]),
            }
        stampa_confronto(agg[args.nome_a], agg[args.nome_b])
        righe.append({"riepilogo": agg})

    percorso = salva(righe, args.nome if args.modo == "singolo" else f"{args.nome_a}-vs-{args.nome_b}")
    print(f"\nmisure salvate in {percorso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
