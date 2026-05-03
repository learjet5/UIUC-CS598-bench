# PoC source provenance — llama.cpp.GHSA-vgg9-87g3-85w8

| file | source URL | fetched | sha256 | license | modifications |
|------|-----------|---------|--------|---------|---------------|
| `generate_poc.c` | https://huggingface.co/yuuoniy/overflow/resolve/main/generate_poc.c | 2026-05-03 | `78642bbc54bef0d5a3bd51ffdf96ede08064d3a2749c51d82cb2926ba42e432d` | not stated (HF repo `yuuoniy/overflow`); treated as security-research exhibit | none |
| `overflow_poc.gguf` | https://huggingface.co/yuuoniy/overflow/resolve/main/overflow_poc.gguf | 2026-05-03 | `956b516244ffb8eefd08138e3206f17ea4539836fd4ebd715fa63b763eb14a22` | not stated; treated as security-research exhibit | none |

## Reference advisory

- GitHub Security Advisory: https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-vgg9-87g3-85w8
- HuggingFace artifacts repo: https://huggingface.co/yuuoniy/overflow

## Trigger recipe (per advisory)

```bash
# llama-cli built with -fsanitize=address,undefined at the vulnerable commit
# (5b359bb1e3585de45bec79fd6c18934897662cdf — parent of fix tag b4057)
ASAN_OPTIONS=use_sigaltstack=0 \
  ./build-asan/bin/llama-cli -m repro/overflow_poc.gguf
# Expected: UBSan reports pointer overflow in ggml/src/gguf.cpp,
#           ASAN reports heap-buffer-overflow shortly after.
```

## How to regenerate `overflow_poc.gguf` (verification path)

```bash
gcc generate_poc.c -o /tmp/generate_poc
cd repro && /tmp/generate_poc overflow_poc.gguf
sha256sum overflow_poc.gguf  # should match the table above
```

The C generator computes two F16 tensors whose padded `nbytes` sum overflows
`uint64_t`, causing `ctx->size` to wrap to 1024 bytes — model context buffer
ends up undersized, and tensor-data write triggers a heap OOB.
