---
name: aspetta-waitfor
description: "Aspettare che compaia una finestra o un elemento prima di continuare."
version: 1.0.0
category: pc
tags: [aspetta, attendi, aspettare, compare, carica, apparire, finestra]
tools: [App, WaitFor]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Wait for a slow app or element instead of guessing a delay: "apri il Blocco note e aspetta che compaia prima di scrivere".

## Procedure
1. App {"mode":"launch","name":"<Italian app name>"} (or "switch").
2. WaitFor {"condition":"active_window","window_name":"<app>","timeout":10}.
3. Waiting for one control instead: WaitFor {"condition":"element_exists","text":"<label>","timeout":10}.
4. Result says the condition was NOT met in time: that is a normal answer, not a crash; say so.
5. Check: confirm the window or element is really there before typing or clicking.

## Pitfalls
- timeout must be over 0 and at most 120s, interval at most 5s: pick 5-15s.
- valid conditions: text_exists, active_window, element_exists, element_enabled, focused_element.
- a timeout result just means "not there yet": do not retry it blindly in a loop.
