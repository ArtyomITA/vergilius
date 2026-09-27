# PROVE: apri-passa-app

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| App: mode (launch\|launch_executable\|resize\|switch), name, window_loc, window_size, executable, args, cwd | Windows-MCP/src/windows_mcp/tools/app.py:70-113 (schema/register) | P01, P02 |
| mode="switch" porta in primo piano una finestra gia' aperta trovata per nome; mode="launch" apre l'app e attende la finestra (UIA Exists, 10s) prima di rispondere | Windows-MCP/src/windows_mcp/desktop/service.py:475-504 (`app`, ramo launch), 412-439 (`_find_window_by_name` usata anche da switch) | P01, P02 |
| il nome e' cercato per fuzzy match fra le finestre aperte con score_cutoff=70; sotto soglia: "Application X not found." | Windows-MCP/src/windows_mcp/desktop/service.py:435 (`process.extractOne(name, ..., score_cutoff=70)`) | P02 |
| alias italiani noti del menu Start -> processo: blocco note/calcolatrice/esplora file/paint/impostazioni/wordpad | odysseus/src/tool_execution.py:745-752 (`_ALIAS_FINESTRE`) | P01, P13, P14 |
| mode="launch_executable" lancia un eseguibile con argv/cwd separati: il classificatore R0 lo conta sempre irreversibile ("runs an executable"), diverso da launch/switch/resize | odysseus/src/tool_execution.py:1312-1316 (`azione_desktop_irreversibile`, ramo App) | nessuna (fatto di codice) |
| un App(mode=launch\|switch) riuscito registra il "bersaglio" della chat: le azioni Click/Type successive vengono rifiutate se la finestra in primo piano non combacia | odysseus/src/tool_execution.py:929-964 (`_guardia_finestra_pc`), 967-974 (`_ricorda_bersaglio_pc`) | P07 (usata dalla skill scrivi-campo-giusto, che segue questa) |

Token: da misurare con verifica-pc.py.
