# PROVE: militare-zona

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_militare: luogo, raggio_km, quanti | odysseus/src/shadowbroker/schemi.py:77-93 | descrizione: aerei/navi militari o governativi raggruppati per ruolo |
| raggio clamp 10-10000 (default vero 1000 nel briefing, non nell'handler); quanti default 15 (3-40) | odysseus/src/agent_tools/shadowbroker_tools.py:243-250 (`MilitareTool.run`, clamp); odysseus/src/shadowbroker/briefing.py:799 (`_raggio(raggio_km, posto, 1000)`, default vero) | la skill sceglie 800 esplicito, sotto il tetto di 8000 caratteri; citazione corretta dopo revisione FINANZA #24 |
| osint_allerte: luogo, raggio_km, quante | odysseus/src/shadowbroker/schemi.py:97-112 | quante, non quanti |
| raggio clamp 10-10000 (default vero 1000 nel briefing); quante default 15 (3-30) | odysseus/src/agent_tools/shadowbroker_tools.py:253-260 (`AllerteTool.run`, clamp); odysseus/src/shadowbroker/briefing.py:926 (`_raggio(raggio_km, posto, 1000)`, default vero) | stessa correzione |
| osint_rischio: azione (classifica/dossier/ricalcola), regione, quante; dossier richiede regione altrimenti errore | odysseus/src/shadowbroker/schemi.py:272-292; odysseus/src/agent_tools/shadowbroker_tools.py:775-802 (`RischioTool.run`, riga 789-790 errore se manca regione) | |
| errore esplicito se GT_ANALYTICS_ENABLED e' spento, messaggio incluso nella risposta | odysseus/src/agent_tools/shadowbroker_tools.py:799-802 | citato nel messaggio di errore del codice stesso |
| navi_militari include navi mercantili nel raggio | D:\vergilius-lab\ricerche\decisori\materiale-skill\pipeline-osint-finanza.md sezione 3, riga osint_militare "trappole" | stesso avviso di area-cosa-vola |

Token: da misurare con verifica-skill.py.
