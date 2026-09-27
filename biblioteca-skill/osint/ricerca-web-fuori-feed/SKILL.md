---
name: ricerca-web-fuori-feed
description: "Ricerca sul web aperto quando i feed della piattaforma non sanno rispondere."
version: 1.0.0
category: osint
tags: [web, internet, online, biografia, wikipedia, sito, background]
tools: [osint_web, osint_notizie, web_search, web_fetch]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Chi e' il ministro della difesa di X", "cosa produce questa azienda", background of a headline, or a briefing answering tema_non_trovato on a question that is not about live data.

## Procedure
1. In Intelligence or Financial profile: osint_web {"query":"<3-6 English keywords>","quanti":5}; add "recenti":"week" for recent facts.
2. To read one result in full: osint_notizie {"url":"<url from step 1>"}.
3. Without a profile: web_search {"query":"<keywords>","time_filter":"week"}, then web_fetch {"url":"<one url>"}.
4. Fallback: zero results -> one retry with simpler English keywords.
5. Check: say the source is the open web and name the site; if still nothing, say the web does not cover it.

## Pitfalls
- Never for live feeds already covered by another skill (flights, ships, alerts, prices).
- No standalone text-reading tool exists, even if older rules still name one.
- One concept per query; English keywords work better here.
