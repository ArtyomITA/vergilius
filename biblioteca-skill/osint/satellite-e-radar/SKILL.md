---
name: satellite-e-radar
description: "Analisi satellitare su un punto: incendi termici, passaggi satellite, anomalie radar SAR."
version: 1.0.0
category: osint
tags: [satellite, satelliti, termico, incendio, radar, sar, passaggi, orbita]
tools: [osint_satellite, osint_sar]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"C'e' un incendio qui", "quali satelliti passano sopra X", "cosa vede il radar vicino a Y".

## Procedure
1. Heat/fire: osint_satellite {"azione":"termico","luogo":"<name or 'lat,lng'>","raggio_km":10}.
2. Overflight prediction: osint_satellite {"azione":"passaggi","luogo":"<same>","ore":24}.
3. Radar anomalies: osint_sar {"azione":"anomalie","luogo":"<same>","raggio_km":50}; no luogo lists recent ones.
4. Fallback: feed off -> say so, offer step 1 instead.
5. Check: answer only with returned data; radar and thermal read different things.

## Pitfalls
- osint_sar writes (centra, aggiungi_area, rimuovi_area, sorveglia) need approval: only on explicit request.
- osint_satellite needs a point: no world-wide call exists.
