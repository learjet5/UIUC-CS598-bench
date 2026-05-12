# Notes — llama.cpp.GHSA-vgg9-87g3-85w8

## Important: what `validated` means here

The `validation_status: validated` for this case means **the PoC reproduces
the wraparound bug** (i.e. on the vulnerable commit, `gguf_init_from_file`
silently accepts the malicious model whose tensor metadata sums to a
size_t overflow; on the fix commit, the same input is rejected with a
"size overflow, cannot accumulate size" error). It does **NOT** mean a
sanitizer (ASAN/UBSan) crash is observable from this PoC alone.

Why: the PoC's `overflow_poc.gguf` constructs two F16 tensors whose padded
nbytes sum overflows `uint64_t`, causing `ctx->size` to wrap to 1024 bytes.
At the vulnerable commit, the call succeeds; at the fix commit, the new
`SIZE_MAX - ctx->size < padded_size` check rejects it. But because the PoC
file itself is only 1152 bytes and `ctx->size` wraps to 1024, the subsequent
`gr.read(data->data, 1024)` stays within the small buffer — no observable
heap OOB on this specific input.

To turn this into a sanitizer-crashing PoC you would need a larger input
file with non-trivial tensor data section that lets `ctx->size` (post-wrap)
underrepresent the real buffer needed. The advisory's PoC stops at
demonstrating the wraparound, not at exploiting it.

## fix_commit metadata bug (yaml)

`projects/llama.cpp/vulns/GHSA-vgg9-87g3-85w8.yaml` lists `fix_commit:
"https://github.com/ggml-org/llama.cpp/commit/b4057"`. Tag `b4057` resolves
to commit `46323fa9` "metal : hide debug messages from normal log" — totally
unrelated to int overflow.

Real fix: PR #14595 = commit `26a48ad699d50b6268900062661bd22f3e792579`
(2025-07-09, "ggml : prevent integer overflow in gguf tensor size
calculation"). Vulnerable commit (parent) =
`ffd59e7d18a76459d5c31ba97073c7c9d73cb752`.

## triggerable_class change

Vuln yaml originally classified this as `cli_binary` (trigger via `llama-cli
-m <gguf>`), but `llama-cli` rejects the PoC at the `llama-model-loader`
file-bounds check (`tensor 'tensor_B' data is not within the file bounds`),
which fires *before* the gguf int-overflow path is reached. Reclassified as
`library_link` and shipped a small harness (`repro/harness_gguf_load.c`)
that calls `gguf_init_from_file()` directly with `no_alloc=false`.

## Build prereqs

- clang/clang++ (any version supporting `-fsanitize=address,undefined`); host
  has clang-11. ASAN runtime requires `ASAN_OPTIONS=use_sigaltstack=0` on
  this host (see workspace CLAUDE.md §2.2).
- cmake ≥ 3.14
- libcurl-dev (cmake --find-package CURL is required by llama)

## Local-only build

`build_sh_sanitizer` only builds the three ggml targets (`ggml`, `ggml-base`,
`ggml-cpu`) — not `llama-cli`, server, or tests. Then directly compiles +
links the harness against `libggml.so` / `libggml-base.so`. Total wall time
~5 min on a 2-core box; ~1 min incremental.
