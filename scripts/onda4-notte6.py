r"""Coda 6: chiude l'onda 4 e prepara il progetto alla pubblicazione.

Aspetta "CODA 5 FINITA" in notte.txt, poi:
  1. ripara i turni in errore di H3 e H3m (504 su /api/session: bug scheduler)
  2. ferma lo stack di prova
  3. accende il binario Pascal in llama-swap (grafi CUDA: +40% su questa GPU)
  4. sposta il laboratorio (ricerche, misure, backup) fuori dal progetto, in
     D:\vergilius-lab, lasciando un puntatore
Stato in misure/onda4/notte.txt.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

W = Path(r"d:\assistenteeee")
LAB = Path(r"d:\vergilius-lab")
OUT = W / "ricerche/opt-1080/misure/onda4"
STATO = OUT / "notte.txt"
PY = W / "odysseus/venv/Scripts/python.exe"
PATCH_H4 = Path(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\d--assistenteeee\f6c9077b-17ce-49ac-bab8-a7efc9b9b9f3\scratchpad\patch_h4.py")

B11 = ["ODYSSEUS_TOOLSET_FREEZE=1", "ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=128",
       "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096", "ODYSSEUS_TOOL_ROUND_REASONING_MESSAGE=Basta ragionare, agisco.",
       "ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_GROUNDING_CHECK=1",
       "ODYSSEUS_HISTORY_REPLAY=1", "ODYSSEUS_MEMORY_TAIL=1",
       "ODYSSEUS_TOOL_OUTPUT_CHARS=3000", "ODYSSEUS_HISTORY_TOOL_CHARS=3300",
       "ODYSSEUS_TOOL_CACHE_TTL=900"]
H3 = B11 + ["ODYSSEUS_GROUNDING_RULES=1", "ODYSSEUS_FRESH_REQUIRED=1", "ODYSSEUS_GROUNDING_RETRY=1"]


def nota(msg):
    riga = f"{time.strftime('%H:%M:%S')} {msg}"
    print(riga, flush=True)
    with open(STATO, "a", encoding="utf-8") as f:
        f.write(riga + "\n")


def completo(f, marca):
    return f.exists() and marca in f.read_text(encoding="utf-8", errors="replace")


def ripara(tag, multi=False):
    fj = OUT / f"alluc-{tag}.json"
    if not fj.exists():
        return
    d = json.loads(fj.read_text(encoding="utf-8"))
    buoni = [t for t in d["turni"] if not t.get("errore")]
    if len(buoni) == len(d["turni"]):
        nota(f"{tag}: nessun turno in errore")
        return
    d["turni"] = buoni
    fj.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    nota(f"{tag}: {len(buoni)} turni validi, rifaccio i mancanti")
    r = subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"),
                        "riavvia-odysseus", tag + "fix", *H3], capture_output=True, text=True)
    if "pronto: True" not in r.stdout:
        nota(f"{tag}: Odysseus non pronto, salto")
        return
    time.sleep(5)
    subprocess.run([str(PY), str(W / "scripts/suite-allucinazioni-e2e.py"), "--tag", tag, "--riprendi"]
                   + (["--multi"] if multi else []), cwd=str(W),
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    nota(f"{tag} riparata")


def sposta_laboratorio():
    LAB.mkdir(parents=True, exist_ok=True)
    for nome in ("ricerche", "backup-pre-pubblicazione", "backup-vergilius-2026-08-20"):
        src = W / nome
        if not src.exists():
            continue
        dst = LAB / nome
        if dst.exists():
            nota(f"{nome}: in {LAB} c'e' gia', salto")
            continue
        try:
            shutil.move(str(src), str(dst))
            nota(f"{nome} spostato in {dst}")
        except Exception as e:
            nota(f"{nome} NON spostato: {type(e).__name__} {e}")
    puntatore = W / "LABORATORIO.md"
    puntatore.write_text(
        "# Dove sono finite le misure\n\n"
        f"Ricerche, banchi, misure grezze e backup vivono fuori dal progetto, in `{LAB}`.\n\n"
        "Non servono per usare Vergilius: sono il diario di come sono state scelte le\n"
        "impostazioni di `vergilius.env` e `vergilius-hardware.env`. Ogni riga di quei due\n"
        "file cita la misura che la giustifica.\n\n"
        "| cartella | cosa contiene |\n|---|---|\n"
        "| `ricerche/opt-1080/` | le sei onde di ottimizzazione, con esiti e conclusioni |\n"
        "| `ricerche/opt-1080/misure/` | dati grezzi dei banchi (json, log) |\n"
        "| `backup-pre-pubblicazione/` | database e memorie prima della pulizia |\n",
        encoding="utf-8")
    nota("scritto LABORATORIO.md")


if __name__ == "__main__":
    nota("coda 6 avviata: aspetto la fine della coda cinque")
    while not completo(STATO, "CODA 5 FINITA"):
        time.sleep(30)
    ripara("H3")
    ripara("H3m", multi=True)
    # H4: le tre correzioni trovate da H3 (quotazione in testa all'output, tolleranza
    # numerica stretta allo 0,5%, eco della richiesta che non conta come dato) piu' la
    # descrizione di fin_mercati ristretta. Patch applicata a Odysseus FERMO.
    if not completo(OUT / "alluc-H4.txt", "SUITE COMPLETA"):
        pids = OUT / "stack/pids.json"
        if pids.exists():
            dd = json.loads(pids.read_text())
            if "odysseus" in dd:
                subprocess.run(["taskkill", "/PID", str(dd["odysseus"]), "/T", "/F"], capture_output=True)
                dd.pop("odysseus")
                pids.write_text(json.dumps(dd), encoding="utf-8")
        time.sleep(3)
        marker = W / "odysseus/src/shadowbroker/finanza.py"
        if "IN TESTA, non in coda" not in marker.read_text(encoding="utf-8", errors="replace"):
            r = subprocess.run([sys.executable, str(PATCH_H4)], cwd=str(W), capture_output=True, text=True)
            nota("patch H4: " + ((r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]))
        ok = all(subprocess.run([sys.executable, "-c",
                                 "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())", str(W / f)],
                                capture_output=True, text=True).returncode == 0
                 for f in ("odysseus/src/shadowbroker/finanza.py", "odysseus/src/agent_loop.py",
                           "odysseus/src/shadowbroker/schemi.py"))
        if not ok:
            nota("sorgenti NON compilano dopo la patch H4: braccio saltato")
        else:
            r = subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"),
                                "riavvia-odysseus", "H4", *H3], capture_output=True, text=True)
            if "pronto: True" in r.stdout:
                time.sleep(5)
                nota("H4 avvio suite allucinazioni")
                subprocess.run([str(PY), str(W / "scripts/suite-allucinazioni-e2e.py"),
                                "--tag", "H4", "--riprendi"], cwd=str(W),
                               stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                nota("H4 fine: " + ((OUT / "alluc-H4.txt").read_text(encoding="utf-8", errors="replace").splitlines() or ["?"])[-1])
            else:
                nota("H4: Odysseus non pronto")
    subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"), "ferma"],
                   cwd=str(W), capture_output=True, text=True)
    nota("stack di prova fermato")
    time.sleep(5)
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(W / "scripts/vergilius-binario-pascal.ps1"), "-Pascal"],
                       capture_output=True, text=True, cwd=str(W))
    nota("binario Pascal: " + " | ".join(l.strip() for l in r.stdout.splitlines() if l.strip())[:200])
    sposta_laboratorio()
    nota("CODA 6 FINITA")
