# PROVE: file-desktop

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| FileSystem: mode (read\|write\|copy\|move\|delete\|list\|search\|info, required), path (required), destination, content, pattern, recursive, append, overwrite, offset, limit, encoding, show_hidden | Windows-MCP/src/windows_mcp/tools/filesystem.py:13-39 | P20 |
| i percorsi relativi si risolvono dalla cartella Desktop dell'utente; un percorso assoluto raggiunge qualunque altro posto | Windows-MCP/src/windows_mcp/tools/filesystem.py:15 (descrizione), 41-46 (`default_dir = user_desktop_dir()`) | P20 |
| per il classificatore R0 i modi sicuri di FileSystem sono solo read/list/search/info; write/copy/move/delete sono irreversibili | odysseus/src/tool_execution.py:1302-1311 (`azione_desktop_irreversibile`, ramo FileSystem) | nessuna (fatto di codice) |

Token: da misurare con verifica-pc.py.
