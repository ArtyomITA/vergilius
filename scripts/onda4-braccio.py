r"""Onda 4: un BRACCIO completo su istanza di prova, controllabile e riprendibile.

Cosa fa: `onda4-braccio.py TAG KEY=VAL ...`
  1. segna l'offset di stack/llama-swap.log (per leggere i timings solo di questo braccio);
  2. riavvia Odysseus (7000) con le variabili date, log in stack/odysseus-TAG.log, dump in dump-TAG/;
  3. prova_e2e_agente.py x3 (4 casi Financial, chat unica per passata) -> baseline-TAG-agente-N.txt;
     una passata gia' completa su disco (file che finisce con "E2E:") viene SALTATA (ripresa);
  4. prova_e2e_onda4.py --suite core -> baseline-TAG-onda4-core.txt;
  5. stato in braccio-TAG.txt, una riga per passo, con temperatura e clock GPU.

Poi: python scripts/onda4-baseline-leggi.py TAG
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

W = Path(r"d:\assistenteeee")
OUT = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4")
STACK = OUT / "stack"
PY = W / "odysseus/venv/Scripts/python.exe"


def gpu():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,clocks.sm",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return "?"


def main():
    tag = sys.argv[1]
    extra = [a for a in sys.argv[2:] if "=" in a]
    stato = OUT / f"braccio-{tag}.txt"

    def nota(msg):
        riga = f"{time.strftime('%H:%M:%S')} gpu[{gpu()}] {msg}"
        print(riga, flush=True)
        with open(stato, "a", encoding="utf-8") as f:
            f.write(riga + "\n")

    swap = STACK / "llama-swap.log"
    off = STACK / f"llama-swap.offset-{tag}"
    if not off.exists():
        off.write_text(str(swap.stat().st_size if swap.exists() else 0), encoding="utf-8")
    nota(f"braccio {tag} extra={extra} offset llama-swap={off.read_text()}")

    r = subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"),
                        "riavvia-odysseus", tag, *extra], capture_output=True, text=True)
    nota("riavvio odysseus: " + (r.stdout.strip().splitlines() or ["?"])[-1])
    if "pronto: True" not in r.stdout:
        nota("ODYSSEUS NON PRONTO, fermo"); sys.exit(2)
    time.sleep(5)

    for n in (1, 2, 3):
        f = OUT / f"baseline-{tag}-agente-{n}.txt"
        if f.exists() and "E2E:" in f.read_text(encoding="utf-8", errors="replace"):
            nota(f"passata {n}/3 gia' completa, salto"); continue
        nota(f"passata {n}/3 avvio")
        t0 = time.time()
        with open(f, "w", encoding="utf-8") as fo:
            subprocess.run([str(PY), str(W / "scripts/prova_e2e_agente.py")],
                           stdout=fo, stderr=subprocess.STDOUT, cwd=str(W))
        esito = [l for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("E2E:")]
        nota(f"passata {n}/3 fine {time.time()-t0:.0f}s {esito[-1] if esito else 'SENZA ESITO'}")

    f = OUT / f"baseline-{tag}-onda4-core.txt"
    if f.exists() and ("passed" in f.read_text(encoding="utf-8", errors="replace").lower()
                       or "PASS" in f.read_text(encoding="utf-8", errors="replace")):
        nota("core gia' fatto, salto")
    else:
        nota("core avvio")
        t0 = time.time()
        with open(f, "w", encoding="utf-8") as fo:
            subprocess.run([str(PY), str(W / "scripts/prova_e2e_onda4.py"), "--suite", "core",
                            "--log", str(STACK / f"odysseus-{tag}.log")],
                           stdout=fo, stderr=subprocess.STDOUT, cwd=str(W))
        nota(f"core fine {time.time()-t0:.0f}s")
    nota("BRACCIO COMPLETO")


if __name__ == "__main__":
    main()
