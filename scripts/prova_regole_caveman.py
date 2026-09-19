r"""A/B: le regole del profilo Financial in versione caveman-ultra.

Domanda dell'utente: comprimendo i prompt lunghi in stile telegrafico (via
articoli, riempitivi, frasi complete — MAI il contenuto tecnico) il 9B
degrada oppure no? Qui si monkeypatcha REGOLE_FINANCE con la versione
compressa (~60% piu' corta) e si riesegue il banco diretto identico:
stesso modello, stessi 13 casi, stessa procedura a 3 giri.

Confronto: la corsa normale di prova_modello_finanza.py (regole piene).

Uso:  odysseus\venv\Scripts\python.exe scripts\prova_regole_caveman.py
"""

import importlib.util
import sys

sys.path.insert(0, "d:/assistenteeee/odysseus")

import src.shadowbroker.schemi as schemi  # noqa: E402

# Le stesse regole, caveman-ultra: ogni vincolo conservato, ogni parola di
# contorno morta. ~1.500 caratteri contro ~4.100.
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

print(f"regole piene: {len(schemi.REGOLE_FINANCE)} caratteri · "
      f"caveman: {len(REGOLE_CAVEMAN)} caratteri "
      f"({100 - round(100 * len(REGOLE_CAVEMAN) / len(schemi.REGOLE_FINANCE))}% in meno)\n")

schemi.REGOLE_FINANCE = REGOLE_CAVEMAN

spec = importlib.util.spec_from_file_location(
    "prova", "d:/assistenteeee/scripts/prova_modello_finanza.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
# exec_module non passa da __main__: il banco va lanciato a mano.
m.main()
