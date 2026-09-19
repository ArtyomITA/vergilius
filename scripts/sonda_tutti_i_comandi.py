"""Interroga TUTTI i comandi del canale agente e registra cosa restituiscono.

Serve a comporre gli strumenti sapendo davvero cosa c'e' dentro ognuno, invece
di indovinare. Per ogni comando: se risponde, quanto pesa, che forma ha, quali
chiavi porta, e un campione.

Il rate limiter loro blocca le raffiche: pausa fra le chiamate e ritentativi.
"""

import json
import sys
import time
import urllib.error
import urllib.request

SB = "http://127.0.0.1:8000"
PAUSA = 0.7


def tk(s: str) -> int:
    return round(len(s) / 3.6)


def chiama(cmd, args=None, timeout=90):
    corpo = json.dumps({"cmd": cmd, "args": args or {}}).encode()
    req = urllib.request.Request(
        f"{SB}/api/ai/channel/command", data=corpo,
        headers={"Content-Type": "application/json"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < 2:
                time.sleep(3 * (i + 1))
                continue
            return None, f"HTTP {e.code}"
        except Exception as e:
            if i < 2:
                time.sleep(2)
                continue
            return None, type(e).__name__
    return None, "tentativi esauriti"


# Argomenti sensati per i comandi che ne richiedono. Kyiv come punto di prova.
ARGS = {
    "get_layer_slice": {"layers": ["news"], "limit_per_layer": 3},
    "search_telemetry": {"query": "iran", "compact": True, "confirm_expensive": True},
    "search_news": {"query": "conflict", "compact": True, "limit": 3},
    "find_flights": {"query": "RCH", "compact": True},
    "find_ships": {"query": "carrier", "compact": True},
    "find_entity": {"query": "air force one", "compact": True},
    "get_entity_profile": {"query": "RCH462", "compact": True},
    "get_entity_trail": {"query": "RCH462", "compact": True},
    "correlate_entity": {"query": "RCH462", "compact": True},
    "entities_near": {"lat": 50.45, "lng": 30.52, "radius_km": 300, "compact": True},
    "brief_area": {"lat": 50.45, "lng": 30.52, "radius_km": 300, "compact": True},
    "entity_expand": {"entity_type": "country", "query": "Ukraine"},
    "route_query": {"text": "what is happening in ukraine"},
    "run_playbook": {"playbook": "hot_snapshot"},
    "osint_lookup": {"tool": "ip", "query": "8.8.8.8", "ip": "8.8.8.8"},
    "osint_tools": {},
    "gt_dossier": {"region": "ukraine"},
    "gt_analyze": {"region": "ukraine"},
    "get_ai_pins": {},
    "list_analysis_zones": {},
    "list_watches": {},
    "timemachine_list": {},
    "timemachine_config": {},
    "sar_status": {},
    "sar_anomalies_recent": {"limit": 3},
    "sar_aoi_list": {},
    "sar_scene_search": {"limit": 3},
    "what_changed": {"compact": True},
    "get_summary": {"compact": True},
    "get_layers": {},
    "get_correlations": {"compact": True},
    "get_sigint_totals": {},
    "get_prediction_markets": {},
    "get_fetch_health": {},
    "channel_status": {},
    "gt_top_alerts": {},
    "gt_risk_heatmap": {},
    "gt_micro_rolling": {},
    "gt_rolling_backtest": {},
}

# Da non chiamare: milioni di token, o scrivono qualcosa.
SALTA = {"get_telemetry", "get_slow_telemetry", "get_report",
         "gt_backtest", "gt_rolling_freeze", "gt_rolling_label",
         "place_pin", "place_analysis_zone", "delete_pin", "inject_data",
         "create_layer", "update_layer", "delete_layer", "take_snapshot",
         "add_watch", "remove_watch", "clear_watches", "watch_area",
         "track_entity", "clear_analysis_zones", "delete_analysis_zone",
         "refresh_feed", "osint_sweep", "sar_watch_anomaly", "sar_pin_from_anomaly",
         "sar_aoi_add", "sar_aoi_remove", "timemachine_playback",
         "show_satellite", "show_sentinel", "sar_focus_aoi", "sar_pin_click",
         "sar_anomalies_near", "sar_coverage_for_aoi"}


def forma(v, prof=0):
    if isinstance(v, dict):
        return "{" + ", ".join(sorted(v.keys())[:12]) + ("…}" if len(v) > 12 else "}")
    if isinstance(v, list):
        if not v:
            return "[]"
        return f"[{len(v)} x {forma(v[0], prof+1)}]" if prof < 2 else f"[{len(v)}]"
    return type(v).__name__


def main():
    with urllib.request.urlopen(f"{SB}/api/ai/tools", timeout=30) as r:
        catalogo = json.loads(r.read().decode())
    strumenti = catalogo.get("tools") or catalogo.get("commands") or []
    nomi = sorted({t.get("name") for t in strumenti if isinstance(t, dict) and t.get("name")})
    print(f"catalogo: {len(nomi)} comandi\n")

    risultati = {}
    for nome in nomi:
        if nome in SALTA:
            print(f"  {nome:<26} — saltato di proposito")
            risultati[nome] = {"saltato": True}
            continue
        grezzo, err = chiama(nome, ARGS.get(nome, {}))
        time.sleep(PAUSA)
        if err:
            print(f"  {nome:<26} ERRORE {err}")
            risultati[nome] = {"errore": err}
            continue
        try:
            d = json.loads(grezzo)
            dati = (d.get("result") or {}).get("data", d.get("result"))
        except Exception:
            dati = None
        peso = tk(grezzo)
        ok = dati is not None and dati != {} and dati != []
        # Vuoto non e' errore: e' un layer senza dati adesso.
        vuoto = ""
        if isinstance(dati, dict):
            se_vuoto = all((not v) for v in dati.values()) if dati else True
            if se_vuoto:
                vuoto = "  (contenuto vuoto)"
        print(f"  {nome:<26} {peso:>6} tok  {forma(dati)[:64]}{vuoto}")
        risultati[nome] = {
            "token": peso,
            "forma": forma(dati),
            "chiavi": sorted(dati.keys()) if isinstance(dati, dict) else None,
            "campione": json.dumps(dati, ensure_ascii=False)[:600],
        }

    with open("d:/assistenteeee/scripts/sonda_comandi.json", "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=1)
    print(f"\nsalvato in scripts/sonda_comandi.json ({len(risultati)} comandi)")


if __name__ == "__main__":
    main()
