---
name: notizie-soggetto
description: "Notizie recenti su un'azienda, persona o organizzazione, e lettura di un articolo."
version: 1.0.0
category: osint
tags: [notizie, news, novita, articoli, articolo, leggimi]
tools: [osint_notizie, osint_web]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Cercami news su Boeing", "novita' su Rheinmetall", "leggimi quell'articolo". News about a PLACE: use luogo-cosa-succede instead.

## Procedure
1. osint_notizie {"soggetto":"<one distinctive name>","giorni":2,"quante":5,"leggi_testo":false}.
2. Read eventi, notizie_finanziarie, web; keep only items whose title names the subject.
3. Read one article: osint_notizie {"id":"<id from step 1>"} or {"url":"<url from step 1>"}.
4. Fallback: nothing relevant -> osint_web {"query":"<subject> news","quanti":5}.
5. Check: answer with 3-5 items, source and date.

## Pitfalls
- soggetto matches inside longer words: use one distinctive name, never a place.
- A quoted stock's own news comes back with its quote already: no extra call here.
- quante, not quanti; leggi_testo defaults true (slow) if omitted.
