---
name: sorveglianza-attiva
description: "Tenere d'occhio un aereo, una nave o un'area, e i suoi avvisi."
version: 1.0.0
category: osint
tags: [sorveglia, sorveglianza, avvisami, tieni, occhio, allerta, watch]
tools: [osint_sorveglianza]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Avvisami se decolla un aereo militare da qui", "tieni d'occhio questa nave", "quali sorveglianze ho attive".

## Procedure
1. List: osint_sorveglianza {"azione":"elenca"}; pushed alerts: osint_sorveglianza {"azione":"avvisi"}.
2. Watch a target or an area: osint_sorveglianza {"azione":"aggiungi","bersaglio":"<callsign, ship or keyword>"} or {"azione":"aggiungi","luogo":"<name or 'lat,lng'>","raggio_km":100}.
3. Remove one: osint_sorveglianza {"azione":"rimuovi","id":"<id from elenca>"}.
4. Check: confirm what is now watched; say writes need the full access tier.

## Pitfalls
- aggiungi/rimuovi/pulisci are writes: only on explicit request.
- aggiungi needs bersaglio OR luogo, never both empty.
- A standing watch, not a one-shot search.
