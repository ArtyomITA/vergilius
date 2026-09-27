---
name: guarda-trova-elemento
description: "Vedere cosa c'e' sullo schermo o trovare le coordinate di un elemento prima di cliccarci."
version: 1.0.0
category: pc
tags: [schermo, vedi, guarda, trova, dove, pulsante, icona, coordinate, cosa]
tools: [vista_schermo, vista_trova, Snapshot]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Read what is on screen, or locate an element's coordinates before Click/Type: "cosa vedi aperto adesso", "dove si trova il pulsante Salva".

## Procedure
1. vista_schermo {"focus":"<topic, not a yes/no question>"}: description plus `albero_ui` lines "(x,y) type \"label\"".
2. Target is one of those lines: read its (x,y) from the line.
3. Icon or custom widget not in `albero_ui`: vista_trova {"elemento":"<short visual description in English>"}.
4. Still missing: Snapshot {"use_ui_tree":true} for the fuller tree.
5. Check: state the exact (x,y) and label used before clicking.

## Pitfalls
- vista_trova answers one element per call: split a compound request.
- coordinates go stale after any desktop action: re-check before reusing an old (x,y).
- never click from the eyes' prose alone: only from numeric (x,y).
