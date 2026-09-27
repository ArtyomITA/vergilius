# PROVE: scrivi-o-modifica-file

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| write_file: path (required), content (required); crea o SOVRASCRIVE il file | odysseus/src/tool_schemas.py:172-183 (schema), descrizione "Write/save a file to disk" | F10, F13 |
| edit_file: path, old_string, new_string (required), replace_all (opzionale); sostituzione per stringa esatta | odysseus/src/tool_schemas.py:187-199 | F11 |
| old_string non trovato: errore "old_string not found in <path>. Read the file and match it exactly." | odysseus/src/agent_tools/filesystem_tools.py:230 | F11 |
| old_string non unico: errore "old_string is not unique in <path> (<n> matches). Add surrounding context or set replace_all=true." | odysseus/src/agent_tools/filesystem_tools.py:231-233 | F11 |
| edit_file ritorna anche un diff unificato del cambiamento fatto | odysseus/src/agent_tools/filesystem_tools.py:236-239 (`_unified_diff`) | F11 |
| write_file (path assoluto o nel workspace) passa dallo stesso `_resolve_tool_path` di read_file: stessi percorsi negati | odysseus/src/agent_tools/filesystem_tools.py:292-298 (import `_resolve_tool_path`) | F10, F13 (stessa guardia di leggi-file) |

Token: da misurare con verifica-pc.py.
