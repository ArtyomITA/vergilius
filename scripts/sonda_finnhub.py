"""Cosa ci da' davvero il piano gratuito di Finnhub.

La documentazione e' una pagina JavaScript e i blog si contraddicono. L'unico
modo onesto e' chiamare ogni endpoint con la nostra chiave e guardare cosa
risponde: 200 con dati, 200 vuoto, o 403 perche' e' a pagamento.

Le chiamate sono lente di proposito: il tetto e' 60 al minuto e non ha senso
bruciarlo per una sonda.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, "d:/assistenteeee/shadowbroker/backend")
from services.api_settings import _parse_env_file, OPERATOR_KEYS_ENV_PATH  # noqa: E402

CHIAVE = _parse_env_file(OPERATOR_KEYS_ENV_PATH).get("FINNHUB_API_KEY", "")
BASE = "https://finnhub.io/api/v1"

oggi = date.today()
da = (oggi - timedelta(days=7)).isoformat()
a = oggi.isoformat()
fra_un_mese = (oggi + timedelta(days=30)).isoformat()

PROVE = [
    ("quotazione",            "/quote",                        {"symbol": "RTX"}),
    ("profilo azienda",       "/stock/profile2",               {"symbol": "RTX"}),
    ("notizie generali",      "/news",                         {"category": "general"}),
    ("notizie azienda",       "/company-news",                 {"symbol": "RTX", "from": da, "to": a}),
    ("sentiment notizie",     "/news-sentiment",               {"symbol": "RTX"}),
    ("consigli analisti",     "/stock/recommendation",         {"symbol": "RTX"}),
    ("obiettivi di prezzo",   "/stock/price-target",           {"symbol": "RTX"}),
    ("utili passati",         "/stock/earnings",               {"symbol": "RTX"}),
    ("calendario utili",      "/calendar/earnings",            {"from": a, "to": fra_un_mese}),
    ("calendario IPO",        "/calendar/ipo",                 {"from": a, "to": fra_un_mese}),
    ("calendario economico",  "/calendar/economic",            {}),
    ("insider",              "/stock/insider-transactions",   {"symbol": "RTX"}),
    ("insider sentiment",     "/stock/insider-sentiment",      {"symbol": "RTX", "from": da, "to": a}),
    ("scambi Congresso",      "/stock/congressional-trading",  {"symbol": "RTX"}),
    ("fondi istituzionali",   "/institutional/ownership",      {"symbol": "RTX", "from": da, "to": a}),
    ("azionisti",             "/stock/ownership",              {"symbol": "RTX"}),
    ("bilanci",               "/stock/financials-reported",    {"symbol": "RTX"}),
    ("indicatori",            "/stock/metric",                 {"symbol": "RTX", "metric": "all"}),
    ("archivio SEC",          "/stock/filings",                {"symbol": "RTX"}),
    ("dividendi",             "/stock/dividend",               {"symbol": "RTX", "from": da, "to": a}),
    ("frazionamenti",         "/stock/split",                  {"symbol": "RTX", "from": da, "to": a}),
    ("pari settore",          "/stock/peers",                  {"symbol": "RTX"}),
    ("candele azioni",        "/stock/candle",                 {"symbol": "RTX", "resolution": "D", "from": 1785000000, "to": 1785600000}),
    ("candele cripto",        "/crypto/candle",                {"symbol": "BINANCE:BTCUSDT", "resolution": "D", "from": 1785000000, "to": 1785600000}),
    ("cambio valute",         "/forex/rates",                  {"base": "USD"}),
    ("stato del mercato",     "/stock/market-status",          {"exchange": "US"},),
    ("elenco simboli",        "/stock/symbol",                 {"exchange": "US"}),
    ("ricerca simbolo",       "/search",                       {"q": "lockheed"}),
    ("borse cripto",          "/crypto/exchange",              {}),
    ("ETF profilo",           "/etf/profile",                  {"symbol": "SPY"}),
    ("indice costituenti",    "/index/constituents",           {"symbol": "^GSPC"}),
    ("USA spending",          "/stock/usa-spending",           {"symbol": "RTX", "from": da, "to": a}),
    ("lobbying",              "/stock/lobbying",               {"symbol": "RTX", "from": da, "to": a}),
    ("brevetti",              "/stock/uspto-patent",           {"symbol": "RTX", "from": da, "to": a}),
    ("visti H1B",             "/stock/visa-application",       {"symbol": "RTX", "from": da, "to": a}),
    ("catena fornitura",      "/stock/supply-chain",           {"symbol": "RTX"}),
    ("social sentiment",      "/stock/social-sentiment",       {"symbol": "RTX"}),
]


def misura(dati):
    """Quanto materiale c'e' davvero dentro la risposta."""
    if dati is None:
        return "nullo"
    if isinstance(dati, list):
        return f"lista di {len(dati)}"
    if isinstance(dati, dict):
        for campo in ("data", "results", "earningsCalendar", "ipoCalendar", "result", "financials"):
            if isinstance(dati.get(campo), list):
                return f"{campo}: {len(dati[campo])}"
        vuoto = all(not v for v in dati.values())
        return "dizionario VUOTO" if vuoto else f"dizionario, {len(dati)} campi"
    return type(dati).__name__


def prova(nome, percorso, parametri):
    p = dict(parametri)
    p["token"] = CHIAVE
    url = f"{BASE}{percorso}?{urllib.parse.urlencode(p)}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as r:
            dati = json.loads(r.read().decode())
            residuo = r.headers.get("X-Ratelimit-Remaining", "?")
            return "OK", misura(dati), residuo
    except urllib.error.HTTPError as e:
        corpo = ""
        try:
            corpo = e.read().decode()[:70]
        except Exception:
            pass
        return f"HTTP {e.code}", corpo, "?"
    except Exception as e:
        return "ERRORE", f"{type(e).__name__}: {e}"[:70], "?"


def main():
    print(f"chiave: {'presente' if CHIAVE else 'ASSENTE'}\n")
    print(f"{'endpoint':24} {'stato':10} {'contenuto':28} resto")
    print("-" * 76)
    liberi, pagamento, vuoti = [], [], []
    for nome, percorso, parametri in PROVE:
        stato, contenuto, residuo = prova(nome, percorso, parametri)
        print(f"{nome:24} {stato:10} {contenuto:28} {residuo}")
        if stato == "OK":
            (vuoti if "VUOTO" in contenuto or contenuto in ("lista di 0", "nullo") else liberi).append(nome)
        else:
            pagamento.append(nome)
        # 60 al minuto: una pausa breve e la sonda non disturba i fetcher veri.
        time.sleep(1.1)

    print("\n" + "=" * 76)
    print(f"USABILI SUBITO ({len(liberi)}): {', '.join(liberi)}")
    print(f"\nVUOTI ({len(vuoti)}): {', '.join(vuoti)}")
    print(f"\nNEGATI ({len(pagamento)}): {', '.join(pagamento)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
