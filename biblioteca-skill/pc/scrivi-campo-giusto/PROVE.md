# PROVE: scrivi-campo-giusto

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| Type: text (required), loc, label, clear (default false), caret_position, press_enter (default false) | Windows-MCP/src/windows_mcp/tools/input.py:260-297 | P07 |
| Type e' rifiutato se la finestra in primo piano non e' quella dichiarata da un App(launch\|switch) precedente nella stessa sessione, o se la finestra in primo piano non si legge | odysseus/src/tool_execution.py:929-964 (`_guardia_finestra_pc`) | P07, P09 |
| processi mai bersaglio di input sintetico: terminali (windowsterminal, conhost, cmd, powershell, pwsh), editor (code, devenv, idea64, pycharm64), l'agente stesso (claude, node), i browser (chrome, msedge, firefox, brave, opera) | odysseus/src/tool_execution.py:737-742 (`_FINESTRE_VIETATE`) | P09 |
| Type con press_enter=True, o testo con un a-capo, e' irreversibile ("Type with press_enter" / "line break"); un tab nel testo sposta il fuoco e i tasti dopo possono premere un pulsante | odysseus/src/tool_execution.py:1335-1345 (`azione_desktop_irreversibile`, ramo Type) | nessuna (fatto di codice) |
| Type dentro un dialogo (o se non si sa) su un elemento che non e' un campo di testo ("edit"/"modifica" nello Snapshot) e' irreversibile: le lettere fanno da mnemonico, lo spazio preme il pulsante col fuoco | odysseus/src/tool_execution.py:1183-1190 (`_campo_di_testo`), 1363-1373 | nessuna (fatto di codice) |

Token: da misurare con verifica-pc.py.
