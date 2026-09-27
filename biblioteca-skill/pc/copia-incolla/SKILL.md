---
name: copia-incolla
description: "Copiare un testo sugli appunti, leggerlo o incollarlo in un campo gia' aperto."
version: 1.0.0
category: pc
tags: [copia, incolla, appunti, clipboard, taglia]
tools: [Clipboard, Shortcut]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Put text on the clipboard, read it back, or paste into a focused field: "copia questo testo negli appunti", "cosa c'e' negli appunti adesso".

## Procedure
1. Clipboard {"mode":"set","text":"<text>"} to copy text directly.
2. Clipboard {"mode":"get"} to read the clipboard.
3. Field already focused in its target window: Shortcut {"shortcut":"ctrl+v"}.
4. Copying a selection: Shortcut {"shortcut":"ctrl+c"}, then Clipboard {"mode":"get"} to confirm.
5. Check: Clipboard {"mode":"get"} again, confirm the content matches.

## Pitfalls
- the clipboard holds only text: an image or file reads back as empty.
- ctrl+v/ctrl+c only work if the field is already focused in the declared target app.
- Clipboard {"mode":"set"} overwrites the old content at once: read it first if it still matters.
