# PROVE: notizie-soggetto

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_notizie: soggetto, luogo, tema, giorni, raggio_km, quante, url, id, leggi_testo | odysseus/src/shadowbroker/schemi.py:47-73 | soggetto descritto come azienda/persona/organizzazione, MAI un luogo (riga 61) |
| con url o id legge il testo vero dell'articolo invece del solo elenco (osint_testo fuso qui il 20 ago) | odysseus/src/agent_tools/shadowbroker_tools.py:191-240 (`NotizieTool.run`, `_leggi`) | id non trovato -> errore esplicito "rifai la domanda" (riga 226-227) |
| id preso da un evento gia' visto, formato tipo gdelt:xxxxxx | odysseus/src/agent_tools/shadowbroker_tools.py:223-228 (`get_store().dettaglio`) | coerente con osint_dettaglio |
| giorni default 2, quante default 8, leggi_testo VERO se omesso (rallenta) | odysseus/src/agent_tools/shadowbroker_tools.py:214-217 | motivo per cui la skill fissa leggi_testo:false di default |
| soggetto = corrispondenza a sottostringa su parole di 3+ lettere ("Mar Nero" ha agganciato "Denmark") | D:\vergilius-lab\qa\mar-nero\skill.md sezione 4, skill 3 pitfall | stesso difetto osservato nella conversazione Mar Nero |
| fin_mercati con titolo restituisce notizie_di_questo_titolo dentro la stessa chiamata | odysseus/src/shadowbroker/schemi.py:481-499; concordato in chat con FINANZA (#6) | evita la doppia chiamata notizie-soggetto + fin_mercati per lo stesso titolo |
| osint_web: query (required), quanti, recenti (day/week/month) | odysseus/src/shadowbroker/schemi.py:247-267 | usato come ripiego finale |

Token: da misurare con verifica-skill.py.
