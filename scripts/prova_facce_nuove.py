"""Test NON-LLM delle facciate nuove (osint_rischio/sorveglianza/storico) e
della fusione osint_testo dentro osint_notizie.

Mocka il client ShadowBroker e il modulo testo: verifica che ogni handler
SMISTI al comando OpenClaw giusto con gli argomenti giusti, senza modello e
senza backend vivo. Il tier non c'entra: qui non si esegue nulla lato rete.

    d:\\assistenteeee\\odysseus\\venv\\Scripts\\python.exe d:\\assistenteeee\\scripts\\prova_facce_nuove.py
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

os.chdir("d:/assistenteeee/odysseus")
sys.path.insert(0, "d:/assistenteeee/odysseus")

import src.shadowbroker.client as mod_client
import src.shadowbroker.geo as mod_geo
import src.shadowbroker.testo as mod_testo
import src.shadowbroker.briefing as mod_briefing
import src.shadowbroker.store as mod_store
from src.agent_tools.shadowbroker_tools import (
    RischioTool, SorveglianzaTool, StoricoTool, NotizieTool,
)

ESITI = []


class FakeClient:
    def __init__(self):
        self.calls = []

    def comando(self, cmd, args=None, timeout=None):
        self.calls.append((cmd, dict(args or {})))
        return {"fake_data_per": cmd}

    def http_get(self, path, params=None, timeout=None):
        self.calls.append(("GET " + path, dict(params or {})))
        return {"fake_get": path}

    def http_post(self, path, body, timeout=None):
        self.calls.append(("POST " + path, dict(body or {})))
        return {"fake_post": path}

    def avvisi_watchdog(self, timeout=None):
        self.calls.append(("avvisi_watchdog", {}))
        return [{"type": "alert", "msg": "test"}]


def _installa_fake_client():
    fake = FakeClient()
    mod_client.get_client = lambda: fake
    return fake


def verifica(nome, condizione, dettaglio=""):
    ok = bool(condizione)
    ESITI.append(ok)
    segno = "ok  " if ok else "FAIL"
    print(f"  [{segno}] {nome}" + (f" — {dettaglio}" if not ok and dettaglio else ""))


# ── osint_rischio ─────────────────────────────────────────────────────────
def prova_rischio():
    print("osint_rischio")
    f = _installa_fake_client()
    RischioTool().run({}, {})
    verifica("default → gt_top_alerts", f.calls and f.calls[0][0] == "gt_top_alerts",
             f"chiamato {f.calls[:1]}")

    f = _installa_fake_client()
    RischioTool().run({"azione": "dossier", "regione": "Sahel"}, {})
    verifica("dossier → gt_dossier(region=Sahel)",
             f.calls and f.calls[0][0] == "gt_dossier" and f.calls[0][1].get("region") == "Sahel",
             f"chiamato {f.calls[:1]}")

    f = _installa_fake_client()
    RischioTool().run({"azione": "ricalcola"}, {})
    verifica("ricalcola → gt_analyze", f.calls and f.calls[0][0] == "gt_analyze")

    f = _installa_fake_client()
    r = RischioTool().run({"azione": "dossier"}, {})  # regione mancante
    verifica("dossier senza regione → errore, nessuna chiamata",
             not f.calls and r.get("exit_code") == 1)


# ── osint_sorveglianza ────────────────────────────────────────────────────
def prova_sorveglianza():
    print("osint_sorveglianza")
    f = _installa_fake_client()
    SorveglianzaTool().run({"azione": "elenca"}, {})
    verifica("elenca → list_watches", f.calls and f.calls[0][0] == "list_watches")

    f = _installa_fake_client()
    SorveglianzaTool().run({"azione": "rimuovi", "id": "w7"}, {})
    verifica("rimuovi(id=w7) → remove_watch(id=w7)",
             f.calls and f.calls[0][0] == "remove_watch" and f.calls[0][1].get("id") == "w7")

    f = _installa_fake_client()
    SorveglianzaTool().run({"azione": "pulisci"}, {})
    verifica("pulisci → clear_watches", f.calls and f.calls[0][0] == "clear_watches")

    f = _installa_fake_client()
    SorveglianzaTool().run({"azione": "aggiungi", "bersaglio": "RCH01"}, {})
    verifica("aggiungi(bersaglio) → track_entity(query)",
             f.calls and f.calls[0][0] == "track_entity" and f.calls[0][1].get("query") == "RCH01")

    f = _installa_fake_client()
    mod_geo.risolvi_posto = lambda s: (50.45, 30.52)  # Kyiv finto
    SorveglianzaTool().run({"azione": "aggiungi", "luogo": "Kyiv", "raggio_km": 80}, {})
    verifica("aggiungi(luogo) → watch_area(lat,lng,radius)",
             f.calls and f.calls[0][0] == "watch_area"
             and abs(f.calls[0][1].get("lat", 0) - 50.45) < 0.01
             and f.calls[0][1].get("radius_km") == 80,
             f"chiamato {f.calls[:1]}")


# ── osint_storico ─────────────────────────────────────────────────────────
def prova_storico():
    print("osint_storico")
    f = _installa_fake_client()
    StoricoTool().run({"azione": "elenca"}, {})
    verifica("elenca → timemachine_list", f.calls and f.calls[0][0] == "timemachine_list")

    f = _installa_fake_client()
    StoricoTool().run({"azione": "cattura"}, {})
    verifica("cattura → take_snapshot", f.calls and f.calls[0][0] == "take_snapshot")

    f = _installa_fake_client()
    StoricoTool().run({"azione": "riproduci", "id": "s3"}, {})
    verifica("riproduci(id=s3) → timemachine_playback(snapshot_id=s3)",
             f.calls and f.calls[0][0] == "timemachine_playback"
             and f.calls[0][1].get("snapshot_id") == "s3")


# ── osint_notizie: fusione di osint_testo ─────────────────────────────────
def prova_notizie_fusione():
    print("osint_notizie (fusione osint_testo)")
    testo_chiamato = {"urls": None}
    briefing_chiamato = {"si": False}

    def fake_recupera(urls, **kw):
        testo_chiamato["urls"] = list(urls)
        return {"testo": "corpo finto", "urls": urls}

    def fake_notizie(**kw):
        briefing_chiamato["si"] = True
        return {"eventi": []}

    mod_testo.recupera_testo = fake_recupera
    mod_briefing.notizie = fake_notizie

    # con url → percorso lettura, briefing NON chiamato
    testo_chiamato["urls"] = None; briefing_chiamato["si"] = False
    NotizieTool().run({"url": "https://esempio.it/a"}, {})
    verifica("url → recupera_testo, non briefing",
             testo_chiamato["urls"] == ["https://esempio.it/a"] and not briefing_chiamato["si"])

    # con id → risolve store poi legge
    class FakeStore:
        def dettaglio(self, i):
            return {"link": "https://esempio.it/da-id", "_urls_list": ["https://esempio.it/da-id"]}
    mod_store.get_store = lambda: FakeStore()
    testo_chiamato["urls"] = None; briefing_chiamato["si"] = False
    NotizieTool().run({"id": "gdelt:abc"}, {})
    verifica("id → store.dettaglio + recupera_testo",
             testo_chiamato["urls"] == ["https://esempio.it/da-id"] and not briefing_chiamato["si"])

    # senza url/id → briefing normale, niente lettura testo
    testo_chiamato["urls"] = None; briefing_chiamato["si"] = False
    NotizieTool().run({"luogo": "Ucraina"}, {})
    verifica("luogo → briefing.notizie, non recupera_testo",
             briefing_chiamato["si"] and testo_chiamato["urls"] is None)


# ── capacità nuove (20 ago): geocode / cyber / radio / satellite ──────────
def prova_capacita_nuove():
    from src.agent_tools.shadowbroker_tools import (
        GeocodeTool, CyberTool, RadioTool, SatelliteTool, SorveglianzaTool)
    mod_geo.risolvi_posto = lambda s: (48.85, 2.35)  # Parigi finta

    print("osint_geocode")
    f = _installa_fake_client()
    GeocodeTool().run({"azione": "cerca", "luogo": "Kyiv"}, {})
    verifica("cerca → GET /api/geocode/search(q=Kyiv)",
             f.calls and f.calls[0][0] == "GET /api/geocode/search" and f.calls[0][1].get("q") == "Kyiv")
    f = _installa_fake_client()
    GeocodeTool().run({"azione": "inverso", "lat": 50.4, "lng": 30.5}, {})
    verifica("inverso → GET /api/geocode/reverse(lat,lng)",
             f.calls and f.calls[0][0] == "GET /api/geocode/reverse" and f.calls[0][1].get("lat") == 50.4)

    print("osint_cyber")
    for az, path in [("malware", "/api/malware"), ("vulnerabilita", "/api/cyber-threats"),
                     ("rischio_paese", "/api/country-risk")]:
        f = _installa_fake_client()
        CyberTool().run({"azione": az}, {})
        verifica(f"{az} → GET {path}", f.calls and f.calls[0][0] == "GET " + path)
    f = _installa_fake_client()
    CyberTool().run({"azione": "tutto"}, {})
    verifica("tutto → 3 GET", len(f.calls) == 3)

    print("osint_radio")
    f = _installa_fake_client()
    RadioTool().run({"azione": "scanner", "luogo": "Parigi"}, {})
    verifica("scanner(luogo) → GET /api/radio/nearest-list(lat,lng)",
             f.calls and f.calls[0][0] == "GET /api/radio/nearest-list" and abs(f.calls[0][1].get("lat", 0) - 48.85) < 0.01)
    f = _installa_fake_client()
    RadioTool().run({"azione": "kiwisdr", "lat": 41.9, "lng": 12.5}, {})
    verifica("kiwisdr → GET /api/sigint/nearest-sdr", f.calls and f.calls[0][0] == "GET /api/sigint/nearest-sdr")
    f = _installa_fake_client()
    RadioTool().run({"azione": "acars", "aereo": "3c6444"}, {})
    verifica("acars(icao24 hex) → GET /api/aviation/datalink/messages(icao24)",
             f.calls and f.calls[0][0] == "GET /api/aviation/datalink/messages" and f.calls[0][1].get("icao24") == "3c6444")

    print("osint_satellite")
    f = _installa_fake_client()
    SatelliteTool().run({"azione": "termico", "lat": 50.0, "lng": 36.2}, {})
    verifica("termico → GET /api/thermal/verify(lat,lng,radius_km)",
             f.calls and f.calls[0][0] == "GET /api/thermal/verify" and "radius_km" in f.calls[0][1])
    f = _installa_fake_client()
    SatelliteTool().run({"azione": "passaggi", "lat": 50.0, "lng": 36.2}, {})
    verifica("passaggi → POST /api/satellites/overflights(bbox)",
             f.calls and f.calls[0][0] == "POST /api/satellites/overflights"
             and all(k in f.calls[0][1] for k in ("s", "n", "w", "e", "hours")))

    print("osint_sorveglianza avvisi (watchdog proattivo)")
    f = _installa_fake_client()
    SorveglianzaTool().run({"azione": "avvisi"}, {})
    verifica("avvisi → avvisi_watchdog()", f.calls and f.calls[0][0] == "avvisi_watchdog")


if __name__ == "__main__":
    for prova in (prova_rischio, prova_sorveglianza, prova_storico,
                  prova_notizie_fusione, prova_capacita_nuove):
        prova()
    passati = sum(ESITI)
    print("\n" + "=" * 60)
    print(f"{passati}/{len(ESITI)} verifiche passate")
    sys.exit(0 if passati == len(ESITI) else 1)
