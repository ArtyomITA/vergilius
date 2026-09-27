---
name: trova-file-per-nome
description: "Trovare file per nome o estensione dentro una cartella, senza aprirli."
version: 1.0.0
category: file
tags: [trova, cerca, file, nome, estensione, dove]
tools: [glob]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Find files by name pattern or extension: "trova tutti i file che finiscono in .py dentro la cartella src".

## Procedure
1. glob {"pattern":"<glob, e.g. \"**/*.py\">","path":"<folder>"}.
2. Nothing found: try a looser pattern (a shorter stem, or "*<part of the name>*").
3. Check: list the exact paths returned; the newest-modified files come first, not an alphabetical order.

## Pitfalls
- results are capped (200 matches) with a note when more exist: never claim the pattern only matched what was shown.
- sensitive folders/files (.ssh, .env, node_modules, .git...) are pruned from the search and never appear, even on a matching pattern.
