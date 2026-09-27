# PROVE: cerca-testo-in-file

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| grep: pattern (required, regex), path opzionale, glob opzionale, ignore_case opzionale, max_results opzionale | odysseus/src/tool_schemas.py:117-130 | F08 |
| output in formato file:line:match | odysseus/src/tool_schemas.py:118 (descrizione) | F08 |
| max_results e' limitato a _CODENAV_MAX_HITS=200 anche se richiesto piu' alto (`max(1, min(max_hits, _CODENAV_MAX_HITS))`) | odysseus/src/agent_tools/filesystem_tools.py:706-709; _CODENAV_MAX_HITS=200 a riga 18 | F08 |
| ignore_case e' False di default (`bool(args.get("ignore_case"))`) | odysseus/src/agent_tools/filesystem_tools.py:703 | F08 |
| pattern e' una vera regex passata al motore (ripgrep se presente, altrimenti `re.compile`): caratteri speciali non sfuggiti cambiano il match | odysseus/src/agent_tools/filesystem_tools.py:60-66 (`_python_grep_worker`, `re.compile(payload["pattern"], flags)`), 700 (pattern passato cosi' com'e' a rg/regex) | F08 |

Token: da misurare con verifica-pc.py.
