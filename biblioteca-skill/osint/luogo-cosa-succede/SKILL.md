---
name: luogo-cosa-succede
description: "Cosa succede in un luogo o intorno a esso adesso: eventi, allerte, movimenti."
version: 1.0.0
category: osint
tags: [succede, succedendo, successo, vicino, intorno, dintorni, zona]
tools: [osint_geocode, osint_zona, osint_notizie, osint_allerte, osint_situazione]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Cosa succede a Odessa", "cosa c'e' vicino a Kharkiv".

## Procedure
1. Point: known name or "lat,lng"; else osint_geocode {"azione":"cerca","luogo":"<English name>"} -> risultati[0].lat/.lng.
2. osint_zona {"luogo":"<name or lat,lng>","raggio_km":200}: read vicino.<layer>, layer_vuoti.
3. If asked: osint_notizie {"luogo":"<same>","giorni":2,"quante":5,"leggi_testo":false}, or osint_allerte {"luogo":"<same>","raggio_km":300,"quante":10}.
4. World: osint_situazione {"quanti":8}.
5. Check: answer with counts and sources per layer, naming empty ones.

## Pitfalls
- Short names match inside longer ones (Romania gives Roma).
- osint_notizie, osint_allerte use quante; osint_zona has neither.
- osint_zona requires luogo.
