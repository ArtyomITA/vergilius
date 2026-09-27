---
name: cerca-testo-in-file
description: "Cercare una parola dentro i file di una cartella, con il punto esatto dove compare."
version: 1.0.0
category: file
tags: [cerca, trova, parola, testo, dentro, file, grep]
tools: [grep]
status: published
confidence: 0.8
source: user
owner: admin
---

## When to Use
Search text across files in a folder: "cerca la parola 'TODO' in tutti i file della cartella src".

## Procedure
1. grep {"pattern":"<regex>","path":"<folder>"}.
2. Only some file types matter: add {"glob":"*.py"}.
3. Case does not matter: add {"ignore_case":true}.
4. Too many or too few hits: adjust {"max_results":<n>} (capped at 200) or narrow the pattern.
5. Check: quote the file:line:match triples exactly as returned.

## Pitfalls
- pattern is a real regex, not a plain substring: escape . * + ? ( ) [ ].
- matches are capped at 200: say the search was not exhaustive when hit.
- case-sensitive unless ignore_case=true.
