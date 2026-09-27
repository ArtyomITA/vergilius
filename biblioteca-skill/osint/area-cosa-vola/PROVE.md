# PROVE: area-cosa-vola (mai iniettato; lo legge il revisore)

| affermazione nella skill | fonte (file:riga) | note |
|---|---|---|
| osint_militare vuole luogo, raggio_km, quanti | odysseus/src/shadowbroker/schemi.py:77-93 (schema) | nessun campo required |
| raggio_km clamp 10-10000 (nessun default nell'handler: None senza valore); quanti default 15, clamp 3-40 | odysseus/src/agent_tools/shadowbroker_tools.py:243-250 (`MilitareTool.run`, `_raggio_chiesto` righe 68-77 torna None se omesso, `_numero`) | il vero default 1000 vive nel briefing, non qui: `_raggio(raggio_km, posto, 1000)` in odysseus/src/shadowbroker/briefing.py:799 (corretto dopo revisione di FINANZA, chat #24) |
| luogo sconosciuto = dati mondo intero, non errore | odysseus/src/shadowbroker/schemi.py:87 ("Empty = whole world"); comportamento confermato dal referto pipeline-osint-finanza.md sezione 3, riga "osint_militare" trappole | briefing.militare non alza errore su luogo non risolto, torna il mondo |
| osint_geocode azione=cerca, luogo (required); NESSUN campo quanti nello schema | odysseus/src/shadowbroker/schemi.py:344-362 | `quanti` esiste nell'handler (riga sotto) ma e' fuori schema: non va passato |
| la chiave del risultato e' "risultati" (non "results"), presa da /api/geocode/search con limit 5 (1-10) | odysseus/src/agent_tools/shadowbroker_tools.py:922-944 (`GeocodeTool.run`, riga 943 `int(_numero(a.get("quanti"), 5, 1, 10))`, riga 944 `"risultati": r`) | correzione rispetto alla bozza pipeline-osint-finanza.md che scriveva "results[0]" in inglese: il campo vero e' italiano |
| "Mar Nero", "Black Sea", "Bosforo" non risolti dal geocoder locale | D:\vergilius-lab\ricerche\decisori\materiale-skill\pipeline-osint-finanza.md sezione 3, tabella risoluzione luoghi [verificato con geo.risolvi_posto] | da qui la scelta di centro manuale per i mari |
| osint_mappa azione=centra e' sola vista, nessuna approvazione | odysseus/src/shadowbroker/schemi.py:197-243 (schema, azione enum); D:\vergilius-lab\ricerche\decisori\materiale-skill\pipeline-osint-finanza.md sezione 1 punto 8 [codice, tool_capabilities.py:481-487] | evidenzia/livelli/preset invece armano il varco: qui non usati |
| zoom default 6, per un punto stretto si preferisce 5 | odysseus/src/shadowbroker/schemi.py:230 ("1 world, 6 country, 10 city") | scelta di skill: 5 per un'area larga tipo mare |

Token (vocabolario LFM2.5, resa senza nome): da misurare con verifica-skill.py (cancello 1), riportato in chat.
