r"""Prova LFM2.5-2.6B al posto di Ling (settembre 2026). Catena riprendibile, stato riga per riga in
D:\vergilius-lab\ricerche\opt-1080\misure\onda4\prova-lfm.txt

  LFM1   12 casi Financial x3 + core, controlli ACCESI (= vergilius.env di produzione)
  LH1    suite allucinazioni singolo turno (entita/aperta/calcolo/negativa), controlli ACCESI
  LH1m   suite multi-turno, controlli ACCESI
  LH0    suite singolo turno, controlli anti-invenzione SPENTI (regole, required, rilancio): il modello da solo
  LH0m   multi-turno, controlli SPENTI
  LingC  SOLO popolazione "calcolo" con Ling e controlli accesi: quanti rilanci a torto sui calcoli
Prima di ogni suite controlla che il modello risponda davvero (lezione H4: suite girata a modello spento).
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

W = Path(r"d:\assistenteeee")
OUT = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4")
STATO = OUT / "prova-lfm.txt"
PY = W / "odysseus/venv/Scripts/python.exe"
CFG_LFM = "C:/vergilius-build/config-lfm.yaml"

BASE = ["ODYSSEUS_TOOLSET_FREEZE=1", "ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=128",
        "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096", "ODYSSEUS_TOOL_ROUND_REASONING_MESSAGE=Basta ragionare, agisco.",
        "ODYSSEUS_HISTORY_REPLAY=1", "ODYSSEUS_MEMORY_TAIL=1",
        "ODYSSEUS_TOOL_OUTPUT_CHARS=3000", "ODYSSEUS_HISTORY_TOOL_CHARS=3300",
        "ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_GROUNDING_CHECK=1"]
ACCESI = BASE + ["ODYSSEUS_GROUNDING_RULES=1", "ODYSSEUS_FRESH_REQUIRED=1", "ODYSSEUS_GROUNDING_RETRY=1"]
SPENTI = BASE


def nota(msg):
    riga = f"{time.strftime('%H:%M:%S')} {msg}"
    print(riga, flush=True)
    with open(STATO, "a", encoding="utf-8") as f:
        f.write(riga + "\n")


def completo(f, marca):
    return f.exists() and marca in f.read_text(encoding="utf-8", errors="replace")


def stack(azione, cfg=None):
    env = os.environ.copy()
    if cfg:
        env["ONDA4_SWAP_CONFIG"] = cfg
    else:
        env.pop("ONDA4_SWAP_CONFIG", None)
    r = subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"), azione],
                       capture_output=True, text=True, env=env, cwd=str(W))
    nota(f"stack {azione}: " + ((r.stdout.strip().splitlines() or ["?"])[-1])[:120])
    if azione == "avvia" and "RIFIUTO" in r.stdout:
        nota("stack non avviato: CATENA INTERROTTA (niente suite a vuoto)")
        sys.exit(2)


def modello_vivo():
    corpo = json.dumps({"model": "ling", "messages": [{"role": "user", "content": "Rispondi solo: ok"}],
                        "max_tokens": 200}).encode()
    try:
        req = urllib.request.Request("http://127.0.0.1:8012/v1/chat/completions", data=corpo,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read().decode())
        m = d["choices"][0]["message"]
        vivo = bool((m.get("content") or "") + (m.get("reasoning_content") or ""))
        nota(f"modello vivo: {vivo} ({d.get('model', '?')[-40:]})")
        return vivo
    except Exception as e:
        nota(f"modello NON risponde: {type(e).__name__} {str(e)[:100]}")
        return False


def riavvia(tag, env):
    r = subprocess.run([sys.executable, str(W / "scripts/onda4-stack-prova.py"), "riavvia-odysseus", tag, *env],
                       capture_output=True, text=True, cwd=str(W))
    ok = "pronto: True" in r.stdout
    nota(f"odysseus {tag} riavviato: {ok}")
    if ok:
        time.sleep(5)
    return ok


def suite(tag, env, multi=False, solo="", rip=3):
    if completo(OUT / f"alluc-{tag}.txt", "SUITE COMPLETA"):
        nota(f"{tag} gia' completa"); return
    if not riavvia(tag, env) or not modello_vivo():
        nota(f"{tag} SALTATA"); return
    nota(f"{tag} avvio suite" + (" multi" if multi else "") + (f" solo={solo}" if solo else ""))
    cmd = [str(PY), str(W / "scripts/suite-allucinazioni-e2e.py"), "--tag", tag, "--riprendi", "--rip", str(rip)]
    if multi:
        cmd.append("--multi")
    if solo:
        cmd += ["--solo", solo]
    subprocess.run(cmd, cwd=str(W), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    nota(f"{tag} fine")


def braccio(tag, env):
    if completo(OUT / f"braccio-{tag}.txt", "BRACCIO COMPLETO"):
        nota(f"{tag} gia' completo"); return
    if not modello_vivo():
        nota(f"{tag} SALTATO"); return
    subprocess.run([sys.executable, str(W / "scripts/onda4-braccio.py"), tag, *env], cwd=str(W),
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    nota(f"braccio {tag} completo")


if __name__ == "__main__":
    nota("prova LFM avviata")
    stack("ferma")
    (OUT / "stack/pids.json").unlink(missing_ok=True)
    stack("avvia", CFG_LFM)
    # 19 set, dopo la patch calcoli (rilevatore, quotazione per nome, regola "Arithmetic is YOUR job").
    # LH1 (pre-patch, tutto acceso) e LH1bis (replica involontaria) restano come riferimento del problema.
    PULITO = ["ODYSSEUS_HISTORY_REPLAY=1", "ODYSSEUS_MEMORY_TAIL=1",
              "ODYSSEUS_TOOL_OUTPUT_CHARS=8000", "ODYSSEUS_HISTORY_TOOL_CHARS=8800",
              "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096",
              "ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_GROUNDING_CHECK=1"]
    suite("LP0", PULITO)                       # infrastruttura si', restrizioni no
    suite("LH0", SPENTI)                       # orchestrazione si', anti-invenzione no
    suite("LC1", ACCESI, solo="calcolo")       # tutto acceso, rilevatore corretto: i calcoli passano?
    suite("LE1", ACCESI, solo="entita")
    braccio("LFM1", ACCESI)
    suite("LP0m", PULITO, multi=True, rip=2)
    suite("LH1m", ACCESI, multi=True, rip=2)
    # confronto Ling sui soli casi di calcolo: stack di nuovo con la config di produzione
    stack("ferma")
    (OUT / "stack/pids.json").unlink(missing_ok=True)
    stack("avvia")
    suite("LingC", ACCESI, solo="calcolo")
    stack("ferma")
    nota("PROVA LFM FINITA")
