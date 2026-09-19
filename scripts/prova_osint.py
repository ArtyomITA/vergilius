"""Prova completa della catena OSINT: ponte, briefing, strumenti, mappa.

Non prova che le risposte siano *belle* — prova che ogni pezzo risponda, che
nessuna risposta sfondi il contesto, e che le difese scattino quando devono.
"""

import asyncio
import json
import sys
import time

sys.path.insert(0, r"d:\assistenteeee\odysseus")

CONTESTO = 49152
TETTO_TOKEN = 4000  # nessun singolo risultato deve superarlo

esiti = []


def tk(o):
    return round(len(json.dumps(o, ensure_ascii=False, default=str)) / 3.6)


def prova(nome, fn, tetto=TETTO_TOKEN):
    t0 = time.time()
    try:
        r = fn()
    except Exception as e:
        esiti.append((nome, "ROTTO", 0, 0.0, f"{type(e).__name__}: {str(e)[:70]}"))
        return None
    ms = time.time() - t0
    n = tk(r)
    nota = ""
    stato = "ok"
    if n > tetto:
        stato = "GROSSO"
        nota = f"{n} > tetto {tetto}"
    esiti.append((nome, stato, n, ms, nota))
    return r


def main():
    from src.shadowbroker import briefing, entita, geo, testo
    from src.shadowbroker.client import get_client
    from src.shadowbroker.store import get_store

    print("=" * 78)
    print("1. PONTE")
    print("=" * 78)
    c = get_client()
    prova("stato del canale", lambda: c.stato(), 400)
    prova("riepilogo layer", lambda: c.riepilogo(), 1500)

    # Le difese devono scattare.
    for cmd in ("get_telemetry", "get_slow_telemetry", "get_report"):
        try:
            c.comando(cmd, {})
            esiti.append((f"blocco {cmd}", "ROTTO", 0, 0.0, "NON bloccato!"))
        except ValueError:
            esiti.append((f"blocco {cmd}", "ok", 0, 0.0, "bloccato come previsto"))
        except Exception as e:
            esiti.append((f"blocco {cmd}", "ROTTO", 0, 0.0, f"errore sbagliato: {type(e).__name__}"))

    print("\n" + "=" * 78)
    print("2. GEOGRAFIA")
    print("=" * 78)
    casi = [("kyiv", (50.45, 30.52)), ("50.45,30.52", (50.45, 30.52)),
            ("notizie sull'ucraina", (49.0, 32.0)), ("zzz_inesistente", None)]
    for testo_in, atteso in casi:
        got = geo.risolvi_posto(testo_in)
        ok = (got == atteso) if atteso else (got is None)
        esiti.append((f"posto '{testo_in[:22]}'", "ok" if ok else "ROTTO", 0, 0.0,
                      "" if ok else f"atteso {atteso}, ottenuto {got}"))
    d = geo.distanza_km(50.45, 30.52, 55.75, 37.62)   # Kyiv -> Mosca, ~755 km
    esiti.append(("distanza Kyiv-Mosca", "ok" if 700 < d < 800 else "ROTTO", 0, 0.0,
                  f"{d:.0f} km"))
    # La geometria GeoJSON e' (lng, lat): invertirla finisce in mezzo all'oceano.
    c1 = geo.coordinate_di({"geometry": {"type": "Point", "coordinates": [30.52, 50.45]}})
    esiti.append(("ordine geojson lng/lat", "ok" if c1 == (50.45, 30.52) else "ROTTO",
                  0, 0.0, str(c1)))

    print("\n" + "=" * 78)
    print("3. TITOLI: si marcano, non si cancellano")
    print("=" * 78)
    buoni = ["Russia Pounds Kyiv With Missiles",
             "President Trump Pauses Consideration Of Giving Ukraine Patriot"]
    cattivi = ["2V2I2Yypobgvrnf76Nzytqcqge", "kyivpost.com", "news.webindia123.com", "Articles"]
    for t in buoni:
        ok = not testo.titolo_illeggibile(t)
        esiti.append((f"tiene '{t[:28]}'", "ok" if ok else "ROTTO", 0, 0.0,
                      "" if ok else "scartato per errore!"))
    for t in cattivi:
        ok = testo.titolo_illeggibile(t)
        esiti.append((f"scarta '{t[:28]}'", "ok" if ok else "ROTTO", 0, 0.0,
                      "" if ok else "non riconosciuto"))
    # Nessun articolo va perso: 4 url -> 4 voci, alcune con titolo None.
    voci = testo.titoli_puliti(buoni + cattivi[:2],
                               [f"https://x{i}.com/a" for i in range(4)])
    esiti.append(("nessun articolo perso", "ok" if len(voci) == 4 else "ROTTO", 0, 0.0,
                  f"{len(voci)} voci da 4 url"))

    print("\n" + "=" * 78)
    print("4. BRIEFING")
    print("=" * 78)
    prova("situazione globale", lambda: briefing.situazione(quanti=6))
    prova("allerte", lambda: briefing.allerte(quante=12))
    prova("militare (mondo)", lambda: briefing.militare(quanti=10))
    prova("militare (Europa)", lambda: briefing.militare(luogo="europa", raggio_km=2000, quanti=8))
    prova("notizie Ucraina", lambda: briefing.notizie(luogo="ucraina", giorni=2, quante=6, con_testo=False))
    prova("notizie Gaza + testo", lambda: briefing.notizie(luogo="gaza", giorni=2, quante=4, con_testo=True), 6000)
    prova("notizie a tema", lambda: briefing.notizie(tema="iran", giorni=3, quante=6, con_testo=False))
    prova("zona Kyiv", lambda: briefing.zona("kyiv", raggio_km=300))
    r = prova("zona inesistente", lambda: briefing.zona("zzz_inesistente"), 300)
    if r and "errore" not in r:
        esiti.append(("zona ignota dichiarata", "ROTTO", 0, 0.0, "non ha segnalato l'errore"))

    print("\n" + "=" * 78)
    print("5. ENTITA' (composizione annidata)")
    print("=" * 78)
    prova("scheda base", lambda: entita.scheda("RCH462"), 1200)
    prova("scheda + contesto", lambda: entita.scheda("RCH462", con_contesto=True), 2000)
    prova("scheda inesistente", lambda: entita.scheda("ZZZ_NON_ESISTE"), 1500)

    print("\n" + "=" * 78)
    print("6. STRUMENTI (come li chiama il modello)")
    print("=" * 78)
    from src.agent_tools import TOOL_HANDLERS

    async def chiama(nome, args):
        return await TOOL_HANDLERS[nome](json.dumps(args), {})

    casi = [
        ("osint_situazione", {"quanti": 5}),
        ("osint_allerte", {"quante": 8}),
        ("osint_militare", {"quanti": 8}),
        ("osint_notizie", {"luogo": "ucraina", "giorni": 2, "quante": 5, "con_testo": False}),
        ("osint_zona", {"luogo": "gaza", "raggio_km": 200}),
        ("osint_cerca", {"query": "RCH462"}),
        ("osint_mappa", {"azione": "centra", "luogo": "kyiv", "zoom": 7}),
        ("osint_mappa", {"azione": "livelli", "accendi": ["gdelt", "military_flights"]}),
        ("osint_mappa", {"azione": "ripristina"}),
        ("osint_recon", {"tipo": "ip", "valore": "8.8.8.8"}),
    ]
    for nome, args in casi:
        t0 = time.time()
        try:
            r = asyncio.run(chiama(nome, args))
        except Exception as e:
            esiti.append((f"{nome} {str(args)[:26]}", "ROTTO", 0, 0.0,
                          f"{type(e).__name__}: {str(e)[:60]}"))
            continue
        ms = time.time() - t0
        if r.get("exit_code") != 0:
            esiti.append((f"{nome} {str(args)[:26]}", "ERRORE", 0, ms,
                          str(r.get("error"))[:70]))
            continue
        n = round(len(r.get("output", "")) / 3.6)
        esiti.append((f"{nome} {str(args)[:26]}", "GROSSO" if n > TETTO_TOKEN else "ok",
                      n, ms, ""))

    # Errori attesi.
    for nome, args, perche in [
        ("osint_zona", {}, "senza luogo"),
        ("osint_dettaglio", {"id": "non:esiste"}, "identificativo ignoto"),
        ("osint_recon", {"tipo": "magia", "valore": "x"}, "tipo non ammesso"),
        ("osint_mappa", {"azione": "balla"}, "azione non ammessa"),
    ]:
        r = asyncio.run(chiama(nome, args))
        ok = r.get("exit_code") == 1
        esiti.append((f"{nome} rifiuta ({perche})", "ok" if ok else "ROTTO", 0, 0.0,
                      "" if ok else "avrebbe dovuto fallire"))

    # Il ciclo completo: briefing -> identificativo -> scheda intera.
    r = asyncio.run(chiama("osint_situazione", {"quanti": 3}))
    try:
        d = json.loads(r["output"])
        ident = (d.get("piu_coperti") or [{}])[0].get("id")
        if ident:
            r2 = asyncio.run(chiama("osint_dettaglio", {"id": ident}))
            ok = r2.get("exit_code") == 0
            esiti.append((f"ciclo briefing->dettaglio", "ok" if ok else "ROTTO",
                          round(len(r2.get("output", "")) / 3.6), 0.0,
                          ident if ok else str(r2.get("error"))[:60]))
        else:
            esiti.append(("ciclo briefing->dettaglio", "ROTTO", 0, 0.0, "nessun id nel briefing"))
    except Exception as e:
        esiti.append(("ciclo briefing->dettaglio", "ROTTO", 0, 0.0, str(e)[:60]))

    print("\n" + "=" * 78)
    print("7. SCHEMI E REGISTRO")
    print("=" * 78)
    from src.tool_schemas import FUNCTION_TOOL_SCHEMAS
    from src.agent_tools import TOOL_TAGS, OSINT_TOOL_NAMES
    osint = [s for s in FUNCTION_TOOL_SCHEMAS if s["function"]["name"].startswith("osint_")]
    costo = tk(osint)
    esiti.append(("schemi registrati", "ok" if len(osint) == 10 else "ROTTO",
                  costo, 0.0, f"{len(osint)} strumenti, {costo/CONTESTO*100:.1f}% del contesto"))
    senza = [s["function"]["name"] for s in osint if s["function"]["name"] not in TOOL_HANDLERS]
    esiti.append(("ogni schema ha un handler", "ok" if not senza else "ROTTO", 0, 0.0,
                  ", ".join(senza)))
    senza_tag = [n for n in OSINT_TOOL_NAMES if n not in TOOL_TAGS]
    esiti.append(("ogni handler ha un tag", "ok" if not senza_tag else "ROTTO", 0, 0.0,
                  ", ".join(senza_tag)))

    # ── esito ────────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("ESITO")
    print("=" * 78)
    rotti = [e for e in esiti if e[1] in ("ROTTO", "ERRORE")]
    grossi = [e for e in esiti if e[1] == "GROSSO"]
    for nome, stato, n, ms, nota in esiti:
        segno = {"ok": " ", "GROSSO": "!", "ROTTO": "X", "ERRORE": "X"}[stato]
        peso = f"{n:>6} tok" if n else " " * 10
        tempo = f"{ms:>5.1f}s" if ms > 0.05 else " " * 6
        print(f" {segno} {nome:<38}{peso} {tempo}  {nota}")
    print()
    print(f"  {len(esiti)} controlli — {len(rotti)} rotti, {len(grossi)} oltre il tetto")
    pesi = [e[2] for e in esiti if e[2] > 0]
    if pesi:
        print(f"  peso massimo {max(pesi)} token ({max(pesi)/CONTESTO*100:.1f}% del contesto), "
              f"media {sum(pesi)//len(pesi)}")
    return 1 if rotti else 0


if __name__ == "__main__":
    sys.exit(main())
