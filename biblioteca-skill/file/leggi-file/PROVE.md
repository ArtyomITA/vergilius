# PROVE: leggi-file

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| read_file: path (required), offset (1-based, opzionale), limit (opzionale) | odysseus/src/tool_schemas.py:101-112 | F01, F02, F20 |
| senza offset/limit legge fino a MAX_READ_CHARS+1 caratteri dall'inizio, poi tronca con nota "... [truncated at N chars]" | odysseus/src/agent_tools/filesystem_tools.py:277-289 (`ReadFileTool.execute`) | F01, F20 |
| con offset/limit legge riga per riga da `start=max(offset,1)`: un offset oltre la fine del file non produce righe (nessun errore che dica la lunghezza vera) | odysseus/src/agent_tools/filesystem_tools.py:260-276 | F02, F20 |
| non esiste una modalita' "ultime righe/tail": l'unico modo per arrivare alla fine di un file enorme e' un offset alto scelto a mano | odysseus/src/agent_tools/filesystem_tools.py:242-290 (nessun ramo che legge dalla coda) | F20 |
| percorso risolto da `_resolve_tool_path`: rifiuta nomi/cartelle sensibili (.env, .ssh, .gitconfig, id_rsa, authorized_keys, known_hosts...) e tutto cio' che sta fuori dalle radici consentite (workspace, uploads, mail-attachments, personal_docs, personal_uploads) | odysseus/src/tool_execution.py:91-132 (`_is_sensitive_path`), 180-220 (`_agent_readable_data_subdirs`), 371-420 (`_resolve_tool_path`) | (percorso-vietato/fuori-area, guardia comune anche a elenca-cartella/trova-file-per-nome/cerca-testo-in-file) |

Token: da misurare con verifica-pc.py.
