# PROVE: luogo-cosa-succede

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_zona: luogo (required), raggio_km; nessun quante/quanti nello schema | odysseus/src/shadowbroker/schemi.py:116-131 | `per_layer` esiste nell'handler ma non nello schema (riga sotto): non citarlo nella skill |
| luogo required, errore esplicito se assente; raggio clamp 5-3000 (default vero 200 nel briefing); per_layer default 5 (1-15) fuori schema | odysseus/src/agent_tools/shadowbroker_tools.py:263-273 (`ZonaTool.run`, clamp); odysseus/src/shadowbroker/briefing.py:1065 (`_raggio(raggio_km, posto, 200)`, default vero) | errore esplicito confermato (non mondo intero, diverso da militare/allerte); citazione corretta dopo revisione FINANZA #24 |
| osint_notizie: luogo, soggetto, tema, giorni, raggio_km, quante, url, id, leggi_testo | odysseus/src/shadowbroker/schemi.py:47-73 | quante non quanti |
| giorni default 2 (0,25-30), quante default 8 (3-25), leggi_testo vero se omesso; raggio clamp 10-5000 (default vero 400 nel briefing) | odysseus/src/agent_tools/shadowbroker_tools.py:210-218 (clamp/giorni/quante/leggi_testo); odysseus/src/shadowbroker/briefing.py:516 (`_raggio(raggio_km, posto, 400)`, default vero) | la skill fissa leggi_testo false per restare sotto il tetto di 8000 caratteri |
| osint_allerte: luogo, raggio_km, quante | odysseus/src/shadowbroker/schemi.py:97-112 | quante non quanti, come notizie |
| raggio clamp 10-10000 (default vero 1000 nel briefing); quante default 15 (3-30) | odysseus/src/agent_tools/shadowbroker_tools.py:253-260 (`AllerteTool.run`, clamp); odysseus/src/shadowbroker/briefing.py:926 (`_raggio(raggio_km, posto, 1000)`, default vero) | la skill sceglie 300 esplicito per restare locale |
| osint_situazione: quanti, con_testo | odysseus/src/shadowbroker/schemi.py:28-43 | quanti qui, non quante: coerente con militare |
| quanti default 8 (3-20), con_testo default False | odysseus/src/agent_tools/shadowbroker_tools.py:168-175 (`SituazioneTool.run`) | |
| Romania -> Roma, Nigeria -> Niger (corrispondenza a sottostringa) | D:\vergilius-lab\ricerche\decisori\materiale-skill\pipeline-osint-finanza.md sezione 3, tabella risoluzione luoghi [verificato con geo.risolvi_posto] | citato anche in area-cosa-vola per gli stessi rischi di geocoding |

Token: da misurare con verifica-skill.py.
