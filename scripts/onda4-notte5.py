r"""Onda 4, coda 5 (pomeriggio 27 ago): "il resto".
  B10  = B9c + ODYSSEUS_TOOL_OUTPUT_CHARS=3000 + ODYSSEUS_HISTORY_TOOL_CHARS=3300 (tool identici in-turno/storia)
  B11  = B10 + ODYSSEUS_TOOL_CACHE_TTL=900 (cache strumenti per sessione)
  H3   = suite allucinazioni singolo turno con env B11 + grounding (regole, required, rilancio con entita')
  H3m  = suite allucinazioni MULTI-turno, stessa env
Poi ferma lo stack. Stato in misure/onda4/notte.txt. Riprendibile passo per passo.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

W = Path(r"d:\assistenteeee")
OUT = W / "ricerche/opt-1080/misure/onda4"
STATO = OUT / "notte.txt"
PY = W / "odysseus/venv/Scripts/python.exe"

B9 = ["ODYSSEUS_TOOLSET_FREEZE=1", "ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=128",
      "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096", "ODYSSEUS_TOOL_ROUND_REASONING_MESSAGE=Basta ragionare, agisco.",
      "ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_GROUNDING_CHECK=1",
      "ODYSSEUS_HISTORY_REPLAY=1", "ODYSSEUS_MEMORY_TAIL=1"]
B10 = B9 + ["ODYSSEUS_TOOL_OUTPUT_CHARS=3000", "ODYSSEUS_HISTORY_TOOL_CHARS=3300"]
B11 = B10 + ["ODYSSEUS_TOOL_CACHE_TTL=900"]
H3 = B11 + ["ODYSSEUS_GROUNDING_RULES=1", "ODYSSEUS_FRESH_REQUIRED=1", "ODYSSEUS_GROUNDING_RETRY=1"]


def nota(msg):
    riga = f"{time.strftime('%H:%M:%S')} {msg}"
    print(riga, flush=True)
    with open(STATO, "a", encoding="utf-8") as f:
        f.write(riga + "\n")


def completo(f, marca):
    return f.exists() and marca in f.read_text(encoding="utf-8", errors="replace")


def riavvia(tag, env):
    r = subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"), "riavvia-odysseus", tag, *env],
                       capture_output=True, text=True)
    ok = "pronto: True" in r.stdout
    nota(f"odysseus {tag} riavviato: {ok}")
    if ok:
        time.sleep(5)
    return ok


def braccio(tag, env):
    if completo(OUT / f"braccio-{tag}.txt", "BRACCIO COMPLETO"):
        nota(f"{tag} gia' completo"); return
    subprocess.run([sys.executable, str(W / "scripts/onda4-braccio.py"), tag, *env], cwd=str(W),
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    nota(f"braccio {tag} completo")


def suite(tag, env, multi=False):
    if completo(OUT / f"alluc-{tag}.txt", "SUITE COMPLETA"):
        nota(f"{tag} gia' completa"); return
    if not riavvia(tag, env):
        nota(f"{tag}: Odysseus non pronto"); return
    nota(f"{tag} avvio suite allucinazioni" + (" MULTI-turno" if multi else ""))
    subprocess.run([str(PY), str(W / "scripts/suite-allucinazioni-e2e.py"), "--tag", tag, "--riprendi"]
                   + (["--multi"] if multi else []), cwd=str(W), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    nota(f"{tag} fine: " + ((OUT / f"alluc-{tag}.txt").read_text(encoding="utf-8", errors="replace").splitlines() or ["?"])[-1])


if __name__ == "__main__":
    nota("coda 5 avviata")
    braccio("B10", B10)
    braccio("B11", B11)
    suite("H3", H3)
    suite("H3m", H3, multi=True)
    subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"), "ferma"], cwd=str(W),
                   capture_output=True, text=True)
    nota("stack di prova fermato")
    nota("CODA 5 FINITA")
