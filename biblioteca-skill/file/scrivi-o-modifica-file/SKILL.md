---
name: scrivi-o-modifica-file
description: "Creare un file, sostituirne il contenuto, o cambiare una parte precisa di un file."
version: 1.0.0
category: file
tags: [scrivi, crea, modifica, cambia, sostituisci, file, salva]
tools: [write_file, edit_file, read_file]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Create a file, overwrite it, or change one exact part: "crea note.txt con dentro...", "nel file config.txt cambia timeout da 30 a 60".

## Procedure
1. New file, or the whole content must be replaced: write_file {"path":"<path>","content":"<full text>"}.
2. A small change: edit_file {"path":"<path>","old_string":"<exact text>","new_string":"<replacement>"}.
3. old_string not unique: add "replace_all":true to the same call.
4. old_string not found: read_file {"path":"<path>"} first, copy the exact text.
5. Check: read the tool's diff, confirm it matches the intended change.

## Pitfalls
- write_file always overwrites the entire file: never for a small edit.
- old_string must match exactly and be unique, or set replace_all.
- refused on the same sensitive/out-of-workspace paths as read_file.
