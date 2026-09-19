# A2 — config quotidiana Windows (validata 31/07/2026 su GTX 1080 + desktop attivo):
#   Q4_K_M + -fa on + KV q8_0 + 48K → ~27 tok/s gen, ~520 tok/s pp, tool call OK
#   -fa on: kernel vec Pascal funziona, +10% velocità, necessario per KV q8_0
#   48K su Windows (desktop ruba ~1.1GB VRAM); 64K testato ok ma solo 267MiB di margine
& "$PSScriptRoot\..\llama\llama-server.exe" `
  -m "$PSScriptRoot\..\models\QwenPaw-Flash-9B.i1-Q4_K_M.gguf" `
  --n-gpu-layers 999 `
  --ctx-size 49152 `
  -fa on `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --no-mmap --mlock `
  --host 127.0.0.1 --port 8012
