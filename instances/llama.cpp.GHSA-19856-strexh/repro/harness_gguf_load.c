// Library-link harness for llama.cpp GHSA-vgg9-87g3-85w8.
//
// Directly invokes gguf_init_from_file() with no_alloc=false, bypassing the
// llama-model-loader file-bounds check that swallows the PoC at the cli_binary
// layer (llama-cli rejects the malicious model before the vulnerable
// ctx->size accumulation has any visible effect).
//
// Build (run from the bench root with the sanitizer build dir in place):
//   clang -fsanitize=address,undefined -g -O0 \
//     -I repos-sanitizer/llama.cpp/ggml/include \
//     repro/harness_gguf_load.c \
//     -L repos-sanitizer/llama.cpp/build-asan/bin -lggml -lggml-base -lggml-cpu \
//     -Wl,-rpath,$PWD/repos-sanitizer/llama.cpp/build-asan/bin \
//     -o repro/harness_gguf_load
//
// Run:
//   ASAN_OPTIONS=use_sigaltstack=0 UBSAN_OPTIONS=print_stacktrace=1 \
//     ./repro/harness_gguf_load repro/overflow_poc.gguf
//
// Expected at vulnerable_commit (ffd59e7d18..., 2025-07-09): UBSan reports
// pointer overflow in ggml_nbytes / ctx->size accumulation in gguf.cpp.
// Expected at fix_commit (26a48ad69..., PR #14595): clean failure with
// "tensor '...' size overflow, cannot accumulate size".

#include "gguf.h"
#include "ggml.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char ** argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <model.gguf>\n", argv[0]);
        return 1;
    }
    struct ggml_context * ctx_data = NULL;
    struct gguf_init_params params = {
        /*.no_alloc =*/ false,
        /*.ctx      =*/ &ctx_data,
    };
    struct gguf_context * gguf_ctx = gguf_init_from_file(argv[1], params);
    if (!gguf_ctx) {
        fprintf(stderr, "gguf_init_from_file returned NULL\n");
        return 2;
    }
    fprintf(stderr, "gguf_init_from_file OK; n_tensors=%lld\n",
            (long long)gguf_get_n_tensors(gguf_ctx));
    gguf_free(gguf_ctx);
    if (ctx_data) ggml_free(ctx_data);
    return 0;
}
