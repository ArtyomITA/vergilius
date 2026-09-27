---
name: articolo-lungo-trova-dato
description: "Trovare un numero, una data o un nome in un articolo lungo o in una tabella."
version: 1.0.0
category: browser
tags: [articolo, pagina, dato, trova, trovami, quanti, quante, quando, tabella, numero]
tools: [browser_open, browser_read, browser_find]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
One page, one fact (text or table): "in che anno fu fondata secondo l'articolo", "quanti dipendenti indica la pagina".

## Procedure
1. browser_open {"url":"<absolute https URL>"}. Fact under "--- page text ---": answer.
2. Else browser_read {} (the start of the article only).
3. Still missing, or the result says "troncato" or "cut": browser_find {"text":"<one rare word next to the fact>"} ("fondat", "dipendenti", "1861"). It returns each matching line with 3 lines around it.
4. No match: one more browser_find with a synonym, a shorter stem or the table column header.
5. Check: quote the line that holds the fact and answer only from it; after two empty browser_find say it is not on this page.

## Pitfalls
- never browser_read {"refs":true} to read an article: it returns the element tree
- "blocked:" (login, captcha) or a paywall "left_open": stop, tell the user, offer another source
