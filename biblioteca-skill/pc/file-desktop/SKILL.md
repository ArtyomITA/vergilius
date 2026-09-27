---
name: file-desktop
description: "Vedere o leggere i file del Desktop e delle cartelle del proprietario dal lato del controllo PC."
version: 1.0.0
category: pc
tags: [desktop, file, cartella, elenca, lista, cerca]
tools: [FileSystem]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
List, inspect or read files from the user's Desktop or another real folder through the PC control tool: "elenca i file sul Desktop", "cosa c'e' in questa cartella".

## Procedure
1. FileSystem {"mode":"list","path":"<relative to Desktop, or absolute>"} to see what is there.
2. One entry needs details (size, dates, type): FileSystem {"mode":"info","path":"<path>"}.
3. Finding files by name: FileSystem {"mode":"search","path":"<folder>","pattern":"<glob>"}.
4. Reading a text file's content: FileSystem {"mode":"read","path":"<path>"}.
5. Check: state the exact path(s) found; a relative path resolved under the Desktop folder unless it was already absolute.

## Pitfalls
- write, copy, move and delete modes are irreversible for the approval system: only read/list/search/info run without a card.
- a bare name like "note.txt" resolves under the Desktop, not the current folder of a previous step: pass an absolute path for anything elsewhere.
