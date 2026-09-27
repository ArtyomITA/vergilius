---
name: militare-zona
description: "Situazione militare in un'area: aerei, navi, allerte e rischio futuro."
version: 1.0.0
category: osint
tags: [militare, militari, forze, truppe, esercito, flotta, portaerei, caccia]
tools: [osint_geocode, osint_militare, osint_allerte, osint_rischio]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Situazione militare in Polonia", "aerei spia sul Baltico". Whole world: same calls, no luogo.

## Procedure
1. Point: known name or "lat,lng"; else osint_geocode {"azione":"cerca","luogo":"<English name>"} -> risultati[0].lat/.lng.
2. osint_militare {"luogo":"<name or lat,lng>","raggio_km":800,"quanti":15}: totali, per_ruolo, navi_militari.
3. osint_allerte {"luogo":"<same>","raggio_km":800,"quante":10}.
4. Outlook: osint_rischio {"azione":"dossier","regione":"<country>"}.
5. Check: answer with counts by role, callsigns, alerts, empty ones named.

## Pitfalls
- luogo_non_riconosciuto means WORLD data, not the zone asked.
- navi_militari lists merchant ships too: give the tipo.
- osint_militare uses quanti, osint_allerte quante.
