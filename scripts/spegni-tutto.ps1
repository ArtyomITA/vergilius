# Spegne l'intero stack Vergilius. Contrario di avvia-tutto.ps1.
#
# -TranneOdysseus: lascia in piedi la porta 7000. Lo usa la rotta
#   POST /api/vergilius/spegni, che spegne il resto da qui e poi esce da sola
#   (se questo script uccidesse anche lei, la risposta HTTP al pulsante
#   morirebbe a metà).
#
# Uccisione per ALBERO (taskkill /T): il backend ShadowBroker spawna figli
# (wormhole 8787, ais_proxy) e uvicorn con reload lascia worker sulla porta —
# ucciso solo il padre, la porta resta occupata e il riavvio successivo parla
# col processo vecchio (gia' successo, vedi docs/knowledge/09).

param([switch]$TranneOdysseus)

$porte = @(3000, 8000, 8787, 8100, 8013, 8014, 8012, 5802)
if (-not $TranneOdysseus) { $porte = @(7000) + $porte }

$pids = [System.Collections.Generic.HashSet[int]]::new()
foreach ($porta in $porte) {
    Get-NetTCPConnection -State Listen -LocalPort $porta -ErrorAction SilentlyContinue |
        ForEach-Object { [void]$pids.Add([int]$_.OwningProcess) }
}
# llama-server puo' non avere porte in ascolto mentre carica il modello;
# pocket-tts a volte non risulta proprietario della 8014 nella scansione.
Get-Process llama-server, llama-swap, pocket-tts -ErrorAction SilentlyContinue |
    ForEach-Object { [void]$pids.Add($_.Id) }

foreach ($processo in $pids) {
    if ($processo -le 4) { continue }   # mai System/Idle
    $nome = (Get-Process -Id $processo -ErrorAction SilentlyContinue).ProcessName
    taskkill /PID $processo /T /F 2>$null | Out-Null
    Write-Host "  [giu]  $nome (PID $processo)"
}

# pocket-tts molla la porta con qualche secondo di ritardo dopo il kill:
# controllare troppo presto fa scrivere "ancora aperte" a un log che poi
# risulterebbe bugiardo (successo: 8014 segnata aperta, libera un attimo dopo).
Start-Sleep -Seconds 5
$vive = @()
foreach ($porta in $porte) {
    if (Get-NetTCPConnection -State Listen -LocalPort $porta -ErrorAction SilentlyContinue) { $vive += $porta }
}
if ($vive) { Write-Host "ancora aperte: $($vive -join ', ')" } else { Write-Host "tutto spento." }
