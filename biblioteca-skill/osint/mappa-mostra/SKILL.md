---
name: mappa-mostra
description: "Muovere o filtrare la mappa: centrare, evidenziare, accendere livelli."
version: 1.0.0
category: osint
tags: [mappa, mostrami, evidenzia, centra, zooma, zoom, nascondi, livelli]
tools: [osint_mappa, osint_geocode]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Mostrami X sulla mappa", "centra su", "evidenzia", "solo voli militari".

## Procedure
1. A place: osint_mappa {"azione":"centra","lat":<lat>,"lng":<lng>,"zoom":<5-10>}; a name/id works as "luogo".
2. Items: after a data tool, osint_mappa {"azione":"evidenzia","ids":["<ids from result>"]}.
3. Layers: osint_mappa {"azione":"livelli","accendi":["military_flights","ships"]}.
4. Fallback: centra fails -> osint_geocode {"azione":"cerca","luogo":"<English name>"}.
5. Check: state what the map now shows.

## Pitfalls
- evidenzia, livelli, preset ask approval and end the turn.
- ids only from results already in this chat.
- livelli AND preset switch everything else off; evidenzia does not.
