# A3 su heretic con vision — il trucco della scheda del modello:
# il proiettore visivo BF16 (879MB) resta sulla RAM di sistema invece che in VRAM
# (--no-mmproj-offload). Costo: qualche decimo di secondo in più per immagine.
# Guadagno: ~900MB di VRAM liberi, che restano al modello e alla cache.
#
# Per questo il contesto qui può restare alto come nella A2, invece dei 16K
# a cui saremmo costretti tenendo il proiettore in GPU.
& "$PSScriptRoot\..\llama\llama-server.exe" `
  -m "$PSScriptRoot\..\models\QwenPaw-Flash-9B-heretic-Q4_K_M.gguf" `
  --mmproj "$PSScriptRoot\..\models\mmproj-heretic-BF16.gguf" `
  --no-mmproj-offload `
  --n-gpu-layers 999 `
  --ctx-size 32768 `
  -fa on `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --temp 1.0 --top-p 0.95 --top-k 20 --presence-penalty 1.5 `
  --no-mmap --mlock `
  --host 127.0.0.1 --port 8012
