# PROVE: radio-sigint

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_radio: azione (required, enum scanner/kiwisdr/acars), luogo, lat, lng, aereo | odysseus/src/shadowbroker/schemi.py:389-411 | |
| scanner default; senza punto risolto errore esplicito "serve un luogo" | odysseus/src/agent_tools/shadowbroker_tools.py:977-1010 (`RadioTool.run`, riga 1000-1002) | |
| acars richiede "aereo"; l'handler indovina hex(icao24)/registration/callsign dal formato della stringa | odysseus/src/agent_tools/shadowbroker_tools.py:985-998 | non serve dire al modello il formato: passa il valore cosi' com'e' |
| scanner: quanti default 5 (1-20, fuori schema, non citato nella skill) | odysseus/src/agent_tools/shadowbroker_tools.py:1008-1009 | |

Token: da misurare con verifica-skill.py.
