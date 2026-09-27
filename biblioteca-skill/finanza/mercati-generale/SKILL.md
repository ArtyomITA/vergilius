---
name: mercati-generale
description: "Quadro generale dei mercati: difesa, tecnologia, cripto, chi va controcorrente."
version: 1.0.0
category: finanza
tags: [mercati, mercato, borsa, indici, andamento, listino, settore, cripto]
tools: [fin_mercati]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Come vanno i mercati", "come sta la difesa", "novita' finanziarie" (no single named stock).

## Procedure
1. fin_mercati {} (no titolo): difesa, tecnologia, cripto groups, each with prezzo and variazione_pct.
2. Read lettura_difesa.controcorrente: names moving against their sector's average.
3. Read picchi (3 biggest movers) and their ha_notizia flag.
4. Fallback: picchi_senza_notizia present -> say no linked news exists; never blame another ticker's headline.
5. Fallback: non_osservabile present -> say so; it does not mean markets are flat.
6. Check: name the biggest movers, whether each has news, and any sector anomaly.

## Pitfalls
- picchi_senza_notizia: never attribute a move to a different stock's news.
- notizie here cover only defense/tech/crypto tickers, not geopolitics.
- Groups sort by variazione_pct, not by importance for your answer.
