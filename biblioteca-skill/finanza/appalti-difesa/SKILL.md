---
name: appalti-difesa
description: "Contratti federali USA ai grandi appaltatori della difesa: chi vince, quanto, dove."
version: 1.0.0
category: finanza
tags: [appalti, appalto, contratti, contratto, commesse, commessa, difesa, contractor]
tools: [fin_appalti, osint_mappa]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Che commesse militari ci sono", "appalti della difesa" (RTX, LMT, NOC, GD, BA, PLTR).

## Procedure
1. fin_appalti {"titolo":"<RTX/LMT/NOC/GD/BA/PLTR, or omit for all six>","mesi":12,"quanti":12}.
2. Read contratti: assegnataria, importo_milioni, agenzia, oggetto, stato_usa or luogo, id.
3. Map asked: osint_mappa {"azione":"evidenzia","ids":["<id from step 1>"]}.
4. Fallback: titolo outside the six is dropped, all six return; few results -> raise mesi (quarterly data).
5. Check: name contractor, amount in millions, agency, place; "non dichiarato" if missing.

## Pitfalls
- importo_milioni is the contract max value, not money spent.
- titolo outside the six returns all six, no error.
- ids only for osint_mappa evidenzia, never a ticker.
