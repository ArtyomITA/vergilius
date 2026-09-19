# Smoke test: 1 chat semplice + 1 tool call, contro llama-server su :8080
$base = "http://127.0.0.1:8012"

Write-Host "== /health =="
Invoke-RestMethod "$base/health"

Write-Host "`n== chat semplice =="
$t0 = Get-Date
$r = Invoke-RestMethod "$base/v1/chat/completions" -Method Post -ContentType 'application/json' -Body (@{
  model = "qwenpaw"
  messages = @(@{ role = "user"; content = "Rispondi con una sola parola: quanto fa 7*8?" })
  max_tokens = 32
} | ConvertTo-Json -Depth 5)
$dt = ((Get-Date) - $t0).TotalSeconds
Write-Host $r.choices[0].message.content
Write-Host ("tokens: {0} in {1:N1}s" -f $r.usage.completion_tokens, $dt)

Write-Host "`n== tool call =="
$body = @{
  model = "qwenpaw"
  messages = @(@{ role = "user"; content = "Che tempo fa a Milano? Usa il tool." })
  tools = @(@{
    type = "function"
    function = @{
      name = "get_weather"
      description = "Ottieni il meteo corrente per una città"
      parameters = @{
        type = "object"
        properties = @{ city = @{ type = "string" } }
        required = @("city")
      }
    }
  })
  max_tokens = 256
} | ConvertTo-Json -Depth 10
$r2 = Invoke-RestMethod "$base/v1/chat/completions" -Method Post -ContentType 'application/json' -Body $body
$tc = $r2.choices[0].message.tool_calls
if ($tc) { Write-Host "TOOL CALL OK:" $tc[0].function.name ($tc[0].function.arguments) }
else { Write-Host "NO tool call. Contenuto:" $r2.choices[0].message.content }
