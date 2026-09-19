#!/usr/bin/env bash
# Smoke test: /health + chat semplice + tool call, contro llama-server su :8080
set -u
BASE="http://127.0.0.1:8080"

echo "== /health =="
curl -sf "$BASE/health" || { echo "server non risponde"; exit 1; }

echo; echo "== chat semplice =="
t0=$(date +%s.%N)
R=$(curl -sf "$BASE/v1/chat/completions" -H 'Content-Type: application/json' -d '{
  "model": "qwenpaw",
  "messages": [{"role": "user", "content": "Rispondi con una sola parola: quanto fa 7*8?"}],
  "max_tokens": 32
}')
t1=$(date +%s.%N)
echo "$R" | python3 -c 'import sys,json; r=json.load(sys.stdin); print(r["choices"][0]["message"]["content"]); print("tokens:", r["usage"]["completion_tokens"])'
echo "tempo: $(echo "$t1 - $t0" | bc)s"

echo; echo "== tool call =="
R2=$(curl -sf "$BASE/v1/chat/completions" -H 'Content-Type: application/json' -d '{
  "model": "qwenpaw",
  "messages": [{"role": "user", "content": "Che tempo fa a Milano? Usa il tool."}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Ottieni il meteo corrente per una citta",
      "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
      }
    }
  }],
  "max_tokens": 256
}')
echo "$R2" | python3 -c '
import sys, json
r = json.load(sys.stdin)
m = r["choices"][0]["message"]
tc = m.get("tool_calls")
if tc:
    print("TOOL CALL OK:", tc[0]["function"]["name"], tc[0]["function"]["arguments"])
else:
    print("NO tool call. Contenuto:", m.get("content"))
'
