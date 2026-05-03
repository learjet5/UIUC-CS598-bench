// Library-link harness for whisper.cpp GHSA-ggml-2025-parser.
//
// Directly invokes gguf_init_from_file() with no_alloc=true; the pre-fix
// parser writes ne[0..n_dims-1] into a 4-element array embedded in the
// gguf_tensor_info struct, so n_dims=255 yields 251 OOB writes that ASAN
// catches as heap-buffer-overflow against the malloc'd ctx->infos array.
//
// Build (run from whisper.cpp repo root):
//   clang -fsanitize=address,undefined -g -O0 -I. \
//     ${POC_DIR}/harness_gguf_load.c \
//     -L build-asan -l:libwhisper.a \
//     -o build-asan/bin/harness_gguf_load
//
// Run:
//   ASAN_OPTIONS=use_sigaltstack=0 ./build-asan/bin/harness_gguf_load <gguf>

#include "ggml.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char ** argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <model.gguf>\n", argv[0]);
        return 1;
    }
    struct gguf_init_params params = {
        /*.no_alloc =*/ true,
        /*.ctx      =*/ NULL,
    };
    struct gguf_context * gguf_ctx = gguf_init_from_file(argv[1], params);
    if (!gguf_ctx) {
        fprintf(stderr, "gguf_init_from_file returned NULL\n");
        return 2;
    }
    fprintf(stderr, "gguf_init_from_file OK; n_tensors=%lld\n",
            (long long)gguf_get_n_tensors(gguf_ctx));
    gguf_free(gguf_ctx);
    return 0;
}
