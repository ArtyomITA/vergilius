---
name: elenca-cartella
description: "Vedere cosa c'e' dentro una cartella, con nomi, tipo e dimensione dei file."
version: 1.0.0
category: file
tags: [elenca, lista, cartella, dentro, contenuto, file]
tools: [ls, get_workspace]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
List what is inside a folder: "elenca i file che ci sono dentro la cartella progetti".

## Procedure
1. No path given and "the project"/"this folder" is meant: get_workspace {} first.
2. ls {"path":"<folder>"}: folders listed first, then files with their size in bytes.
3. Result says "not a directory": the path names a file, not a folder; use read_file on it instead.
4. Check: report exactly the names shown, and flag it if the output says more entries were capped.

## Pitfalls
- ls hides dotfiles (names starting with ".") entirely: it never lists them, not even as "hidden".
- ls caps the listing (200 entries) and says how many more exist: never claim the folder holds only what was shown when it says "more".
