---
name: storico-mappa
description: "Com'era la situazione della mappa nel passato: elenco, scatto o replay di uno snapshot."
version: 1.0.0
category: osint
tags: [storico, snapshot, prima, passato, com'era, replay, rivedi]
tools: [osint_storico]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Com'era la situazione 3 ore fa", "salva lo stato adesso", "fammi vedere gli snapshot". Financial history: use archivio-storico instead.

## Procedure
1. List snapshots: osint_storico {"azione":"elenca"}.
2. Replay one: osint_storico {"azione":"riproduci","id":"<id from elenca>"}.
3. Take one now, only on explicit request: osint_storico {"azione":"cattura"}.
4. Fallback: riproduci without a valid id -> call elenca first.
5. Check: say which snapshot the data comes from, or that it is the live state.

## Pitfalls
- cattura is a write needing the full access tier.
- riproduci needs a real id from elenca: an invented one errors.
- This is the OSINT map state, not financial history.
