r"""Onda 4, coda 3: aspetta la riga "CODA 2 COMPLETA" in notte.txt, poi
  B9b = stessa env di B9 (replay + memorie in coda) con le patch differite applicate
        (marcatura _pre, sweep saltato a modello scarico).
"""
import subprocess
import sys
import time
from pathlib import Path

W = Path(r"d:\assistenteeee")
OUT = W / "ricerche/opt-1080/misure/onda4"
STATO = OUT / "notte.txt"
B9 = ["ODYSSEUS_TOOLSET_FREEZE=1", "ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=128",
      "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096", "ODYSSEUS_TOOL_ROUND_REASONING_MESSAGE=Basta ragionare, agisco.",
      "ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_TOOL_DEDUP=1", "ODYSSEUS_GROUNDING_CHECK=1",
      "ODYSSEUS_HISTORY_REPLAY=1", "ODYSSEUS_MEMORY_TAIL=1"]


def nota(msg):
    riga = f"{time.strftime('%H:%M:%S')} {msg}"
    print(riga, flush=True)
    with open(STATO, "a", encoding="utf-8") as f:
        f.write(riga + "\n")


def completo(f, marca):
    return f.exists() and marca in f.read_text(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    nota("coda 3 avviata: aspetto la fine della coda 2")
    while not completo(STATO, "CODA 2 COMPLETA"):
        time.sleep(30)
    if not completo(OUT / "braccio-B9b.txt", "BRACCIO COMPLETO"):
        subprocess.run([sys.executable, str(W / "scripts/onda4-braccio.py"), "B9b", *B9], cwd=str(W),
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        nota("braccio B9b completo")
    nota("CODA 3 FINITA")
