# PROVE: copia-incolla

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| Clipboard: mode get\|set (required), text (required per set) | Windows-MCP/src/windows_mcp/tools/clipboard.py:10-25 | P18, P19 |
| get legge solo CF_UNICODETEXT: se assente ritorna "Clipboard is empty or contains non-text data." | Windows-MCP/src/windows_mcp/tools/clipboard.py:29-36 | P19 |
| set fa EmptyClipboard()+SetClipboardText: sovrascrive subito il contenuto precedente | Windows-MCP/src/windows_mcp/tools/clipboard.py:39-46 | P18 |
| ctrl+c e ctrl+v non sono nelle combinazioni sempre irreversibili ne' nel ramo spazio/lettera-singola (richiede modificatori solo alt), quindi il classificatore non li segna irreversibili | odysseus/src/tool_execution.py:1102-1108 (`_COMBINAZIONI_IRREVERSIBILI`), 1259-1266 (`_shortcut_irreversibile`, mods<={"alt"}) | nessuna (fatto di codice, motiva perche' i passi 3-4 non chiedono scheda) |
| Shortcut e' fra i tool di input soggetti alla guardia finestra (rifiutato se il bersaglio dichiarato non e' in primo piano) | odysseus/src/tool_execution.py:754-758 (`_WINDOWS_MCP_INPUT_TOOLS`) | nessuna (fatto di codice, motiva il pitfall sul focus) |

Token: da misurare con verifica-pc.py.
