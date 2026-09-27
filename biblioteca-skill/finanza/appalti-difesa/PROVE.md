# PROVE: appalti-difesa (mai iniettato; lo legge il revisore)

| affermazione nella skill | fonte (file:riga) | operazioni del banco |
|---|---|---|
| fin_appalti accetta `titolo`, `mesi`, `quanti`; sei contractor validi RTX, LMT, NOC, GD, BA, PLTR | odysseus/src/shadowbroker/schemi.py:504-520 (schema); finanza.py:50 (`DIFESA = ("RTX","LMT","NOC","GD","BA","PLTR")`) | in attesa operazioni-finanza.json |
| campi per contratto: `assegnataria`, `importo_milioni`, `agenzia`, `oggetto`, `stato_usa` o `luogo`, `id` | finanza.py:608-625 (costruzione di `v`, `luogo = "non dichiarato"` se manca lo stato) | |
| gli `id` vengono registrati nel magazzino apposta per `osint_mappa evidenzia` | finanza.py:629-633 (`ids = get_store().registra("appalti", per_magazzino)`); commento riga 564-567 | |
| osint_mappa evidenzia vuole `ids` (elenco), mai ticker o nomi azienda | schemi.py:223-235 (`azione` enum incl. "evidenzia", `ids`: "Never stock tickers or company names"), 240 (`required: ["azione"]`) | |
| un `titolo` fuori dai sei e' scartato in silenzio: torna l'elenco di tutti e sei | odysseus/src/agent_tools/shadowbroker_tools.py:680-690, in particolare 683-685 (`if titolo and str(titolo).upper() not in finanza.DIFESA: titolo = None`) | |
| dati trimestrali: sotto i 3 mesi il risultato puo' essere vuoto | finanza.py:656-660 (`fuori["non_osservabile"] = "nessun contratto nella finestra. Dati trimestrali: allarga mesi prima di concludere."`) | |
| `importo_milioni` e' il valore massimo potenziale del contratto, non la spesa reale | finanza.py:652 (`"nota_importo": "importo = valore potenziale massimo del contratto, non speso"`) | |

Token (verifica-skill.py, tokenizzatore GGUF LFM2.5): 294 iniettati, descrizione 23.
