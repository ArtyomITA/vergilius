# PROVE: guarda-trova-elemento

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| vista_schermo: parametro `focus` (stringa, topic non domanda si/no), ritorna descrizione neutra + albero a11y `albero_ui` | odysseus/src/vista/schemi.py:11-28 | P04, P05 |
| vista_trova: parametro `elemento` (required, breve descrizione visiva in inglese), un elemento per chiamata | odysseus/src/vista/schemi.py:30-46 | P05 |
| il VLM risponde solo alla prima parte di un prompt con piu' domande (motiva "un elemento per chiamata") | odysseus/src/vista/schemi.py:4-7 (commento di modulo) | nessuna (fatto di codice) |
| formato reale delle righe elemento dello Snapshot/albero_ui: `(x,y) tipo "etichetta"`, tipo LOCALIZZATO (pulsante, modifica, voce di menu...) | odysseus/src/agent_tools/vista_tools.py:99-118 (commento "Formato reale dello Snapshot") | P04, P05 |
| Snapshot: use_ui_tree (default true) da' elementi interattivi con coordinate; use_vision aggiunge lo screenshot | Windows-MCP/src/windows_mcp/tools/snapshot.py:27-72 (descrizione e parametri di `_state_tool`) | P04 |
| la mappa etichetta-coordinate dell'ultimo Snapshot scade dopo ogni azione sul desktop e dopo un tempo massimo (default 30s, tetto 120s): un (x,y) vecchio non e' piu' garantito valido | odysseus/src/tool_execution.py:1112-1119 (`_MAPPA_PC`, `_MAPPA_PC_DURATA_S`), 870-878 (`_eta_max_mappa_pc`) | nessuna (fatto di codice, motiva il pitfall sulla staleness) |

Token: da misurare con verifica-pc.py.
