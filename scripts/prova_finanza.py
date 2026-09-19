"""I tre briefing finanziari sui dati veri, senza il modello di mezzo.

Prima di guardare come si comporta il modello bisogna sapere che cosa gli
arriva. Qui si misura: quanti token pesa ogni briefing, se gli identificativi
sono risolvibili per la mappa, e se le trappole note (duplicati, luoghi
mancanti, codici transazione) sono davvero gestite.

Uso:  odysseus\\venv\\Scripts\\python.exe scripts\\prova_finanza.py
"""

import json
import os
import sys
import time

sys.path.insert(0, "d:/assistenteeee/odysseus")
os.chdir("d:/assistenteeee/odysseus")

from src.shadowbroker import finanza  # noqa: E402
from src.shadowbroker.store import get_store  # noqa: E402

rotti = 0


def token(o) -> int:
    """Stima a ~3,6 caratteri per token. Buona per confronti, non assoluta."""
    return round(len(json.dumps(o, ensure_ascii=False, default=str)) / 3.6)


def verifica(nome, condizione, dettaglio=""):
    global rotti
    if not condizione:
        rotti += 1
    print(f"  {'ok  ' if condizione else 'ROTTO'} {nome}{'  ' + dettaglio if dettaglio else ''}")


def titolo(t):
    print("\n" + "=" * 74)
    print(t)
    print("=" * 74)


# ── mercati ──────────────────────────────────────────────────────────────
titolo("fin_mercati")
t0 = time.time()
m = finanza.mercati()
print(f"  {token(m)} token · {time.time()-t0:.1f}s")

verifica("ha i titoli della difesa", len(m.get("difesa", [])) >= 4,
         f"{len(m.get('difesa', []))} titoli")
verifica("ha la lettura del comparto", "lettura_difesa" in m)
verifica("ha le notizie", len(m.get("notizie", [])) > 0,
         f"{len(m.get('notizie', []))} su {m.get('notizie_disponibili')}")
if m.get("lettura_difesa"):
    l = m["lettura_difesa"]
    print(f"     media {l['media_pct']:+.2f}%  ·  in rialzo {l['in_rialzo']}")
    for c in l["controcorrente"]:
        print(f"     controcorrente: {c['nome']} {c['variazione_pct']:+.2f}%")

# ── appalti ──────────────────────────────────────────────────────────────
titolo("fin_appalti")
t0 = time.time()
a = finanza.appalti(mesi=12, quanti=10)
print(f"  {token(a)} token · {time.time()-t0:.1f}s")

contratti = a.get("contratti", [])
verifica("ha contratti", len(contratti) > 0, f"{len(contratti)}")
verifica("ha scartato duplicati", a.get("duplicati_scartati", 0) >= 0,
         f"{a.get('duplicati_scartati')} scartati su {a.get('totali_trovati')} unici")
con_luogo = [c for c in contratti if "lat" in c]
verifica("almeno met\u00e0 mappabili", len(con_luogo) * 2 >= len(contratti),
         a.get("mappabili", ""))
verifica("tutti hanno un id", all("id" in c for c in contratti))

# Il punto che conta: l'identificativo deve risolversi, altrimenti
# `osint_mappa evidenzia` risponde "non trovato" su cose appena citate.
if contratti:
    store = get_store()
    risolti = sum(1 for c in contratti if store.dettaglio(c["id"]) is not None)
    verifica("gli id si risolvono nel magazzino", risolti == len(contratti),
             f"{risolti}/{len(contratti)}")
    print("\n  primi tre:")
    for c in contratti[:3]:
        dove = c.get("stato_usa") or c.get("luogo", "?")
        print(f"   {c['importo_milioni']:>9.1f} M$  {c['titolo']:5} {dove:22} "
              f"{(c.get('oggetto') or '')[:42]}")

# ── insider ──────────────────────────────────────────────────────────────
titolo("fin_insider")
t0 = time.time()
i = finanza.insider(quanti=10)
print(f"  {token(i)} token · {time.time()-t0:.1f}s")

sent = i.get("sentimento_mensile", [])
mov = i.get("movimenti_recenti", [])
verifica("ha il sentimento mensile", len(sent) > 0, f"{len(sent)} righe")
verifica("ordinato per forza del segnale, non per MSPR nudo",
         all(sent[k]["forza_segnale"] >= sent[k+1]["forza_segnale"]
             for k in range(len(sent)-1)))
verifica("ha i movimenti", len(mov) > 0, f"{len(mov)}")
verifica("ogni movimento dichiara se e\u00e8 decisione di mercato",
         all("decisione_di_mercato" in x for x in mov))
non_mercato = [x for x in mov if not x["decisione_di_mercato"]]
verifica("i codici non-mercato sono spiegati",
         all(x["cosa_significa"] != "codice non catalogato" for x in non_mercato),
         f"{len(non_mercato)} su {len(mov)} non sono decisioni")
if sent:
    print("\n  segnali piu\u00f9 forti:")
    for s in sent[:4]:
        print(f"   {s['nome']:20} {s['mese']}  MSPR {s['mspr']:+7.2f}  "
              f"netto {s['azioni_nette']:+,}  forza {s['forza_segnale']}")

# ── totale ───────────────────────────────────────────────────────────────
titolo("bilancio")
totale = token(m) + token(a) + token(i)
print(f"  i tre briefing insieme: {totale} token ({totale/48000*100:.1f}% di 48K)")
verifica("ognuno sta sotto i 3.000 token",
         max(token(m), token(a), token(i)) < 3000,
         f"max {max(token(m), token(a), token(i))}")

print(f"\n{'tutto a posto' if rotti == 0 else str(rotti) + ' PROVE ROTTE'}")
sys.exit(1 if rotti else 0)
