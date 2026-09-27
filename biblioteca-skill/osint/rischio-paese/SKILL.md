---
name: rischio-paese
description: "Rischio geopolitico previsionale di una regione o classifica globale, non incidenti in corso."
version: 1.0.0
category: osint
tags: [rischio, rischi, dossier, previsione, geopolitico, classifica, regioni]
tools: [osint_rischio]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Dove sta salendo il rischio", "quali regioni sono a rischio", "dammi il dossier di rischio del Sahel". Live incidents now, not a forecast: use luogo-cosa-succede or militare-zona instead.

## Procedure
1. Ranking across regions: osint_rischio {"azione":"classifica","quante":10}.
2. One region in depth: osint_rischio {"azione":"dossier","regione":"<country or region>"}.
3. Refresh on explicit request only: osint_rischio {"azione":"ricalcola"}.
4. Fallback: error naming GT_ANALYTICS_ENABLED -> say the model is off, offer live alerts instead.
5. Check: answer with score and reasoning, say this is a forward outlook, not live incidents.

## Pitfalls
- dossier without regione errors: always name a country or region.
- This is a forecast, not live incidents: different from an alerts feed.
- ricalcola only on explicit request: it recomputes the whole model.
