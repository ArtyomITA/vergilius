# PROVE: rischio-paese

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_rischio: azione (classifica/dossier/ricalcola), regione, quante | odysseus/src/shadowbroker/schemi.py:272-292 | descrizione: modello previsionale, diverso da osint_allerte (incidenti vivi) |
| classifica default, quante default 10 (3-30) | odysseus/src/agent_tools/shadowbroker_tools.py:775-798 (`RischioTool.run`, riga 796) | |
| dossier senza regione: errore esplicito "serve una regione" | odysseus/src/agent_tools/shadowbroker_tools.py:787-790 | |
| ricalcola chiama gt_analyze, un ricalcolo del modello intero | odysseus/src/agent_tools/shadowbroker_tools.py:793-795 | non da chiamare senza richiesta esplicita: costoso (timeout 60s) |
| errore se GT_ANALYTICS_ENABLED e' spento, messaggio incluso in risposta | odysseus/src/agent_tools/shadowbroker_tools.py:799-802 | stessa citazione di militare-zona |
| osint_allerte come alternativa per incidenti vivi | odysseus/src/shadowbroker/schemi.py:97-112, descrizione "Active alerts ranked by severity" | usata nel fallback |

Token: da misurare con verifica-skill.py.
