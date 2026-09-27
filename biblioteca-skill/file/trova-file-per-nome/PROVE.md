# PROVE: trova-file-per-nome

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| glob: pattern (required), path opzionale (radice del progetto se assente) | odysseus/src/tool_schemas.py:135-146 | F06 |
| i risultati sono ordinati per mtime decrescente (piu' recenti prima), non alfabetico | odysseus/src/agent_tools/filesystem_tools.py:666-667 (`matched.sort(key=lambda t: t[0], reverse=True)`) | F06 |
| tetto di 200 risultati (`_CODENAV_MAX_HITS`) con nota "... [capped at 200 files]" quando ce ne sono di piu' | odysseus/src/agent_tools/filesystem_tools.py:667, 674-676 | F06 |
| cartelle/nomi sensibili (.ssh, .env, node_modules, .git, __pycache__...) sono esclusi dalla camminata (`_CODENAV_SKIP_DIRS`, `_SENSITIVE_BASENAMES`) e i file deny-listed sono scartati anche se combaciano col pattern | odysseus/src/agent_tools/filesystem_tools.py:643-656 | F06 |

Token: da misurare con verifica-pc.py.
