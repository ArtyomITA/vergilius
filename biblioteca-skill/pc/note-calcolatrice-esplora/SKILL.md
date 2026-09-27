---
name: note-calcolatrice-esplora
description: "Aprire Calcolatrice, Blocco note o Esplora file per un compito semplice sul desktop."
version: 1.0.0
category: pc
tags: [calcolatrice, calcola, blocco, note, esplora, file, cartella, documenti]
tools: [App, Click, vista_schermo]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
A quick task in a native app: "apri la Calcolatrice", "apri Esplora file e vai in Documenti".

## Procedure
1. App {"mode":"switch","name":"<Calcolatrice|Blocco note|Esplora file>"}, or "launch" if closed.
2. vista_schermo {"focus":"the controls or navigation pane"} for fresh (x,y).
3. Click {"loc":[x,y]} on one control: a digit/operator, or a folder shortcut.
4. Check: vista_schermo again, read the result before answering.

## Pitfalls
- opening a subfolder or file needs a double click, which always asks approval first.
- button layout changes with window size: always read fresh coordinates, never reuse old ones.
