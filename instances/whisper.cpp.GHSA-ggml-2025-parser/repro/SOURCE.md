# PoC source provenance — whisper.cpp.GHSA-ggml-2025-parser

| file | source URL | fetched | sha256 | license | modifications |
|------|-----------|---------|--------|---------|---------------|
| `craft_oob_ndims.py` | `projects/whisper.cpp/vulns/GHSA-ggml-2025-parser.yaml::poc_code` (inline-yaml) | 2026-05-03 | `65f51bf5f0271ac46216c839d6fef9fc611a1e6a215436144d6337a006a4c237` | n/a (bench-internal) | none — preserved verbatim from inline yaml |
| `oob_ndims.gguf` | generated locally by `craft_oob_ndims.py` | 2026-05-03 | `94f114ea03b8e630b77b5904ad5a3237e972b7b2d1ba788ab8d19aa5c5ed348f` | n/a | regenerable from craft_oob_ndims.py |

## Reference

- Related advisory (covers the integer-overflow OOB *write* sibling):
  https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-vgg9-87g3-85w8
- This particular n_dims-OOB issue has no CVE. It was identified by reading
  the gguf parser source (see yaml description) and confirmed by the fix
  commit `8f5220d8` "gguf : add input validation, prevent integer overflows"
  (2024-01-29), which adds `ok && (info->n_dims <= GGML_MAX_DIMS)` plus a
  `gguf_tensor_info_sanitize()` helper. Vulnerable commit = `8f5220d8^` =
  `8e391fcf3a7582a64f7adf6f95f7e87177d79e6e`.

## Trigger recipe

```bash
ASAN_OPTIONS=use_sigaltstack=0 \
  ./build-asan/bin/main -m repro/oob_ndims.gguf
# Expected: ASAN heap-buffer-overflow when the parser reads
# info->n_dims=255 from the file then iterates ne[0..254] writing past
# the 4-element ne[] array embedded in the gguf_tensor_info struct.
```
