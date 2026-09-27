---
name: scrivi-campo-giusto
description: "Scrivere del testo in un campo di una finestra precisa, senza sbagliare finestra."
version: 1.0.0
category: pc
tags: [scrivi, scrivere, digita, testo, campo, casella, finestra]
tools: [App, Type]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Type text into one field of a specific app window: "apri il Blocco note e scrivi...", "scrivi nella casella di ricerca".

## Procedure
1. App {"mode":"switch","name":"<Italian app name>"} (or "launch") to declare the target window.
2. vista_schermo {"focus":"the field to type into"} for its (x,y), check it is editable.
3. Type {"text":"<text>","loc":[x,y],"clear":false}.
4. Replacing existing text: Type {"text":"<text>","loc":[x,y],"clear":true}.
5. Check: vista_schermo again, confirm the field shows the typed text.

## Pitfalls
- refused if the foreground window is a terminal, editor, browser, or does not match the App target.
- never use press_enter=true or a newline/tab in text: each counts as irreversible.
- typing on coordinates not shown as editable, especially inside a dialog, can press a button instead.
