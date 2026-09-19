r"""Catena della suite lunga su LFM2.5-2.6B (19 set 2026). Riprendibile; stato in misure/onda4/prova-lfm-lunga.txt

  L1  LIBERO     proposta completa: niente freeze/required/regole grounding/rilancio; budget 256; output 8000;
                 nudge max 1 senza chiamata forzata e senza regex del futuro; [state] spento; nota tracce spenta;
                 regole di profilo "libere"
  L2  L1 + vincoli nascosti riaccesi ([state], nudge 3 + forzata + futuro, nota tracce)   -> isola C2/C3/C4/C9
  L3  L1 + regole di profilo piene (testo scritto per Ling)                              -> isola E1
  L4  L1 con budget di pensiero 512                                                      -> isola B2

Uso: python scripts\prova-lfm-lunga.py [secco]     secco = solo L1, scenario 1, 2 turni, poi ferma lo stack
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("plfm", str(Path(__file__).with_name("prova-lfm.py")))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
P.STATO = P.OUT / "prova-lfm-lunga.txt"

INFRA = ["ODYSSEUS_HISTORY_REPLAY=1", "ODYSSEUS_MEMORY_TAIL=1",
         "ODYSSEUS_TOOL_OUTPUT_CHARS=8000", "ODYSSEUS_HISTORY_TOOL_CHARS=8800",
         "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096",
         "ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_GROUNDING_CHECK=1",
         "ODYSSEUS_TOOL_ROUND_REASONING_MESSAGE=Basta ragionare, agisco."]
LIBERI = ["ODYSSEUS_INTENT_NUDGE_MAX=1", "ODYSSEUS_INTENT_NUDGE_FORCE=0", "ODYSSEUS_INTENT_NUDGE_FUTURO=0",
          "ODYSSEUS_STATE_REMINDER=0", "ODYSSEUS_TRACE_HINT=0"]
VINCOLI = ["ODYSSEUS_INTENT_NUDGE_MAX=3", "ODYSSEUS_INTENT_NUDGE_FORCE=1", "ODYSSEUS_INTENT_NUDGE_FUTURO=1",
           "ODYSSEUS_STATE_REMINDER=1", "ODYSSEUS_TRACE_HINT=1"]
BRACCI = {
    "L1": INFRA + LIBERI + ["ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=256", "VERGILIUS_REGOLE_PROFILO=libere"],
    "L2": INFRA + VINCOLI + ["ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=256", "VERGILIUS_REGOLE_PROFILO=libere"],
    "L3": INFRA + LIBERI + ["ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=256", "VERGILIUS_REGOLE_PROFILO=piene"],
    "L4": INFRA + LIBERI + ["ODYSSEUS_TOOL_ROUND_REASONING_BUDGET=512", "VERGILIUS_REGOLE_PROFILO=libere"],
}


def lunga(tag, env, extra=()):
    if P.completo(P.OUT / f"lunga-{tag}.txt", "SUITE COMPLETA") and not extra:
        P.nota(f"{tag} gia' completa"); return
    if not P.riavvia(tag, env) or not P.modello_vivo():
        P.nota(f"{tag} SALTATA"); return
    log = P.OUT / f"stack/odysseus-{tag}.log"
    if log.exists() and "error while attempting to bind" in log.read_text(encoding="utf-8", errors="replace")[-20000:]:
        P.nota(f"{tag} SALTATA: errore di bind nel log, istanza sbagliata"); return
    P.nota(f"{tag} avvio suite lunga {' '.join(extra)}")
    subprocess.run([str(P.PY), str(P.W / "scripts/suite-lunga-e2e.py"), "--tag", tag, "--riprendi", *extra],
                   cwd=str(P.W), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    P.nota(f"{tag} fine")


if __name__ == "__main__":
    secco = len(sys.argv) > 1 and sys.argv[1] == "secco"
    P.nota("catena lunga avviata" + (" (prova a secco)" if secco else ""))
    P.stack("ferma")
    (P.OUT / "stack/pids.json").unlink(missing_ok=True)
    P.stack("avvia", P.CFG_LFM)
    if secco:
        lunga("L1", BRACCI["L1"], ("--scenari", "1", "--turni", "2"))
    else:
        for tag in ("L1", "L2", "L3", "L4"):
            lunga(tag, BRACCI[tag])
    P.stack("ferma")
    P.nota("CATENA LUNGA FINITA" + (" (secco)" if secco else ""))
