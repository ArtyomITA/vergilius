# PROVE: cerca-entita

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_cerca: query (required), contesto (boolean), relazioni (boolean) | odysseus/src/shadowbroker/schemi.py:151-167 | descrizione: profilo di UNA entita' precisa, cerca per nome/callsign/matricola/proprietario |
| contesto aggiunge "cosa c'e' vicino con un livello di confidenza"; relazioni aggiunge sanzioni OFAC e collegamenti | odysseus/src/shadowbroker/schemi.py:154-156 (descrizione schema) | entrambi passati come flag nella stessa chiamata (`entita.scheda(con_contesto=..., con_relazioni=...)`) |
| raggio_km per il contesto: default 300, clamp 10-2000 (fuori schema, non citarlo nella skill) | odysseus/src/agent_tools/shadowbroker_tools.py:298-318 (`CercaTool.run`, riga 317) | lo schema non espone raggio_km per osint_cerca: usarlo darebbe errore "parametro non esiste" |
| query mancante: errore esplicito | odysseus/src/agent_tools/shadowbroker_tools.py:311-312 | |
| osint_dettaglio: id (required) | odysseus/src/shadowbroker/schemi.py:135-146 | "la scheda intera di un elemento gia' visto in un briefing" |
| id non trovato: errore che dice di rifare la domanda, perche' l'id vale finche' l'elemento resta in memoria | odysseus/src/agent_tools/shadowbroker_tools.py:284-293 (`DettaglioTool.run`) | stesso comportamento di osint_notizie con id (notizie-soggetto) |

Token: da misurare con verifica-skill.py.
