# Avvia llama-swap sulla porta 8012, al posto di llama-server diretto.
# Da qui in poi il modello si sceglie dal menu di Odysseus: llama-swap carica
# la configurazione richiesta e spegne la precedente.
#
# Pannello di controllo (log, caricamento manuale, prove): http://127.0.0.1:8012/ui

# Un llama-server avviato a mano occuperebbe la porta e la VRAM.
Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false

& d:\assistenteeee\llama-swap\llama-swap.exe `
  --config d:\assistenteeee\llama-swap\config.yaml `
  --listen 127.0.0.1:8012 `
  --watch-config
