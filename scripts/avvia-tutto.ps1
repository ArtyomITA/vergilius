# Avvia SOLO Vergilius Boot (porta 7001): la pagina dei profili, nello stile
# di Odysseus. Finche' l'utente non sceglie, non parte nient'altro.
#
# Profili: shadowbroker, vergilius-chat (niente ShadowBroker), vergilius-lite,
# full. Il loader mostra percentuale e stato reale di ogni componente; a fine
# carico si va a ShadowBroker (:3000) o Vergilius (:7000).
#
# Da riga di comando si puo' saltare la scelta:  -Profilo vergilius-lite
# Spegnere: scripts\spegni-tutto.ps1

param(
    [ValidateSet('selector', 'shadowbroker', 'vergilius-chat', 'vergilius-lite', 'full')]
    [string]$Profilo = 'selector'
)

$ErrorActionPreference = 'Continue'
$logs = 'd:\assistenteeee\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Gia-Su { param([int]$Porta) [bool](Get-NetTCPConnection -State Listen -LocalPort $Porta -ErrorAction SilentlyContinue) }

if (Gia-Su 7001) {
    Write-Host "Vergilius Boot gia' in piedi su :7001"
} else {
    $argomenti = @('d:\assistenteeee\boot\vergilius_boot.py', '--open')
    if ($Profilo -ne 'selector') { $argomenti += @('--profilo', $Profilo) }
    # python di sistema: il boot e' stdlib pura, nessun venv da attivare
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = 'd:\assistenteeee\odysseus\venv\Scripts\python.exe' }
    Start-Process -FilePath $py -ArgumentList $argomenti `
        -WorkingDirectory 'd:\assistenteeee' `
        -RedirectStandardOutput "$logs\boot.out.log" `
        -RedirectStandardError  "$logs\boot.err.log" `
        -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i++) { if (Gia-Su 7001) { break }; Start-Sleep -Milliseconds 250 }
}

Write-Host ""
Write-Host "Vergilius Boot: http://127.0.0.1:7001"
if ($Profilo -eq 'selector') {
    Write-Host "Scegli ShadowBroker, Vergilius Chat, Lite o Full dalla pagina."
} else {
    Write-Host "profilo richiesto: $Profilo"
}
Write-Host "log in:        $logs"
