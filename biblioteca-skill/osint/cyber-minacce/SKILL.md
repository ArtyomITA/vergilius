---
name: cyber-minacce
description: "Minacce cyber vive: malware, vulnerabilita' sfruttate, rischio del paese."
version: 1.0.0
category: osint
tags: [cyber, malware, vulnerabilita, botnet, hacker, minacce]
tools: [osint_cyber]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Quali vulnerabilita' sono sfruttate ora", "server malevoli attivi", "quanto e' a rischio il paese X".

## Procedure
1. One feed: osint_cyber {"azione":"malware"} for botnet C2, osint_cyber {"azione":"vulnerabilita"} for CISA KEV, osint_cyber {"azione":"rischio_paese"} for the index.
2. All three together: osint_cyber {"azione":"tutto"}.
3. Fallback: one source failed inside "tutto" -> report the other two, say which one is missing.
4. Check: answer only with returned fields, no invented CVE or IP.

## Pitfalls
- Live feeds only: for one IP, domain or CVE lookup use a technical-recon skill instead.
- "tutto" can return one source as errore without failing the other two.
- No azione given defaults to "tutto": say so if the user asked for one feed only.
