# Notes — whisper.cpp.GHSA-ggml-2025-parser

## Status

- triggerable_class: library_link
- PoC: synthesised from yaml's inline `poc_code` (Python script in repro/)
- vulnerable_commit: `8e391fcf3a` (parent of fix `8f5220d8`); set in instance.json
- validation_status: `validated` — UBSan reports out-of-bounds read on the
  vulnerable commit and the bounds check `(info->n_dims <= GGML_MAX_DIMS)`
  on the fix commit prevents it.

## Sanitizer fingerprint

```
ggml.c:19400:49: runtime error: index 5 out of bounds for type 'uint64_t [4]'
    #0 gguf_init_from_file ggml.c:19400:49
    #1 main harness_gguf_load.c:30:38
SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ggml.c:19400:49
```

The vulnerable line is the inner loop:

```c
ok = ok && gguf_fread_el (file, &info->n_dims, sizeof(info->n_dims),  &offset);
for (uint32_t j = 0; j < info->n_dims; ++j) {
    ok = ok && gguf_fread_el(file, &info->ne[j], sizeof(info->ne[j]), &offset);
}
```

`info->ne` is a fixed-size `int64_t[GGML_MAX_DIMS=4]`, but `info->n_dims` is
read straight from the file with no upper bound. With `n_dims=255`, the loop
overruns by 251 elements into the next `gguf_tensor_info` struct in the
malloc'd `ctx->infos[]` array.

## Why library_link

Tried `main -m oob_ndims.gguf` first; main needs a wav file via `-f` to
exercise the model-load path, so reaching the gguf parser through main is
awkward. The library_link harness (`harness_gguf_load.c`) calls
`gguf_init_from_file` directly with `no_alloc=true`, which is the most direct
exercise of the parser.

## fix_commit metadata bug (yaml)

`fix_commit` originally read "Multiple incremental ggml commits" — too vague
to drive a checkout. Replaced with `8f5220d8` (synced from ggml/709,
2024-01-29, "gguf : add input validation, prevent integer overflows"). See
METADATA_TODO.md.
