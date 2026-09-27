# PROVE: recon-tecnico

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_recon: tipo (required, enum ip/dns/whois/certs/bgp/sanctions/cve/mac/github/leaks/threats/espandi), valore (required), entita (per espandi) | odysseus/src/shadowbroker/schemi.py:172-192 | descrizione: "External lookup, slower than platform tools" |
| valore mancante o tipo sconosciuto: errore esplicito con l'elenco ammesso | odysseus/src/agent_tools/shadowbroker_tools.py:340-348 (`ReconTool.run`) | |
| espandi: entita default company se il valore non e' un IPv4 a 4 gruppi, altrimenti ip | odysseus/src/agent_tools/shadowbroker_tools.py:358-370 (`_espandi`) | |
| alias italiani accettati (sanzioni->sanctions, dominio->dns, ecc.) ma lo schema espone solo i nomi inglesi | odysseus/src/agent_tools/shadowbroker_tools.py:328-338 | la skill usa solo i nomi inglesi dello schema |

Token: da misurare con verifica-skill.py.
