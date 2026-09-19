r"""Legge le suite allucinazioni E2E (alluc-TAG.json) e confronta i bracci.

Uso: python scripts/onda4-alluc-leggi.py H0 H1 [...]
Stampa per braccio: esiti per popolazione, punti, Type-1/Type-2, mediana secondi, dedup;
poi i casi di INVENZIONE e UTU con l'inizio del ragionamento e della risposta (per capire
cosa pensa il modello quando inventa); infine i contatori [grounding]/[fresh-required]
dal log stack/odysseus-TAG.log se esiste.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

O = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4")


def braccio(tag):
    f = O / f"alluc-{tag}.json"
    if not f.exists():
        print(f"{tag}: manca {f.name}"); return None
    d = json.loads(f.read_text(encoding="utf-8"))
    T = d["turni"]
    print(f"\n=== {tag}: {len(T)} turni ===")
    print(f"{'pop':9}{'n':>3} {'tool':>5} {'inv':>4} {'ast':>4} {'utu':>4} {'punti':>6} {'T1':>3} {'T2':>3} {'med s':>6} {'pens med':>9} {'num med':>8}")
    for pop in ("entita", "aperta", "calcolo", "negativa"):
        tt = [t for t in T if t["pop"] == pop]
        if not tt:
            continue
        c = Counter(t["esito"] for t in tt)
        med = sorted(t["secondi"] for t in tt)[len(tt) // 2]
        pm = sorted(t["pensiero_caratteri"] for t in tt)[len(tt) // 2]
        nm = sorted(t["numeri"] for t in tt)[len(tt) // 2]
        print(f"{pop:9}{len(tt):3} {c.get('corretta-con-tool', 0) + (c.get('utu', 0)):5} {c.get('invenzione', 0):4} "
              f"{c.get('astensione', 0):4} {c.get('utu', 0):4} {sum(t['punti'] for t in tt):+6d} "
              f"{sum(t['type1'] for t in tt):3} {sum(t['type2'] for t in tt):3} {med:6.0f} {pm:9} {nm:8}")
    print(f"totale punti {sum(t['punti'] for t in T):+d}; dedup {sum(t['dedup'] for t in T)}; "
          f"errori {sum(1 for t in T if t['errore'])}; eventi {Counter(e for t in T for e in t['eventi'])}")
    tools = Counter(s for t in T for s in t["strumenti"])
    print("strumenti:", dict(tools.most_common(8)))
    brutti = [t for t in T if t["esito"] in ("invenzione", "utu")]
    if brutti:
        print(f"\n--- casi da guardare ({len(brutti)}) ---")
        for t in brutti:
            print(f"[{t['esito']}] rip{t['rip']} {t['pop']} | {t['domanda']}")
            print(f"   tool={t['strumenti']} num={t['numeri_es']} astiene={t['astiene']} T1={t['type1']} T2={t['type2']} pens={t['pensiero_caratteri']}c {t['secondi']}s")
            pens = re.sub(r"\s+", " ", t["pensiero"])[:420]
            print(f"   PENSIERO: {pens}")
            print(f"   RISPOSTA: {re.sub(chr(10), ' ', t['testo'])[:300]}")
    log = O / f"stack/odysseus-{tag}.log"
    if log.exists():
        righe = log.read_text(encoding="utf-8", errors="replace").splitlines()
        gr = [r for r in righe if "[grounding]" in r]
        ns = [int(m.group(1)) for r in gr for m in [re.search(r"non_supportati=(\d+)", r)] if m]
        con_tool = [r for r in gr if "tools=0" not in r]
        ns_tool = [int(m.group(1)) for r in con_tool for m in [re.search(r"non_supportati=(\d+)", r)] if m]
        print(f"\nlog: [grounding] turni={len(gr)} con tool={len(con_tool)} non_supportati>0 con tool={sum(1 for x in ns_tool if x > 0)} "
              f"(numeri non supportati totali {sum(ns)}); [fresh-required]={sum(1 for r in righe if '[fresh-required]' in r)}; "
              f"[tool-dedup] hit={sum(1 for r in righe if '[tool-dedup] hit' in r)}; [slot-erase] ok={sum(1 for r in righe if '[slot-erase] slot' in r and ' ok ' in r)}")
        es = [r.split("es=", 1)[1] for r in con_tool if "non_supportati=0" not in r][:6]
        for e in es:
            print("   es:", e[:160])
    return T


if __name__ == "__main__":
    for tag in sys.argv[1:] or ["H0", "H1"]:
        braccio(tag)
