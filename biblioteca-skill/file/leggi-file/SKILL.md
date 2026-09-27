---
name: leggi-file
description: "Leggere il contenuto di un file di testo, tutto o solo un intervallo di righe."
version: 1.0.0
category: file
tags: [leggi, leggere, apri, contenuto, file, righe]
tools: [read_file]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Read a text file, whole or by line range: "leggi il file appunti.txt e dimmi cosa contiene", "leggimi solo le righe da 100 a 150".

## Procedure
1. read_file {"path":"<file path>"} for a normal-sized file.
2. A precise range: read_file {"path":"<path>","offset":<1-based line>,"limit":<lines>}.
3. Only the END of a huge file matters, no tail mode exists: guess a high offset, lower it if empty.
4. Path refused (outside workspace, or a sensitive name): say so, do not retry with a different spelling.
5. Check: state which lines were shown, flag a truncation note.

## Pitfalls
- no offset/limit on a huge file returns only the first chunk, with an easy-to-miss truncation note.
- offset is 1-based; out-of-range returns empty, not the real length.
- .env, .ssh, id_rsa, authorized_keys and paths outside the allowed folders are always refused.
