# A2 su QwenPaw-Flash-9B-heretic — stessa configurazione della A2 standard.
#   Q4_K_M + flash attention + KV q8_0 + 48K di contesto, tutto in GPU.
# Campionamento consigliato dalla scheda del modello: temp 1.0, top_p 0.95,
# top_k 20, presence_penalty 1.5.
& "$PSScriptRoot\..\llama\llama-server.exe" `
  -m "$PSScriptRoot\..\models\QwenPaw-Flash-9B-heretic-Q4_K_M.gguf" `
  --n-gpu-layers 999 `
  --ctx-size 49152 `
  -fa on `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --temp 1.0 --top-p 0.95 --top-k 20 --presence-penalty 1.5 `
  --no-mmap --mlock `
  --host 127.0.0.1 --port 8012
