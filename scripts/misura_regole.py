import os, sys
sys.path.insert(0, r"d:\assistenteeee\odysseus"); os.chdir(r"d:\assistenteeee\odysseus")
import src.agent_tools
from src.agent_loop import _API_AGENT_RULES

def tok(s): return round(len(s) / 3.6)

righe = _API_AGENT_RULES.strip().split("\n")
mie = [r for r in righe if "toolset" in r or r.strip().startswith("(") or "browser_find" in r]
blocco = "\n".join(mie)

print(f"regole di base COMPLETE : {tok(_API_AGENT_RULES):>4} token ({len(righe)} righe)")
print(f"la parte che ho aggiunto: {tok(blocco):>4} token ({len(mie)} righe)")
print(f"incidenza sul contesto  : {tok(blocco)/49152*100:.2f}%")
print()
print("--- quello che ho aggiunto ---")
print(blocco)
