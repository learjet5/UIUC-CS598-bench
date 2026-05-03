# PoC source provenance — whisper.cpp.TALOS-2024-1914

| file | source URL | fetched | sha256 | license | modifications |
|------|-----------|---------|--------|---------|---------------|
| `craft_fread_str_overflow.py` | bench-internal (synthesised from yaml description + ggml.c source analysis) | 2026-05-03 | `f45347a12e89b25009e2f75560a98c4f46bf40cf6cc4c9f0c9efd12f41fff8fc` | n/a | n/a |
| `fread_str_overflow.gguf` | generated locally by `craft_fread_str_overflow.py` | 2026-05-03 | `1a4707f813e27109510c32394d53eb2d0d6297606efe408a4261dea644fc2415` | n/a | regenerable |
| `harness_gguf_load.c` | copied from `instances/whisper.cpp.GHSA-ggml-2025-parser/repro/` | 2026-05-03 | (same content, same purpose) | n/a | none |

## Reference

- Cisco Talos advisory: https://talosintelligence.com/vulnerability_reports/TALOS-2024-1914
  (no standalone PoC published, only ASAN crash output in advisory body)
- Companion advisory (same root cause, llama.cpp side): TALOS-2024-1913
- Fix: same commit `8f5220d8` that addresses GHSA-ggml-2025-parser (adds
  `if (p->n == SIZE_MAX) return false` early exit in `gguf_fread_str`).

## Trigger recipe

```bash
ASAN_OPTIONS=use_sigaltstack=0 \
  ./build-asan/bin/harness_gguf_load_t1914 repro/fread_str_overflow.gguf
# Expected: ASAN heap-buffer-overflow inside fread, called from
# gguf_fread_str (ggml.c:19231) where calloc(p->n + 1, 1) was given
# p->n=UINT64_MAX, wrapped to calloc(0, 1), then fread tried to write
# 256 bytes into the resulting 1-byte allocation.
```
