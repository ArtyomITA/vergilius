r"""Onda 4, catena notturna (27 ago 2026): aspetta i bracci B6b/B7, poi
  H0  suite allucinazioni E2E con env B7 (senza grounding)           -> alluc-H0.*
  H1  suite allucinazioni E2E con env B7 + grounding + fresh-required -> alluc-H1.*
  BANCO comportamentale 526 casi (prova_ling_behavior --suite all --repeats 2) via llama-swap 8012
        con reasoning_budget_tokens=128 (la leva E11), Odysseus fermo intanto -> banco-budget128.json
Ogni passo e' riprendibile: se il suo file di esito esiste ed e' completo, viene saltato.
Stato riga per riga in misure/onda4/notte.txt.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

W = Path(r"d:\assistenteeee")
OUT = W / "ricerche/opt-1080/misure/onda4"
PY = W / "odysseus/venv/Scripts/python.exe"
STATO = OUT / "notte.txt"

B6 = ["ODYSSEUS_TOOLSET_FREEZE=1", "ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=128",
      "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096", "ODYSSEUS_TOOL_ROUND_REASONING_MESSAGE=Basta ragionare, agisco."]
B7 = B6 + ["ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_TOOL_DEDUP=1", "ODYSSEUS_GROUNDING_CHECK=1"]
B8 = B7 + ["ODYSSEUS_HISTORY_REPLAY=1"]
H1 = B8 + ["ODYSSEUS_GROUNDING_RULES=1", "ODYSSEUS_FRESH_REQUIRED=1"]


def nota(msg):
    riga = f"{time.strftime('%H:%M:%S')} {msg}"
    print(riga, flush=True)
    with open(STATO, "a", encoding="utf-8") as f:
        f.write(riga + "\n")


def completo(f, marca):
    return f.exists() and marca in f.read_text(encoding="utf-8", errors="replace")


def attendi_bracci():
    while not completo(OUT / "braccio-B7.txt", "BRACCIO COMPLETO"):
        time.sleep(30)
    nota("bracci B6b/B7 completi")


def riavvia(tag, env):
    r = subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"), "riavvia-odysseus", tag, *env],
                       capture_output=True, text=True)
    ok = "pronto: True" in r.stdout
    nota(f"odysseus {tag} riavviato: {ok}")
    return ok


def suite_alluc(tag, env):
    if completo(OUT / f"alluc-{tag}.txt", "SUITE COMPLETA"):
        nota(f"{tag} gia' completa, salto"); return
    if not riavvia(tag, env):
        nota(f"{tag}: Odysseus non pronto, salto"); return
    time.sleep(5)
    nota(f"{tag} avvio suite allucinazioni (16 casi x 3)")
    subprocess.run([str(PY), str(W / "scripts/suite-allucinazioni-e2e.py"), "--tag", tag, "--riprendi"],
                   cwd=str(W), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    nota(f"{tag} fine: " + ((OUT / f"alluc-{tag}.txt").read_text(encoding="utf-8", errors="replace").splitlines() or ["?"])[-1])


def ferma_odysseus():
    pids = OUT / "stack/pids.json"
    if pids.exists():
        d = json.loads(pids.read_text())
        if "odysseus" in d:
            subprocess.run(["taskkill", "/PID", str(d["odysseus"]), "/T", "/F"], capture_output=True)
            d.pop("odysseus"); pids.write_text(json.dumps(d), encoding="utf-8")
            nota("odysseus fermato per il banco (llama-swap resta su)")


def banco():
    out = OUT / "banco-budget128.json"
    if out.exists() and out.stat().st_size > 100_000:
        nota("banco gia' presente, salto"); return
    ferma_odysseus()
    time.sleep(3)
    nota("banco comportamentale avvio (--suite all --repeats 2, budget 128)")
    extra = json.dumps({"reasoning_budget_tokens": 128, "reasoning_budget_message": "Basta ragionare, agisco."})
    with open(OUT / "banco-budget128.log", "a", encoding="utf-8") as fo:
        subprocess.run([str(PY), str(W / "odysseus/scripts/prova_ling_behavior.py"), "--suite", "all", "--repeats", "2",
                        "--extra-payload", extra, "--output", str(out), "--request-timeout", "300"],
                       cwd=str(W / "odysseus"), stdout=fo, stderr=subprocess.STDOUT)
    nota(f"banco fine, file {out.exists()} {out.stat().st_size if out.exists() else 0} byte")


if __name__ == "__main__":
    nota("catena notturna avviata")
    attendi_bracci()
    # B7b: come B7 ma con sweep iniziale degli slot morti (C04-bis)
    if not completo(OUT / "braccio-B7b.txt", "BRACCIO COMPLETO"):
        subprocess.run([sys.executable, str(W / "scripts/onda4-braccio.py"), "B7b", *B7], cwd=str(W),
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        nota("braccio B7b completo")
    # B8: B7b + replay fedele della storia (E08c)
    if not completo(OUT / "braccio-B8.txt", "BRACCIO COMPLETO"):
        subprocess.run([sys.executable, str(W / "scripts/onda4-braccio.py"), "B8", *B8], cwd=str(W),
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        nota("braccio B8 completo")
    suite_alluc("H0", B8)
    suite_alluc("H1", H1)
    banco()
    nota("CATENA COMPLETA")
    (OUT / "catena-fine.flag").write_text("ok", encoding="utf-8")
