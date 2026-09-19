#!/usr/bin/env bash
# A2 — config quotidiana Linux (display su iGPU Radeon → 1080 quasi headless)
# Validata su Windows 31/07/2026: -fa on (kernel vec Pascal ok, +10%), KV q8_0 senza
# perdita di recall (needle a 13.8K trovato). Headless regge 64K comodi.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$DIR/llama.cpp-src/build/bin/llama-server" \
  -m "$DIR/models/QwenPaw-Flash-9B.i1-Q4_K_M.gguf" \
  --n-gpu-layers 999 \
  --ctx-size 65536 \
  -fa on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --no-mmap --mlock \
  --host 127.0.0.1 --port 8012 "$@"
