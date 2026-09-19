r"""Versione C: caveman-ultra su TUTTO cio' che il modello legge.

Non solo le regole (versione B): anche le description di ogni tool del
profilo e il prompt di sistema del banco. Pura ricerca: quanto contenuto
"di contorno" regge un 9B prima di degradare — o migliora, visto che meno
token = meno rumore?

Uso:  odysseus\venv\Scripts\python.exe scripts\prova_regole_caveman_tutto.py
"""

import importlib.util
import sys

sys.path.insert(0, "d:/assistenteeee/odysseus")

import src.shadowbroker.schemi as schemi  # noqa: E402

# ── regole: stessa versione della prova B ────────────────────────────────
REGOLE_CAVEMAN = (
    "CRITICAL: Always answer in Italian.\n"
    "- Start: fin_mercati / fin_appalti / fin_insider. Pre-ranked: narrate, "
    "no re-rank.\n"
    "- Out of scope (weather, recipes, code): ONE sentence, ZERO tool calls.\n"
    "- Act, don't narrate: first reply to data question MUST contain tool "
    "call. Announced tool = call it SAME reply.\n"
    "- Tool holds datum (MSPR, price, amount) -> call tool, never memory.\n"
    "- Map = 2 steps: 1) fetch data (fin_appalti returns id per contract) "
    "2) osint_mappa azione='evidenzia' ids=[...]. Covers 'mostrami sulla "
    "mappa', 'fammi vedere dove', 'nascondi tutto tranne', 'evidenzia', "
    "'centra'. After data, NEXT call = osint_mappa. Table alone = wrong.\n"
    "- 'Nascondi tutto tranne X' = same 2 steps, evidenzia. NEVER "
    "azione='livelli'.\n"
    "- Default news = FINANCIAL (inside fin_mercati). osint_notizie/"
    "osint_testo only for geopolitics cross-check or explicit world-news "
    "request.\n"
    "- 'Which news moved markets' = 1) fin_mercati FIRST (spikes paired "
    "with headlines, ha_notizia flag) 2) osint_notizie ENGLISH keywords "
    "only if geopolitical angle missing.\n"
    "- fin_archivio = past only ('due settimane fa', 'mese scorso'). Live "
    "tools for now.\n"
    "- Every judgement carries its number. No figure, no claim.\n"
    "- Correlation != causation. Never invent link.\n"
    "- Spike ha_notizia:false -> SAY IT.\n"
    "- GREEN up, RED down. Always.\n"
    "- Insider: only P, S = market decisions.\n"
    "- Chart: ```chart {\"type\":\"bar\",\"title\":\"..\",\"labels\":[..],"
    "\"data\":[..]}```. Types bar/line/pie; series:[{name,data}] for multi. "
    "Numbers from tools only.\n"
    "- Missing datum -> DECLARE. Empty feed != calm.\n"
    "CRITICAL: Always answer in Italian."
)

# ── description dei tool: caveman, MA con gli esempi utente in italiano ──
DESCRIZIONI_CAVEMAN = {
    "fin_mercati": (
        "Defense+tech stocks NOW: prices, related news, anomaly pre-found. "
        "For 'come vanno i mercati', 'come sta la difesa', 'cosa si dice "
        "dei titoli'."),
    "fin_appalti": (
        "US federal military contracts: winner, agency, money, WHERE. For "
        "'che commesse militari', 'chi riceve contratti', 'appalti difesa'. "
        "Each contract has 'id' + position -> pass to osint_mappa."),
    "fin_insider": (
        "MSPR + insider moves: who inside defense companies buys/sells. "
        "EVERY TIME you hear 'MSPR', 'insider', 'qualcuno vende', 'cosa "
        "fanno i dirigenti'. MSPR = datum read HERE, not from memory."),
    "fin_archivio": (
        "Archive of past financial events (news, spikes, contracts, "
        "insider). ONLY explicit past questions: 'due settimane fa', "
        "'rispetto al mese scorso'. For 'now' use live tools."),
    "osint_mappa": (
        "Drive the map user watches. ANY request about what is visible: "
        "'mostrami sulla mappa', 'fammi vedere solo X', 'nascondi il "
        "resto', 'centra', 'zooma', 'evidenzia'. azione='centra' moves "
        "view; 'evidenzia' marks ids WITHOUT switching off; 'preset' "
        "curated set (financial, conflitto, infrastruttura); 'livelli' "
        "accendi=[...] keeps ONLY those; 'ripristina' restores. Layers: "
        "military_flights, commercial_flights, private_jets, ships, gdelt, "
        "news, telegram_osint, satellites, earthquakes, firms_fires, "
        "weather_alerts, internet_outages, military_bases, power_plants, "
        "datacenters, frontlines, correlations."),
    "osint_notizie": (
        "World news by place/topic/time window. For 'ultime notizie "
        "sull'Ucraina', 'che succede in Medio Oriente'."),
    "osint_testo": (
        "Fetch REAL article text from its web page. Briefings carry title "
        "only: use this to know what a news item actually says."),
    "osint_dettaglio": (
        "Full record of element already seen in a briefing, every field. "
        "Use the 'id' (e.g. 'gdelt:32e4e3')."),
}

prima_regole = len(schemi.REGOLE_FINANCE)
prima_desc = 0
dopo_desc = 0
for s in schemi.FINANCE_TOOL_SCHEMAS + schemi.OSINT_TOOL_SCHEMAS:
    f = s["function"]
    if f["name"] in DESCRIZIONI_CAVEMAN:
        prima_desc += len(f["description"])
        f["description"] = DESCRIZIONI_CAVEMAN[f["name"]]
        dopo_desc += len(f["description"])

schemi.REGOLE_FINANCE = REGOLE_CAVEMAN

print(f"regole: {prima_regole} -> {len(REGOLE_CAVEMAN)} caratteri · "
      f"description (8 tool): {prima_desc} -> {dopo_desc} caratteri\n")

spec = importlib.util.spec_from_file_location(
    "prova", "d:/assistenteeee/scripts/prova_modello_finanza.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
# Anche il prompt di sistema del banco, caveman.
m.SISTEMA = ("Risk analyst. Finance-intel tools available. Call the right "
             "tool. Answer in Italian.\n\n" + REGOLE_CAVEMAN)
m.main()
