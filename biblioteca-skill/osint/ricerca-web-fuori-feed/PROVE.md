# PROVE: ricerca-web-fuori-feed

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_web: query (required), quanti (default 6, max 10), recenti (day/week/month) | odysseus/src/shadowbroker/schemi.py:247-267 | |
| osint_web usa il motore searxng, quanti clamp 1-10, recenti forzato a None se fuori enum | odysseus/src/agent_tools/shadowbroker_tools.py:734-764 (`WebTool.run`) | zero risultati -> nota che suggerisce parole chiave inglesi piu' semplici (riga 754-758), da qui il fallback |
| osint_notizie legge il testo vero con url o id | odysseus/src/agent_tools/shadowbroker_tools.py:191-240 (`NotizieTool`, `_leggi`) | stessa citazione di notizie-soggetto |
| web_search: query (required), time_filter (day/week/month/year) | odysseus/src/tool_schemas.py:71-81 | strumento generico fuori profilo OSINT/Financial |
| web_fetch: url (required), full | odysseus/src/tool_schemas.py:86-96 | full=true solo dopo un avviso di contenuto parziale |
| "osint_testo" non e' piu' un tool separato (fuso in osint_notizie il 20 ago) ma resta nominato nel testo delle regole finanziarie che il modello legge | odysseus/src/shadowbroker/schemi.py:618-620 (riga viva: "osint_notizie/osint_testo only to cross-check...") | corretto rispetto alla bozza pipeline-osint-finanza.md, che citava shadowbroker_tools.py:701/briefing.py:402,455: quelle righe sono cambiate; la citazione ferma che regge oggi e' questa in schemi.py |
| gli esiti di osint_notizie NON contengono piu' "osint_testo" (verificato con test dedicato) | odysseus/tests/test_sb_percorsi_luoghi.py:493-502 (`test_niente_piu_osint_testo_negli_esiti`) | quindi il rischio e' solo nel testo delle regole che il modello legge, non negli esiti dei tool |

Token: da misurare con verifica-skill.py.

## Versione 1.0.1 (27 set 2026, stanza 6, cancello 2)
- Tolti web_search e web_fetch da `tools:` e il passo "senza profilo". Con loro la skill non era MAI candidata nel dominio osint:
  `candidata()` (odysseus/src/skill_selettore.py) richiede che tutti i `tools:` siano nel paniere forzato del modo Intelligence,
  che non li contiene (provato da DATI con `scripts/banco-selettore-skill.py --famiglia osint --dry-run`: "skill mai candidata").
  Fuori da Intelligence/Financial il selettore non usa il dominio osint, quindi quel passo non serviva mai.
