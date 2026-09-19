#!/usr/bin/env bash
# A3 — vision: Q4_K_M + mmproj Q8_0, KV q8_0, 16K ctx
# Se OOM: mmproj Q8_0 già scelto (624MB vs 918MB f16); poi scendere ctx a 12288
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$DIR/llama.cpp-src/build/bin/llama-server" \
  -m "$DIR/models/QwenPaw-Flash-9B.i1-Q4_K_M.gguf" \
  --mmproj "$DIR/models/QwenPaw-Flash-9B.mmproj-Q8_0.gguf" \
  --n-gpu-layers 999 \
  --ctx-size 16384 \
  -fa on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --no-mmap --mlock \
  --host 127.0.0.1 --port 8012 "$@"
