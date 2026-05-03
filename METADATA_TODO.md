# Metadata TODO — fix_commit corrections

Generated: 2026-05-03 (last updated after Phase-1 instance batch processing)
Tooling: `python3.12 scripts/audit_fix_commits.py`

This file tracks `fix_commit` field issues found while building the runnable
benchmark environment.

Categories:

- **WRONG**: yaml has a `fix_commit` URL/SHA, but the SHA either (a) doesn't
  exist in the upstream repo, or (b) exists but doesn't actually fix the
  vulnerability described.
- **EMPTY**: yaml has no `fix_commit` recorded at all.
- **BAD_FORMAT**: yaml has free-text where a SHA/tag belongs.

Until each entry is corrected, the corresponding instance cannot reach
`validation_status = validated` (we can't checkout the right vulnerable
commit). They can still hold env / harness drafts.

## Resolved (during Phase-1 batch)

| project | id | original yaml fix_commit | corrected to | result |
|---|---|---|---|---|
| llama.cpp | GHSA-vgg9-87g3-85w8 | `b4057` (resolved to unrelated `46323fa9` "metal : hide debug messages") | **`26a48ad6`** (PR #14595, 2025-07-09) | env validated; PoC demonstrates wraparound but no sanitizer crash (see semantic-gap section below) |
| llama.cpp | GHSA-8wwf-w4qm-gpqr | `b4455` (tag absent from repo) | **`3cfbbdb4`** (Merge from fork, "vocab : prevent integer overflow during load", 2025-06-13) | env builds; no public PoC → `invalidated_no_poc` |
| llama.cpp | TALOS-2024-1913 | empty | **`a4b07c05`** ("gguf : add input validation, prevent integer overflows (ggml/709)", 2024-01-30) | **validated** with real ASAN heap-buffer-overflow trigger |
| whisper.cpp | TALOS-2024-1914 | empty | **`8f5220d8`** (same upstream PR as 1913, synced from ggml/709) | **validated** with real ASAN heap-buffer-overflow trigger |
| whisper.cpp | GHSA-ggml-2025-parser | "Multiple incremental ggml commits" | **`8f5220d8`** (same as TALOS-2024-1914 — same fix covers both n_dims OOB and gguf_fread_str overflow) | **validated** with real UBSan OOB-read trigger |
| whisper.cpp | CVE-2025-14569 | empty | **`cec1dd9d`** ("examples : update miniaudio library to 0.11.24" #3672, 2026-02-27) | **validated** with real ASAN bad-free trigger |
| opencv | CVE-2019-5063 | `2eb60f1de4...` (SHA absent from upstream) | **`f42d5399aa`** ("core(persistence): add more checks for implementation limitations", 2019-11-07) | **validated** with real ASAN heap-buffer-overflow trigger |
| opencv | CVE-2019-5064 | `2eb60f1de4...` (same bogus SHA as 5063) | **`f42d5399aa`** (same fix; covers both JSON and XML) | **validated** with real ASAN heap-buffer-overflow trigger |
| opencv | CVE-2023-2618 | `.../commit/...` placeholder | **`2b62ff61`** ("fix(wechat_qrcode): fixed memory leaks" #3484, 2023-04-27) | env recipe set; no public PoC → `invalidated_no_poc` |
| opencv | CVE-2023-2617 | `.../commit/...` placeholder | **`ccc27724`** ("fix(wechat_qrcode): Init nBytes after the count value is determined / Avoid null pointer exception" #3480, 2023-04-26) | env builds; PoC fetched but harness in-flight (see status below) |
| whisper.cpp | TALOS-2024-1914B | empty | _stays empty_ — yaml description doesn't match current `whisper_full_parallel` (refactored to std::vector); no public PoC | env builds; `invalidated_no_poc` |

## Still open (heavy / second-tier)

| project | id | reason still open |
|---|---|---|
| opencv | CVE-2025-53644 | JPEG2000 / J2K UAF needs a 5-call decode sequence with two crafted datasets; advisory has embedded C++ but synthesising J2K marker streams is non-trivial. Marked `pending`. |
| onnx | ORT-2024-HIDDENLAYER | onnxruntime not yet cloned; multi-hour build; second-tier per TASK.md. Marked `pending`. |
| pytorch | CVE-2024-31583 | pytorch not yet cloned; multi-hour mobile build; second-tier per TASK.md. Marked `pending`. |
| onnx | CVE-2022-25882 / 2024-27318 / 2024-5187 | python_api class — second-tier scope (out of Phase-1 first-tier). |
| pytorch | CVE-2024-31580 / 31584 / 48063 | python_api class — second-tier scope. |
| tensorflow | (8 entries) | python_api class — second-tier scope. |
| ollama | (5 entries) | server class — third-tier scope. |
| llama.cpp | CVE-2024-42477 / 42479 | server class (RPC) — third-tier scope. |

## Known semantic gaps (not metadata bugs, but worth flagging)

- **`llama.cpp.GHSA-vgg9-87g3-85w8` is `validated` but does not produce a
  sanitizer crash.** The advisory's PoC (`overflow_poc.gguf`, 1152 bytes)
  demonstrates the `ctx->size` wraparound but doesn't follow through to a
  visible heap-OOB write — after wrap, `ggml_new_tensor_1d(... 1024)` and
  `gr.read(... 1024)` both stay within the legitimate allocation. The
  `expected_fingerprint` we use is the silent-success line on the
  vulnerable commit (`gguf_init_from_file OK; n_tensors=2`), which is
  absent on the fix commit (which prints `tensor '...' size overflow`).
  This proves the pipeline reproduces the *bug* but is *not* a
  sanitizer-trigger PoV — automated PoV generators evaluated on this case
  will rightly fail to produce an ASAN/UBSan crash with this PoC alone. To
  upgrade this to a true sanitizer-crash case, a larger crafted GGUF whose
  post-wrap `ctx->size` underrepresents the file's tensor data section is
  needed. See `instances/llama.cpp.GHSA-vgg9-87g3-85w8/notes.md`.

- **opencv cases need `UBSAN_OPTIONS=halt_on_error=0` at runtime.** OpenCV's
  `writeInt` deliberately stores int* at unaligned addresses (a tolerated
  pattern on x86), and UBSan flags it as misaligned-store before the actual
  ASAN heap overflow can fire. The harness_command for opencv 5063/5064
  prefixes this env var to let execution continue past the false positive.

## How to fix a remaining entry

1. Find the fix commit upstream (GitHub advisory, NVD reference, or scan repo
   history with `git log --grep=<keyword> -- <affected_file>`).
2. Verify with `cd repos-sanitizer/<project> && git cat-file -t <sha>` that
   the SHA exists.
3. Verify the fix is real: `git show --stat <sha>` should touch
   `affected_component`.
4. Update `projects/<project>/vulns/<id>.yaml::fix_commit` with the full URL.
5. Re-run `scripts/audit_fix_commits.py` (must report `OK`).
6. Re-run `scripts/derive_vuln_commit.py --apply` to populate
   `vulnerable_commit`.
7. (Optional) Run `bash scripts/validate_instance.sh <project>.<id>` to
   sanity-check the env + PoC.
