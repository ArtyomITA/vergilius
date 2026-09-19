r"""Onda 4, coda notturna 2: aspetta il flag di fine di onda4-notte.py (catena-fine.flag), poi
  B9   = B8 + ODYSSEUS_MEMORY_TAIL=1 (memorie in coda + replay dei blocchi pre)
  riparazione H0/H1: butta i turni in errore (504, connessioni) e rifa' solo quelli
  H2   = H1 + ODYSSEUS_GROUNDING_RETRY=1 (H4-retry), patch applicata a Odysseus FERMO
Stato in misure/onda4/notte.txt (stesso file).
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
PATCH_RETRY = Path(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\d--assistenteeee\f6c9077b-17ce-49ac-bab8-a7efc9b9b9f3\scratchpad\patch_grounding_retry.py")

B8 = ["ODYSSEUS_TOOLSET_FREEZE=1", "ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=128",
      "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096", "ODYSSEUS_TOOL_ROUND_REASONING_MESSAGE=Basta ragionare, agisco.",
      "ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_TOOL_DEDUP=1", "ODYSSEUS_GROUNDING_CHECK=1",
      "ODYSSEUS_HISTORY_REPLAY=1"]
B9 = B8 + ["ODYSSEUS_MEMORY_TAIL=1"]
H1 = B8 + ["ODYSSEUS_GROUNDING_RULES=1", "ODYSSEUS_FRESH_REQUIRED=1"]
H2 = B9 + ["ODYSSEUS_GROUNDING_RULES=1", "ODYSSEUS_FRESH_REQUIRED=1", "ODYSSEUS_GROUNDING_RETRY=1"]


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


def riavvia(tag, env):
    r = subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"), "riavvia-odysseus", tag, *env],
                       capture_output=True, text=True)
    ok = "pronto: True" in r.stdout
    nota(f"odysseus {tag} riavviato: {ok}")
    if ok:
        time.sleep(5)
    return ok


def suite(tag):
    subprocess.run([str(PY), str(W / "scripts/suite-allucinazioni-e2e.py"), "--tag", tag, "--riprendi"],
                   cwd=str(W), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def ripara(tag, env):
    fj = OUT / f"alluc-{tag}.json"
    if not fj.exists():
        return
    d = json.loads(fj.read_text(encoding="utf-8"))
    buoni = [t for t in d["turni"] if not t.get("errore")]
    if len(buoni) == len(d["turni"]) and len(buoni) >= 48:
        return
    d["turni"] = buoni
    fj.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    nota(f"{tag}: {len(buoni)} turni validi, rifaccio i mancanti")
    if riavvia(tag + "fix", env):
        suite(tag)
        nota(f"{tag} riparata")


if __name__ == "__main__":
    nota("coda 2 avviata: aspetto il flag di fine catena")
    while not (OUT / "catena-fine.flag").exists():
        time.sleep(30)
    if not completo(OUT / "braccio-B9.txt", "BRACCIO COMPLETO"):
        subprocess.run([sys.executable, str(W / "scripts/onda4-braccio.py"), "B9", *B9], cwd=str(W),
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        nota("braccio B9 completo")
    ripara("H0", B8)
    ripara("H1", H1)
    if not completo(OUT / "alluc-H2.txt", "SUITE COMPLETA"):
        ferma_odysseus()
        marker = W / "odysseus/src/agent_loop.py"
        if "ODYSSEUS_GROUNDING_RETRY" not in marker.read_text(encoding="utf-8", errors="replace"):
            r = subprocess.run([sys.executable, str(PATCH_RETRY)], cwd=str(W), capture_output=True, text=True)
            nota("patch grounding-retry: " + ((r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]))
        ok = subprocess.run([sys.executable, "-c",
                             "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())", str(marker)],
                            capture_output=True, text=True).returncode == 0
        if not ok:
            nota("agent_loop.py NON compila dopo la patch: H2 saltata")
        elif riavvia("H2", H2):
            nota("H2 avvio suite allucinazioni (16 casi x 3)")
            suite("H2")
            nota("H2 fine")
    nota("CODA 2 COMPLETA")
