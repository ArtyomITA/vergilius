"""Inventario completo dei dati di ShadowBroker.

Domanda a cui rispondere PRIMA di progettare qualsiasi cosa:
  - quali layer hanno dati veri
  - che campi hanno
  - quali portano testo, date, coordinate
  - quali hanno gia' punteggi/classifiche PRECALCOLATI (la cosa piu' importante:
    se il server ha gia' un punteggio di gravita', non serve che lo inventi il
    modello)

Niente stime. Solo quello che esce davvero dalla nostra installazione.
"""

import json
import sys
import urllib.request

SB = "http://127.0.0.1:8000"

# Campi che indicano un giudizio gia' calcolato dal server. Sono la valuta piu'
# preziosa: permettono di ordinare senza far ragionare il modello.
CAMPI_PUNTEGGIO = {
    "risk_score", "oracle_score", "sentiment", "goldstein", "avg_tone",
    "severity", "score", "confidence", "magnitude", "mag", "intensity",
    "frp", "num_articles", "num_mentions", "num_sources", "count",
    "cluster_count", "machine_assessment", "prediction_odds", "urgency",
    "quad_class", "alert", "verification", "votes", "risk_level",
}
CAMPI_TEMPO = {
    "published", "event_date", "date", "time", "timestamp", "ts", "occurred_iso",
    "acq_date", "created_at", "last_sample_date", "from_date", "seendate",
    "datetime", "last_seen", "first_seen",
}
CAMPI_LUOGO = {"lat", "lng", "lon", "coords", "coordinates", "geometry", "place", "location", "name", "region", "country", "city"}
CAMPI_TESTO = {"title", "summary", "description", "text", "body", "headline", "snippet", "place", "name"}


def chiama(cmd, args=None, timeout=120):
    corpo = json.dumps({"cmd": cmd, "args": args or {}}).encode()
    req = urllib.request.Request(
        f"{SB}/api/ai/channel/command", data=corpo,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def elementi_di(valore):
    """Normalizza: una lista di elementi, o le properties di un GeoJSON."""
    if isinstance(valore, list):
        out = []
        for v in valore:
            if isinstance(v, dict) and "properties" in v and "geometry" in v:
                p = dict(v["properties"])
                g = v.get("geometry") or {}
                c = g.get("coordinates")
                if isinstance(c, list) and len(c) >= 2 and isinstance(c[0], (int, float)):
                    p["lng"], p["lat"] = c[0], c[1]
                out.append(p)
            elif isinstance(v, dict):
                out.append(v)
        return out, ("geojson" if valore and isinstance(valore[0], dict)
                     and "properties" in valore[0] else "lista")
    if isinstance(valore, dict):
        if valore.get("type") == "FeatureCollection":
            return elementi_di(valore.get("features") or [])[0], "featurecollection"
        return [valore], "oggetto"
    return [], type(valore).__name__


def main():
    print("=== 1. QUALI LAYER HANNO DATI ===\n")
    conteggi = chiama("get_summary", {"compact": True})["result"]["data"]["counts"]
    vivi = {k: v for k, v in conteggi.items() if isinstance(v, int) and v > 0}
    morti = [k for k, v in conteggi.items() if not isinstance(v, int) or v == 0]
    for k, v in sorted(vivi.items(), key=lambda x: -x[1]):
        print(f"  {k:<26} {v:>7}")
    print(f"\n  vuoti ({len(morti)}): {', '.join(sorted(morti))}")

    print("\n\n=== 2. STRUTTURA DI OGNI LAYER CON DATI ===\n")
    salta = {"satellite_source", "mesh_channel_stats", "meshtastic_map_fetched_at",
             "sigint_totals", "satellite_analysis"}
    riepilogo = {}
    for layer in sorted(vivi):
        if layer in salta:
            continue
        try:
            d = chiama("get_layer_slice", {"layers": [layer], "limit_per_layer": 3})
            grezzo = d["result"]["data"]["layers"].get(layer)
        except Exception as e:
            print(f"  {layer:<26} ERRORE {type(e).__name__}")
            continue
        items, forma = elementi_di(grezzo)
        if not items:
            print(f"  {layer:<26} forma={forma}, nessun elemento leggibile")
            continue
        campi = set()
        for it in items:
            campi |= set(it.keys())
        punteggi = sorted(campi & CAMPI_PUNTEGGIO)
        tempi = sorted(campi & CAMPI_TEMPO)
        luoghi = sorted(campi & CAMPI_LUOGO)
        testi = sorted(campi & CAMPI_TESTO)
        riepilogo[layer] = {
            "n": vivi[layer], "forma": forma, "campi": sorted(campi),
            "punteggi": punteggi, "tempi": tempi, "luoghi": luoghi, "testi": testi,
        }
        print(f"  {layer}  ({vivi[layer]} elementi, {forma}, {len(campi)} campi)")
        print(f"     punteggi : {', '.join(punteggi) or '—'}")
        print(f"     tempo    : {', '.join(tempi) or '—'}")
        print(f"     luogo    : {', '.join(luoghi) or '—'}")
        print(f"     testo    : {', '.join(testi) or '—'}")
        altri = sorted(campi - set(punteggi) - set(tempi) - set(luoghi) - set(testi))
        if altri:
            print(f"     altro    : {', '.join(altri[:14])}{' …' if len(altri) > 14 else ''}")
        print()

    with open("d:/assistenteeee/scripts/inventario_shadowbroker.json", "w", encoding="utf-8") as f:
        json.dump(riepilogo, f, ensure_ascii=False, indent=1)
    print(f"salvato: inventario_shadowbroker.json ({len(riepilogo)} layer)")


if __name__ == "__main__":
    main()
