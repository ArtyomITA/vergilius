# Sceglie quale llama-server usa llama-swap: la build locale per Pascal oppure
# la release ufficiale. È una scelta HARDWARE, non di programma.
#
#   .\scripts\vergilius-binario-pascal.ps1              stato attuale
#   .\scripts\vergilius-binario-pascal.ps1 -Pascal      build sm_61 + grafi CUDA
#   .\scripts\vergilius-binario-pascal.ps1 -Ufficiale   release llama.cpp
#
# Perché esiste: su GTX 1080 (sm_61) llama.cpp spegne i grafi CUDA per un gate
# scritto nel 2024 su un modello denso. Il nostro grafo ha 1794 nodi ed è
# limitato dai lanci: accendendoli la generazione passa da 41 a 58 token/s
# (72 su generazione lunga), con risposte identiche carattere per carattere
# (10/10 qui, 18/18 su sei architetture). Misure in ricerche/opt-1080/29 e 33;
# la stessa modifica è in review upstream come PR ggml-org/llama.cpp#27721.
#
# La build sm_61 vale SOLO su Pascal (GTX 10xx, Titan X/Xp, Quadro P, Tesla P).
# Su qualsiasi altra GPU serve la release ufficiale.
#
# Rollback: rilanciare con -Ufficiale. Il file di configurazione viene salvato
# in config.yaml.bak-binario prima di ogni cambio.

param(
    [switch]$Pascal,
    [switch]$Ufficiale
)

$ErrorActionPreference = 'Stop'
$radice     = Split-Path -Parent $PSScriptRoot
$config     = Join-Path $radice 'llama-swap\config.yaml'
$exePascal  = Join-Path $radice 'llama-pre5-b02\llama-server.exe'
$exeUffic   = Join-Path $radice 'llama-cuda124-new\llama-server.exe'

function Percorso-Attuale {
    $riga = Select-String -Path $config -Pattern '^\s*server:\s*"([^"]+)"' | Select-Object -First 1
    if (-not $riga) { throw "riga 'server:' non trovata in $config" }
    return $riga.Matches[0].Groups[1].Value
}

$attuale = Percorso-Attuale
if (-not $Pascal -and -not $Ufficiale) {
    $quale = if ($attuale -like '*llama-pre5-b02*') { 'build Pascal sm_61 (grafi CUDA accesi)' }
             elseif ($attuale -like '*llama-cuda124-new*') { 'release ufficiale llama.cpp' }
             else { 'percorso personalizzato' }
    Write-Host "binario in uso: $quale"
    Write-Host "  $attuale"
    Write-Host ""
    Write-Host "per cambiare:  -Pascal   oppure   -Ufficiale"
    return
}

$nuovoExe = if ($Pascal) { $exePascal } else { $exeUffic }
if (-not (Test-Path $nuovoExe)) { throw "binario assente: $nuovoExe" }

# La GPU deve essere libera: cambiare il server mentre genera lascia llama-swap
# con un processo orfano.
$occupato = (Get-Process llama-server -ErrorAction SilentlyContinue)
if ($occupato) {
    Write-Host "llama-server è in esecuzione (pid $($occupato.Id -join ', '))." -ForegroundColor Yellow
    Write-Host "Spegni Vergilius (scripts\spegni-tutto.ps1) e rilancia questo comando."
    return
}

$nuovoPercorso = ($attuale -replace [regex]::Escape((Split-Path -Leaf (Split-Path -Parent $attuale))), (Split-Path -Leaf (Split-Path -Parent $nuovoExe)))
if ($nuovoPercorso -eq $attuale) { Write-Host "già impostato, niente da fare."; return }

Copy-Item $config "$config.bak-binario" -Force
(Get-Content $config -Raw) -replace [regex]::Escape($attuale), $nuovoPercorso | Set-Content $config -NoNewline -Encoding UTF8

Write-Host "binario aggiornato:" -ForegroundColor Green
Write-Host "  da:  $attuale"
Write-Host "  a:   $nuovoPercorso"
Write-Host "backup: $config.bak-binario"
Write-Host ""
Write-Host "llama-swap ricarica la configurazione da solo (--watch-config)."
Write-Host "Prima prova consigliata: una domanda in chat, poi controlla i token/s nei log."
