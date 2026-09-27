---
name: archivio-storico
description: "Eventi finanziari passati gia' archiviati: notizie, picchi, appalti, insider."
version: 1.0.0
category: finanza
tags: [archivio, storico, passato, settimana, mese, scorso, successo]
tools: [fin_archivio]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Cosa era successo a RTX il mese scorso", "notizie finanziarie di due settimane fa". For "now" use the live tools.

## Procedure
1. fin_archivio {"query":"<ticker or topic>","giorni":30,"quanti":6}; query is required.
2. Read risultati: testo, tipo, ticker, quando, fonte, distanza (lower = closer match).
3. Fallback: vuoto present -> say the archive has nothing for this query yet, not that nothing happened.
4. Fallback: no date fits -> drop giorni once, then narrow the query instead.
5. Check: answer only from risultati text, with quando and fonte per item.

## Pitfalls
- The archive holds only what already passed through a live briefing: gaps are normal.
- Price history is only picco EVENTS (a dated jump), never a live-looking quote.
- Never confuse a low distanza with certainty: it is a similarity score, not a date match.
