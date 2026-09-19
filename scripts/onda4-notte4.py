r"""Onda 4, coda 4: aspetta "CODA 3 FINITA" in notte.txt, ferma Odysseus, applica la patch
user_sent (a Odysseus fermo), controlla la sintassi, corre B9c (stessa env di B9), poi FERMA
tutto lo stack di prova.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

W = Path(r"d:\assistenteeee")
OUT = W / "ricerche/opt-1080/misure/onda4"
STATO = OUT / "notte.txt"
PATCH = Path(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\d--assistenteeee\f6c9077b-17ce-49ac-bab8-a7efc9b9b9f3\scratchpad\patch_user_sent.py")
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


def ferma_odysseus():
    pids = OUT / "stack/pids.json"
    if pids.exists():
        d = json.loads(pids.read_text())
        if "odysseus" in d:
            subprocess.run(["taskkill", "/PID", str(d["odysseus"]), "/T", "/F"], capture_output=True)
            d.pop("odysseus")
            pids.write_text(json.dumps(d), encoding="utf-8")
    time.sleep(3)


if __name__ == "__main__":
    nota("coda 4 avviata: aspetto la fine della coda tre")
    while not completo(STATO, "CODA 3 FINITA"):
        time.sleep(30)
    if not completo(OUT / "braccio-B9c.txt", "BRACCIO COMPLETO"):
        ferma_odysseus()
        marker = W / "odysseus/core/models.py"
        if "llm_user_sent" not in marker.read_text(encoding="utf-8", errors="replace"):
            r = subprocess.run([sys.executable, str(PATCH)], cwd=str(W), capture_output=True, text=True)
            nota("patch user_sent: " + ((r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]))
        ok = all(subprocess.run([sys.executable, "-c", "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())", str(W / p)],
                                capture_output=True, text=True).returncode == 0
                 for p in ("odysseus/core/models.py", "odysseus/src/agent_loop.py"))
        if not ok:
            nota("sorgenti NON compilano dopo la patch: B9c saltato")
        else:
            subprocess.run([sys.executable, str(W / "scripts/onda4-braccio.py"), "B9c", *B9], cwd=str(W),
                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            nota("braccio B9c completo")
    subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"), "ferma"], cwd=str(W),
                   capture_output=True, text=True)
    nota("stack di prova fermato")
    nota("CODA 4 FINITA")
