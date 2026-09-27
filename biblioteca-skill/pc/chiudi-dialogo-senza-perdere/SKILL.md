---
name: chiudi-dialogo-senza-perdere
description: "Chiudere un dialogo scegliendo il pulsante giusto senza perdere dati."
version: 1.0.0
category: pc
tags: [dialogo, conferma, salva, annulla, chiudi, finestra, popup, avviso]
tools: [vista_schermo, Click, Shortcut]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
A dialog is open and must be closed correctly: "e' apparso un dialogo, voglio annullare senza salvare", "premi OK per confermare".

## Procedure
1. vista_schermo {"focus":"the dialog title and every button label"}.
2. Nothing must change or be discarded: Shortcut {"shortcut":"escape"}, or Click {"loc":[x,y]} on "Annulla"/"Cancel"/"No".
3. Any other button (Salva, Non salvare, OK, Si/Yes, Continua, Applica) changes or discards something: say it needs the owner's approval, even if already asked, and wait.
4. Approved: Click {"loc":[x,y]} on that button.
5. Check: vista_schermo again, confirm the dialog is gone.

## Pitfalls
- "Non salvare"/"Don't Save" looks safe but discards changes: always needs approval.
- Escape and Annulla/Cancel/No never need approval: prefer them when in doubt.
- read every button label, not just the dialog's title.
