# PoC source provenance — llama.cpp.TALOS-2024-1913

| file | source URL | fetched | sha256 | license | modifications |
|------|-----------|---------|--------|---------|---------------|
| `craft_fread_str_overflow.py` | bench-internal (synthesised; same script as whisper.cpp.TALOS-2024-1914) | 2026-05-03 | `f45347a12e89b25009e2f75560a98c4f46bf40cf6cc4c9f0c9efd12f41fff8fc` | n/a | n/a |
| `fread_str_overflow.gguf` | generated locally by `craft_fread_str_overflow.py` | 2026-05-03 | `1a4707f813e27109510c32394d53eb2d0d6297606efe408a4261dea644fc2415` | n/a | regenerable |
| `harness_gguf_load.c` | bench-internal (same harness as whisper.cpp siblings) | 2026-05-03 | (same content) | n/a | none |

## Reference

- Cisco Talos advisory: https://talosintelligence.com/vulnerability_reports/TALOS-2024-1913
  (CVE-2024-21825; advisory body has ASAN crash output but no standalone PoC)
- Companion advisory (same root cause, whisper.cpp side): TALOS-2024-1914
- Fix: `a4b07c05` "gguf : add input validation, prevent integer overflows
  (ggml/709)" (2024-01-30) — adds `if (p->n == SIZE_MAX) return false`
  early exit in `gguf_fread_str`.

## Trigger recipe

```bash
ASAN_OPTIONS=use_sigaltstack=0 \
  ./build-asan-1913/bin/harness_gguf_load_t1913 repro/fread_str_overflow.gguf
# Expected: ASAN heap-buffer-overflow inside fread, called from
# gguf_fread_str (ggml.c:19261) where calloc(p->n + 1, 1) was given
# p->n=UINT64_MAX, wrapped to calloc(0, 1), then fread tried to write
# 256 bytes into the resulting 1-byte allocation.
```
