---
name: radio-sigint
description: "Scanner radio o SDR vicino a un punto, o messaggi datalink di un aereo."
version: 1.0.0
category: osint
tags: [radio, scanner, sdr, kiwisdr, acars, datalink, ascolto]
tools: [osint_radio]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Scanner vicino a X", "quale radio ascolto da qui", "messaggi datalink del volo Y".

## Procedure
1. Nearest public-safety scanner: osint_radio {"azione":"scanner","luogo":"<name or 'lat,lng'>"}.
2. Nearest SDR receivers: osint_radio {"azione":"kiwisdr","luogo":"<same>"}.
3. Aircraft datalink: osint_radio {"azione":"acars","aereo":"<icao24, registration or callsign>"}.
4. Fallback: scanner/kiwisdr with no place resolved -> ask for a city or "lat,lng".
5. Check: answer only with entries returned; say when none are nearby.

## Pitfalls
- scanner and kiwisdr need a place; acars needs an aircraft, not a place.
- acars guesses the format (hex, registration or callsign) from the string you send.
- Empty result means nothing nearby, not that the tool failed.
