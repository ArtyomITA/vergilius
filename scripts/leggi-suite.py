"""Legge il JSON di suite-storia-temperatura.py e stampa le tabelle.

Due metriche separate, perche' l'errore ha due direzioni:
  richiamo   = sui casi che DEVONO chiamare, quante volte ha chiamato
  precisione = sui casi che NON devono chiamare, quante volte si e' trattenuto
Piu' le invenzioni, che contano solo sui casi che dovevano chiamare: numeri
precisi prodotti senza aver interrogato niente.
"""
import json, sys
from collections import defaultdict
from pathlib import Path

if len(sys.argv) < 2:
    print("uso: python scripts/leggi-suite.py <file.json>")
    raise SystemExit(1)

dati = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
r = dati["risposte"]
print(f"modello {dati['modello']} · max_tokens {dati['max_tokens']} · "
      f"{len(r)} risposte\n")

storie = sorted({x["storia"] for x in r}, key=lambda s: s != "prosa")
temps = sorted({x["temperatura"] for x in r})

agg = defaultdict(lambda: {"dev_tot": 0, "dev_chiama": 0, "inventa": 0,
                           "no_tot": 0, "no_trattiene": 0, "err": 0,
                           "sec": 0.0, "n": 0})
for x in r:
    a = agg[(x["storia"], x["temperatura"])]
    a["n"] += 1
    a["sec"] += x["secondi"]
    if x["esito"] == "ERRORE":
        a["err"] += 1
        continue
    if x["deve_chiamare"]:
        a["dev_tot"] += 1
        if x["esito"] == "chiama":
            a["dev_chiama"] += 1
        elif x["esito"] == "inventa":
            a["inventa"] += 1
    else:
        a["no_tot"] += 1
        if x["esito"] != "chiama":
            a["no_trattiene"] += 1

print(f"{'storia':7} {'temperatura':24} {'richiamo':>12} {'precisione':>12} "
      f"{'INVENTA':>9} {'err':>4} {'s/risp':>7}")
print("-" * 80)
for s in storie:
    for t in temps:
        a = agg.get((s, t))
        if not a or not a["n"]:
            continue
        ric = f"{a['dev_chiama']}/{a['dev_tot']}" if a["dev_tot"] else "-"
        ricp = f" ({100*a['dev_chiama']//a['dev_tot']}%)" if a["dev_tot"] else ""
        pre = f"{a['no_trattiene']}/{a['no_tot']}" if a["no_tot"] else "-"
        prep = f" ({100*a['no_trattiene']//a['no_tot']}%)" if a["no_tot"] else ""
        print(f"{s:7} {t:24} {ric+ricp:>12} {pre+prep:>12} "
              f"{a['inventa']:>9} {a['err']:>4} {a['sec']/a['n']:>6.1f}s")

# --- dettaglio per caso: dove si rompe ---
print("\ncasi che DEVONO chiamare, per storia e temperatura "
      "(chiamate su ripetizioni):")
casi = [c for c in dict.fromkeys(x["caso"] for x in r)
        if any(x["deve_chiamare"] for x in r if x["caso"] == c)]
intest = "  ".join(f"{t[:4]:>5}" for t in temps)
for s in storie:
    print(f"\n  storia {s}")
    print(f"    {'caso':14} " + "  ".join(f"{t:>22}" for t in temps))
    for c in casi:
        celle = []
        for t in temps:
            sel = [x for x in r if x["caso"] == c and x["storia"] == s
                   and x["temperatura"] == t]
            ch = sum(1 for x in sel if x["esito"] == "chiama")
            inv = sum(1 for x in sel if x["esito"] == "inventa")
            marchio = f"{ch}/{len(sel)}" + (f" ({inv} INV)" if inv else "")
            celle.append(f"{marchio:>22}")
        print(f"    {c:14} " + "  ".join(celle))

# --- falsi positivi: chiamate su casi che non le volevano ---
fp = [x for x in r if not x["deve_chiamare"] and x["esito"] == "chiama"]
if fp:
    print(f"\nchiamate a sproposito ({len(fp)}):")
    for x in fp:
        print(f"  {x['storia']:6} {x['temperatura']:24} {x['caso']:10} "
              f"-> {x['strumento']}")
else:
    print("\nnessuna chiamata a sproposito.")
