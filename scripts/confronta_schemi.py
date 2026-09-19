import json, os, sys
sys.path.insert(0, r"d:\assistenteeee\odysseus"); os.chdir(r"d:\assistenteeee\odysseus")
import src.agent_tools  # risolve l'import circolare caricando prima il pacchetto
from src.tool_schemas import FUNCTION_TOOL_SCHEMAS

def tok(s): return round(len(s) / 3.6)

nativi = []
for s in FUNCTION_TOOL_SCHEMAS:
    f = s.get("function", s)
    nativi.append((f["name"], tok(json.dumps(s)), tok(f.get("description", ""))))

nativi.sort(key=lambda x: -x[1])
tot = sum(n[1] for n in nativi)
print(f"STRUMENTI NATIVI DI ODYSSEUS: {len(nativi)}")
print(f"  totale schemi    : {tot} token")
print(f"  media            : {round(tot/len(nativi))} token/strumento")
print(f"  descrizione media: {round(sum(n[2] for n in nativi)/len(nativi))} token")
print("  i 5 piu' grassi:")
for n, t, d in nativi[:5]:
    print(f"    {n:<26} {t:>5} tot (descr. {d})")
print("  i 5 piu' magri:")
for n, t, d in nativi[-5:]:
    print(f"    {n:<26} {t:>5} tot (descr. {d})")
