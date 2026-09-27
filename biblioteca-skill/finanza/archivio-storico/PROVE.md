# PROVE: archivio-storico (mai iniettato; lo legge il revisore)

| affermazione nella skill | fonte (file:riga) | operazioni del banco |
|---|---|---|
| fin_archivio accetta `query` (obbligatoria), `quanti`, `giorni` | odysseus/src/shadowbroker/schemi.py:545-563 (schema, `required: ["query"]`) | famiglia "archivio-storico" in operazioni-finanza.json |
| la facciata rifiuta la chiamata senza query con un errore esplicito | odysseus/src/agent_tools/shadowbroker_tools.py:713-718 (`ArchivioTool.run`: `if not query: return _errore("fin_archivio: serve una query...")`) | |
| campi di ogni risultato: `testo`, `tipo`, `ticker`, `quando`, `fonte`, `distanza` | odysseus/src/shadowbroker/archivio.py:325-333 (`risultati.append({"testo":doc,"tipo":...,"ticker":...,"quando":...,"fonte":...,"url":...,"distanza":...})`) | |
| `vuoto` compare quando non ci sono risultati: non significa che non sia successo nulla | archivio.py:341-346 (`fuori["vuoto"] = "nessun documento per questa ricerca. Archivio cresce con l'uso... Non significa che non sia successo nulla."`) | |
| l'archivio contiene solo cio' che e' gia' passato da un briefing live: normale che manchi qualcosa | archivio.py:250-271 (`ingerisci_da_briefing`: aggancio opportunistico dai briefing mercati/appalti/insider) | |
| lo storico dei prezzi e' solo l'evento "picco" datato, mai una quotazione dal vivo | archivio.py:170-189 (`ingerisci_picchi`: "l'unica forma storica di un prezzo"), righe 14-19 del docstring (14-19: "il prezzo NON entra... l'unica forma in cui un prezzo ha senso storico") | |
| `distanza` e' un punteggio di similarita' (piu' basso = piu' vicino), non una garanzia di corrispondenza sulla data | archivio.py:332 (`"distanza": round((r.get("distances")...)[i], 3)`), 335 (`risultati.sort(key=lambda x: x.get("distanza") or 9)`) | |

Token (verifica-skill.py, tokenizzatore GGUF LFM2.5): 274 iniettati, descrizione 24.
