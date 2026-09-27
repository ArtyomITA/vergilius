# PROVE: quotazione-titolo (mai iniettato; lo legge il revisore)

| affermazione nella skill | fonte (file:riga) | operazioni del banco |
|---|---|---|
| fin_mercati accetta `titolo` (stringa, UNA azienda/ticker) e `quante_notizie` (intero) | odysseus/src/shadowbroker/schemi.py:481-499 (schema) | in attesa operazioni-finanza.json |
| con `titolo`, l'esito e' avvolto in `titolo_richiesto` con `nome_chiesto` a fianco | odysseus/src/shadowbroker/finanza.py:294 (init `{"titolo_richiesto": q}`), 497-498 (`fuori = {"titolo_richiesto": quota, "nome_chiesto": _chiesto, **fuori}`) | |
| campi dentro la quotazione: `disponibile`, `prezzo`, `valuta`, `variazione_percento`, `variazione_in_valuta`, `avviso` | finanza.py:278-279 (valuta), 344-345 (fonte Finnhub, valuta USD), 349-350 (fonte Yahoo, valuta letta), 359-366 (disponibile=True, prezzo, variazione_percento, variazione_in_valuta) | |
| `avviso` compare quando un nome simile ha quotato un altro simbolo: dire quale si e' quotato | finanza.py:326-332 (`fuori["avviso"] = f"quotato {sym}. Esistono altri titoli con nome simile..."`) | |
| `disponibile: false` porta un `motivo`: mai stimare il prezzo | finanza.py:354-357 (`fuori.update(disponibile=False, motivo="quotazione non disponibile...; dillo all'utente, non stimare il prezzo")`), 296 (titolo vuoto), 369 (errore della fonte dati) | |
| differenza o rapporto fra due prezzi: calcola con l'espressione, mai a mente | odysseus/src/agent_tools/calc_tools.py:147-177 (funzione `calcola`), 217-259 (schema, `espressioni` obbligatorio) | |
| periodo passato: `fin_archivio` con `query` (obbligatoria) e `giorni` opzionale | schemi.py:545-563 (schema, `required: ["query"]`) | |
| `titolo` e' UNA sola azienda, mai un settore o un elenco | schemi.py:496 (descrizione: "ONE company name or ticker, never a sector or a list") | |
| EUR (.MI) e USD non si confrontano senza un cambio dato dall'utente | finanza.py:279, 344-345, 349-350 (valuta diversa per fonte/borsa); nessun tasso di cambio live nel codice: dedotto | |
| un grafico e' un blocco ```chart nella risposta, mai una chiamata a uno strumento | odysseus/src/shadowbroker/schemi.py:213-214 (descrizione osint_mappa: "Not for charts, tables or any drawing: a chart is a ```chart block in your reply, not a tool call.") | famiglia "grafico-chart" in operazioni-finanza.json |

Token (verifica-skill.py, tokenizzatore GGUF LFM2.5): 298 iniettati, descrizione 24.
