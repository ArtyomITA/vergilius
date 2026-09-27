---
name: insider-difesa
description: "MSPR e movimenti degli interni nelle aziende della difesa: chi compra o vende."
version: 1.0.0
category: finanza
tags: [insider, mspr, interni, dirigenti, vendite, acquisti, sentiment]
tools: [fin_insider]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"MSPR di Lockheed" (RTX, LMT, NOC, GD, BA, PLTR).

## Procedure
1. fin_insider {"titolo":"<RTX/LMT/NOC/GD/BA/PLTR, or omit for all six>","quanti":12}.
2. Read sentimento_mensile: mspr (-100..+100, saturates), azioni_nette, by forza_segnale.
3. Read movimenti_recenti (only movimenti_su): P/S = real decision; A/M = zero-price grant.
4. Fallback: titolo outside the six is dropped, all six return: check nome first.
5. Check: state MSPR sign and movimenti_su; never call A/M a buy or sell.

## Pitfalls
- MSPR saturates: +100 on 162 shares weighs less than -60 on 180,000.
- Only P/S are decisione_di_mercato; A/M are not buy or sell.
- movimenti_recenti is ONE company (movimenti_su), even omitting titolo.
