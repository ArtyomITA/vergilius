# A3 — vision residente: stesso Q4_K_M (test) o IQ4_XS + mmproj, ctx 16K
# Prima prova col Q4_K_M: se OOM → scaricare IQ4_XS o usare mmproj-Q8_0
param(
  [string]$Model = "QwenPaw-Flash-9B.i1-Q4_K_M.gguf",
  [string]$Mmproj = "QwenPaw-Flash-9B.mmproj-Q8_0.gguf",
  [int]$Ctx = 16384
)
& "$PSScriptRoot\..\llama\llama-server.exe" `
  -m "$PSScriptRoot\..\models\$Model" `
  --mmproj "$PSScriptRoot\..\models\$Mmproj" `
  --n-gpu-layers 999 `
  --ctx-size $Ctx `
  -fa on `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --no-mmap --mlock `
  --host 127.0.0.1 --port 8012
