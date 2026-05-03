# ncnn ISSUE-6214 darknet2ncnn segfault — provenance

## harness_darknet_cfg.cpp
Adapted from `darknet_cfg.cc` shipped in the issue's attached zip
(https://github.com/user-attachments/files/21435805/ncnn_report.zip).
That source is itself a single-file extraction of ncnn's
`tools/darknet/darknet2ncnn.cpp` parsing routines (load_cfg + parse_cfg
plus the Section/SectionConv/... types) wrapped with a libFuzzer entry.

Two edits applied:
- removed `#include "fuzzer_temp_file.h"` (no longer needed)
- replaced `LLVMFuzzerTestOneInput(data, size)` at the bottom with a
  standalone `main(argc, argv)` that takes argv[1] as the cfg file
  path and calls `load_cfg(...)` + `parse_cfg(...)` directly.

The parsing logic itself is unchanged from the upstream issue zip;
the trigger path is identical to the original libFuzzer harness.

## poc_segfault.bin
Verbatim copy of `input_darknet_seg_fault_lf` (72 bytes) from the same
issue zip. Per the Casr report (`input_darknet_seg_fault_lf.casrep`)
this triggers a SEGV in `load_cfg`.

## Trigger
```
$ ASAN_OPTIONS=use_sigaltstack=0 \
  ./harness_darknet_cfg poc_segfault.bin
```

Expected output line: `Loading cfg...` followed by an
`AddressSanitizer:` panic line (SEGV / heap-buffer-overflow / etc.,
depending on which heap region the malformed pointer dereferences).

## Status
Open in upstream tracker (#6214) since 2025-07-25, never patched
(verified against master commit d0d50631, 2026-04-22).

## License
The harness source is BSD-3-Clause (Tencent's ncnn license).
The original libFuzzer wrapper around it is Apache-2.0 (ISP RAS).
