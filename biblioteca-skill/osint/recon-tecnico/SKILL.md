---
name: recon-tecnico
description: "Indagine tecnica su un IP, dominio, CVE, o il grafo di un'entita'."
version: 1.0.0
category: osint
tags: [ip, dominio, dns, whois, certificato, cve, sanzioni, bgp]
tools: [osint_recon]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
"Cosa sai su questo IP", "controlla questo dominio", "che CVE sono queste", "e' sanzionata questa azienda".

## Procedure
1. osint_recon {"tipo":"<ip|dns|whois|certs|bgp|sanctions|cve|mac|github|leaks|threats>","valore":"<the value>"}.
2. Relationship graph around a known entity: osint_recon {"tipo":"espandi","valore":"<name or id>","entita":"<aircraft|vessel|company|person|ip|country>"}.
3. Fallback: tipo missing or unknown -> pick the closest match from step 1's list, never invent one.
4. Check: answer only with fields returned; say when a lookup came back empty.

## Pitfalls
- Needs both tipo and valore: a bare value with no tipo errors.
- espandi guesses entita as company when the value is not an IPv4: name it if known.
- Slower than a live feed: for cyber threats happening now, use a threat-feed skill instead.
