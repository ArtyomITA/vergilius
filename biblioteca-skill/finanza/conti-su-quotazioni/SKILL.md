---
name: conti-su-quotazioni
description: "Calcoli esatti su prezzi, importi, percentuali o cambi valuta: mai a mente."
version: 1.0.0
category: finanza
tags: [calcola, calcolo, conto, conti, totale, percentuale, somma, media, cambio, converti, guadagno, perdita]
tools: [calcola, fin_mercati]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Multi-digit math on prices or amounts: "quanto valgono 30 azioni Leonardo", "di quanto e' salito in percentuale", "convertimi al cambio 0,92".

## Procedure
1. Get numbers: from the message, a chat tool result, or fin_mercati {"titolo":"<name>"} only if live.
2. One call, every expression: calcola {"espressioni":["30 * 25.41","variazione_percento(24.80, 25.41)"]}.
3. Fallback: one errore -> fix only that one, call calcola again.
4. Fallback: conversion with no rate -> ask the user; never invent one.
5. Check: state formula and exact result, currency included; round only in writing.

## Pitfalls
- Never compute a multi-digit result in your head.
- Allowed only: numbers, + - * / % ** ( ), round, abs, min, max, sum, sqrt, media, percento, variazione_percento. No variable names.
- variazione_percento takes the OLD value first.
