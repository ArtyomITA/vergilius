---
name: sito-bloccato-cambia-fonte
description: "Pagina con login, captcha o paywall: fermarsi o cambiare fonte senza accettare nulla."
version: 1.0.0
category: browser
tags: [bloccato, paywall, abbonati, abbonamento, login, accedi, captcha, cookie]
tools: [browser_open, browser_read]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
A browser result starts with "blocked: login", "blocked: captcha" or "cookie_banner: left_open" (pay-or-accept walls of big news sites).

## Procedure
1. Read the first two lines of the browser_open or browser_read result: cookie_banner and blocked.
2. "blocked: login" or "blocked: captcha": stop; one sentence to the user with the URL, asking how to continue.
3. "left_open (rejecting needs a paid subscription)": do not read that page; open another source, e.g. browser_open {"url":"<another site that covers the topic>"}.
4. "left_open (reject still in progress, nothing accepted)": browser_read {} once more.
5. Check: the answer names the site it was really read from.

## Pitfalls
- never click Accetta, Accept, OK, Consenti or "Rifiuta e abbonati"; never type credentials
