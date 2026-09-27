---
name: cerca-entita
description: "Trovare un aereo, nave, persona o azienda e la sua scheda."
version: 1.0.0
category: osint
tags: [dov, trova, trovami, scheda, matricola, callsign, nave, aereo, yacht]
tools: [osint_cerca, osint_dettaglio]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Dov'e' Air Force One", "trova lo yacht di X", "chi possiede quella nave".

## Procedure
1. osint_cerca {"query":"<name, callsign, registration, MMSI or owner>"}.
2. Context/links needed: osint_cerca {"query":"<same>","contesto":true,"relazioni":true}.
3. Already have an id: osint_dettaglio {"id":"<that id>"} instead.
4. Fallback: id not found -> redo the search with osint_cerca.
5. Check: answer with identity and last known position; mark estimates as such.

## Pitfalls
- osint_cerca and osint_dettaglio need one identifier, never a whole area.
- contesto, relazioni are flags in the same call, not separate calls.
- An id is valid only while the element stays in memory: an old one may 404.
