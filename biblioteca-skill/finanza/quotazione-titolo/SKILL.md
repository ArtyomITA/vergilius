---
name: quotazione-titolo
description: "Prezzo in tempo reale di un titolo azionario o cripto, o confronto fra piu' titoli."
version: 1.0.0
category: finanza
tags: [quotazione, quota, prezzo, azione, azioni, titolo, borsa, ticker, confronta, confronto, grafico, chart]
tools: [fin_mercati, calcola, fin_archivio]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Come sta Leonardo in borsa", "quanto vale AAPL", "confronta Nvidia e AMD" (one live price or several to compare).

## Procedure
1. fin_mercati {"titolo":"<name or ticker>","quante_notizie":3}; one call per stock.
2. Read titolo_richiesto: disponibile, prezzo, valuta, variazione_percento, variazione_in_valuta, avviso.
3. Difference or ratio: calcola {"espressioni":["<prezzo1> - <prezzo2>"]}.
4. Fallback: disponibile false -> say motivo, ask exact ticker, never estimate.
5. Fallback: past period -> fin_archivio {"query":"<ticker> picchi","giorni":14}.
6. Check: name symbol, price, currency, percent change; green up, red down.

## Pitfalls
- titolo is ONE company, never a sector or list.
- avviso present: say which symbol you quoted.
- A chart is a fenced chart block in your reply, never a tool call.
