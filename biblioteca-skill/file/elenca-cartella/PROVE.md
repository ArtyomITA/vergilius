# PROVE: elenca-cartella

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| ls: path opzionale, radice del progetto se assente | odysseus/src/tool_schemas.py:150-159 | F04 |
| get_workspace: nessun argomento, ritorna la cartella attiva del progetto | odysseus/src/tool_schemas.py:164-168 | F04 (quando manca il path) |
| l'elenco ordina prima le cartelle poi i file (`rows.sort(key=lambda r: (not r[0], r[1].lower()))`), ogni file con la sua dimensione in byte | odysseus/src/agent_tools/filesystem_tools.py:557-560 (`LsTool._ls`) | F04 |
| gli elementi il cui nome comincia con "." sono saltati e mai messi in lista | odysseus/src/agent_tools/filesystem_tools.py:545-546 | F04 |
| l'elenco e' tagliato a _CODENAV_MAX_HITS (200) con la riga "... [N more]" quando ce ne sono di piu' | odysseus/src/agent_tools/filesystem_tools.py:559-562 | F04 |
| path che punta a un file, non a una cartella: errore "ls: <path>: not a directory" | odysseus/src/agent_tools/filesystem_tools.py:539-540 | F04 |

Token: da misurare con verifica-pc.py.
