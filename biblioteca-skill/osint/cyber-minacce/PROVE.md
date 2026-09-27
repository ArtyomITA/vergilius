# PROVE: cyber-minacce

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_cyber: azione (malware/vulnerabilita/rischio_paese/tutto), nessun campo required | odysseus/src/shadowbroker/schemi.py:367-384 | |
| default azione "tutto" se omessa | odysseus/src/agent_tools/shadowbroker_tools.py:955 (`CyberTool.run`) | |
| malware=botnet C2 (abuse.ch /api/malware), vulnerabilita=CISA KEV (/api/cyber-threats), rischio_paese=indice (/api/country-risk) | odysseus/src/agent_tools/shadowbroker_tools.py:957-962 | |
| "tutto" chiama le tre fonti e mette l'errore di una singola fonte dentro il suo campo, senza far fallire le altre due | odysseus/src/agent_tools/shadowbroker_tools.py:963-972 | conferma i pitfall 2 e 3 |

Token: da misurare con verifica-skill.py.
