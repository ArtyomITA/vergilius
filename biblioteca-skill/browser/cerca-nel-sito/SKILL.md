---
name: cerca-nel-sito
description: "Usare la casella di ricerca interna di un sito aperto per trovare una pagina o una voce."
version: 1.0.0
category: browser
tags: [cerca, cercami, ricerca, sito, casella, risultati, filtra]
tools: [browser_open, browser_read, browser_find, browser_type, browser_click]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
The user wants something inside one site: "cerca su questo sito le ricette con le zucchine", "usa la ricerca del sito per l'orario del museo".

## Procedure
1. browser_open {"url":"<site home URL>"} if the site is not open yet.
2. browser_find {"text":"searchbox"}; no match: browser_find {"text":"textbox"}. Take the ref of the search field.
3. browser_type {"ref":"<ref from step 2>","text":"<2-4 words>","submit":true}.
4. browser_read {} to read the results; to open one: browser_find {"text":"<word of its title>"}, then browser_click {"ref":"<ref>"}.
5. Check: the answer names the result read on the page; zero results: say so and try once with fewer words.

## Pitfalls
- refs come only from the latest browser_find or browser_read {"refs":true}; never a label or a URL as ref
- do not build search URLs by hand: type into the field
