---
name: apri-passa-app
description: "Aprire o passare a un programma diverso da Calcolatrice, Blocco note o Esplora file."
version: 1.0.0
category: pc
tags: [apri, apre, avvia, passa, finestra, programma, app]
tools: [App]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Bring a Start Menu app to front, or launch it if not open, before any click/type on it: "apri Impostazioni", "passa a Paint".

## Procedure
1. App {"mode":"switch","name":"<Italian Start Menu name>"}. Already open: its window comes to front.
2. Not found or failed: App {"mode":"launch","name":"<same Italian name>"}.
3. Slow app: Wait {"duration":2} before looking again.
4. vista_schermo {"focus":"the window that should now be active"} to confirm which app is in front.
5. Check: name the app now in front; only then use Click or Type on it.

## Pitfalls
- name must be the app's Italian Start Menu name, not the English one: fuzzy match (cutoff 70) can pick the wrong window.
- mode="launch_executable" runs one exact file path and is irreversible: never use it just to open a known app.
