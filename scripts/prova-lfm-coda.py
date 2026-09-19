r"""Coda della prova LFM: aspetta "PROVA LFM FINITA", applica a stack SPENTO la patch calcoli
(numeri della domanda e numeri derivati = supportati; quotazione_titolo con watchlist nota),
poi rigira solo le popolazioni toccate dalle correzioni, con LFM:
  LC1  calcolo, controlli accesi     LE1  entita, controlli accesi
  LP0/LP0m  suite intera e multi-turno, braccio PULITO (infrastruttura si', restrizioni no)
Stato in prova-lfm.txt (stesso file).
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
W = Path(r"d:\assistenteeee")
OUT = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4")
PATCH = Path(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\D--assistenteeee\f6c9077b-17ce-49ac-bab8-a7efc9b9b9f3\scratchpad\patch_calcoli.py")

import importlib.util
spec = importlib.util.spec_from_file_location("pl", str(W / "scripts/prova-lfm.py"))
pl = importlib.util.module_from_spec(spec); spec.loader.exec_module(pl)

if __name__ == "__main__":
    pl.nota("coda avviata: aspetto la fine della prova LFM")
    while not pl.completo(pl.STATO, "PROVA LFM FINITA"):
        time.sleep(30)
    pl.stack("ferma")
    marker = W / "odysseus/src/agent_loop.py"
    if "_derivato" not in marker.read_text(encoding="utf-8", errors="replace"):
        r = subprocess.run([sys.executable, str(PATCH)], cwd=str(W), capture_output=True, text=True)
        pl.nota("patch calcoli: " + ((r.stdout.strip().splitlines() or [r.stderr.strip()[-160:]])[-1]))
    ok = all(subprocess.run([sys.executable, "-c", "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())",
                             str(W / f)], capture_output=True).returncode == 0
             for f in ("odysseus/src/agent_loop.py", "odysseus/src/shadowbroker/finanza.py"))
    if not ok:
        pl.nota("sorgenti NON compilano dopo la patch: coda interrotta"); sys.exit(1)
    (OUT / "stack/pids.json").unlink(missing_ok=True)
    pl.stack("avvia", pl.CFG_LFM)
    pl.suite("LC1", pl.ACCESI, solo="calcolo")
    pl.suite("LE1", pl.ACCESI, solo="entita")
    # LP0: braccio PULITO. Resta l'infrastruttura (replay, memorie in coda, slot, tetto di sicurezza),
    # via tutto cio' che restringe il modello: congelamento strumenti, budget di pensiero, required,
    # regole e rilancio grounding. Taglio output tool alzato a 8000/8800 (allineato turno/storia).
    PULITO = ["ODYSSEUS_HISTORY_REPLAY=1", "ODYSSEUS_MEMORY_TAIL=1",
              "ODYSSEUS_TOOL_OUTPUT_CHARS=8000", "ODYSSEUS_HISTORY_TOOL_CHARS=8800",
              "ODYSSEUS_AGENT_MAX_TOKENS_CAP=4096",
              "ODYSSEUS_LOCAL_SLOT_PIN=1", "ODYSSEUS_LOCAL_SLOT_ERASE=1", "ODYSSEUS_GROUNDING_CHECK=1"]
    pl.suite("LP0", PULITO)
    pl.suite("LP0m", PULITO, multi=True, rip=2)
    pl.stack("ferma")
    pl.nota("CODA LFM FINITA")
