# PROVE: storico-mappa

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_storico: azione (elenca/cattura/riproduci), id | odysseus/src/shadowbroker/schemi.py:322-338 | descrizione: "TIME MACHINE", per lo storico finanziario usare fin_archivio |
| elenca default; riproduci senza id errore esplicito; cattura e' scrittura (tier full) | odysseus/src/agent_tools/shadowbroker_tools.py:862-888 (`StoricoTool.run`) | riga 879-880 errore id mancante; riga 887-888 nota tier full su cattura |
| cattura usa profile "openclaw" (take_snapshot) | odysseus/src/agent_tools/shadowbroker_tools.py:874-876 | |
| separazione esplicita da fin_archivio (storico finanziario) | odysseus/src/shadowbroker/schemi.py:327-328 (descrizione) | citato nel When to Use come rimando |

Token: da misurare con verifica-skill.py.
