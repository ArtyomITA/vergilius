# PROVE: aspetta-waitfor

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| WaitFor: condition (required, text_exists\|active_window\|element_exists\|element_enabled\|focused_element), text, window_name, timeout, interval, use_dom | Windows-MCP/src/windows_mcp/tools/input.py:14-20 (Literal), 438-463 (schema) | P16 |
| timeout deve essere >0 e <=120s, interval >0 e <=5s, altrimenti errore esplicito | Windows-MCP/src/windows_mcp/tools/input.py:200-203 (`_validate_wait_for_args`) | P16 |
| un timeout di WaitFor (eccezione TimeoutError nello strumento) viene tradotto dal ponte MCP in un esito normale exit_code=0 con testo "WaitFor: condition NOT met before the timeout", non un errore da nascondere | odysseus/src/mcp_manager.py:567-579 | P16 |
| App(mode=launch\|switch) prima di WaitFor per avere una finestra target dichiarata | odysseus/src/tool_execution.py:967-974 (`_ricorda_bersaglio_pc`) | P16 |

Token: da misurare con verifica-pc.py.
