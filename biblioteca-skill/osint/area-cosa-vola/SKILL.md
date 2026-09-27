---
name: area-cosa-vola
description: "Cosa vola o naviga adesso su una zona: mare, stretto, paese o citta'."
version: 1.0.0
category: osint
tags: [vola, volano, voli, sorvola, aerei, aereo, velivoli, navi, nave, naviga, flotta]
tools: [osint_geocode, osint_militare, osint_mappa]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Military/government aircraft or ships over a sea, strait, country or city now: "cosa vola sopra il Mar Nero".

## Procedure
1. Known name or "lat,lng"; seas need a manual center (Black Sea "43.4,34.3"); else osint_geocode {"azione":"cerca","luogo":"<English name>"} -> risultati[0].lat/.lng.
2. osint_militare {"luogo":"<lat,lng>","raggio_km":<200-650>,"quanti":10}.
3. Fallback: luogo_non_riconosciuto -> redo with "lat,lng".
4. Optional: osint_mappa {"azione":"centra","lat":<lat>,"lng":<lng>,"zoom":5}.
5. Check: state radius, list by tipo and sigla, name empty ones.

## Pitfalls
- navi_militari lists merchant ships too: always give the tipo.
- luogo_non_riconosciuto means WORLD data, not the area asked.
- No airliners here: military/government traffic only.
