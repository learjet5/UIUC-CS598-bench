# Metadata TODO — fix_commit corrections

Generated: 2026-05-03 (Phase-1 batch) · Light-updated: 2026-05-03 (post Phase-3)
Tooling: `python3.12 scripts/audit_fix_commits.py`

This file tracks `fix_commit` field issues found while building the runnable
benchmark environment.

> **Note on shallow clones**: the audit reports BAD for any SHA the upstream
> shallow `--depth 1` clone doesn't have. Several of those (e.g. opencv
> 2019-5063 / 5064 / 2023-2617 / 2023-2618; llama.cpp TALOS-2024-1913) have
> verified-real fix_commits (see Resolved table below); the BAD verdict is
> a clone-depth artefact, not a metadata bug. The `EMPTY` entries are the
> ones that genuinely lack a fix_commit upstream.

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

## Resolved during Phase-2/3 (2026-05-03)

Cases that the previous version of this doc listed as still-open but have
since been built into validated bench instances:

| project | id | new status | how |
|---|---|---|---|
| llama.cpp | CVE-2024-42477 | **validated** | Phase-2 RPC server harness `run_rpc_poc.sh` + pwntools PoC; ASAN global-buffer-overflow in `ggml_blck_size`. fix_commit `b72942fa` (b3561) recorded. |
| llama.cpp | CVE-2024-42479 | **validated** | Same harness chain; ASAN write-what-where assertion. Same fix_commit. |
| llama.cpp | CVE-2024-42478 | invalidated_no_poc | Env / harness reused; bench-internal PoC offset didn't match RPC ALLOC_BUFFER reply. |
| llama.cpp | CVE-2025-52566 / CVE-2026-27940 / CVE-2026-33298 / GHSA-19856-{arr,str}exh / GHSA-g4cc-763q-h9h6 | mostly **validated** | Phase-2 reused the `harness_gguf_load.c` library_link pattern across 6 GGUF-parser cases. |
| onnx | CVE-2022-25882 | **validated** | Phase-3 `craft_traversal_model.py` + `run_traversal.py` against onnx 1.12.0; leaks `/etc/passwd`. |
| onnx | CVE-2024-27318 | **validated** | Same harness against onnx 1.15.0 (lstrip-bypass disclosure). Fix in 1.16.0 PR #6051 (`66b7fb6`). |
| ncnn | ISSUE-3503 | **validated** (new entry) | cli_binary on `ncnnoptimize`, inline 4-line .param PoC; never patched upstream — `vulnerable_commit = master HEAD d0d50631`. |
| ncnn | ISSUE-6214-darknet | **validated** (new entry) | Standalone harness adapted from upstream issue zip; UBSan null-deref in `load_cfg`. Same vulnerable_commit. |
| tensorflow | ISSUE-115308 | **validated** (new entry) | TFLite `BuildFromBuffer` heap-buffer-overflow on 8-byte crafted .tflite; v2.18.0. Fix open upstream — no fix_commit yet. |

## Still open (heavy / not-yet-built)

| project | id | reason still open |
|---|---|---|
| opencv | CVE-2025-53644 | JPEG2000 / J2K UAF needs a 5-call decode sequence with two crafted datasets; advisory has embedded C++ but synthesising J2K marker streams is non-trivial. Marked `pending`. |
| onnx | ORT-2024-HIDDENLAYER | onnxruntime not yet cloned; multi-hour build; second-tier per TASK.md. Marked `pending`. |
| pytorch | CVE-2024-31583 | pytorch not yet cloned; multi-hour mobile build; second-tier per TASK.md. Marked `pending`. |
| onnx | CVE-2024-5187 | tar-extraction arbitrary file write in `download_model_with_test_data`; not yet built (different surface from 25882/27318 — needs malicious tar PoC and runtime that exercises the helper). |
| pytorch | CVE-2024-31580 / 31584 / 48063 | python_api class — needs pytorch clone (heavy build), no instance scaffolded yet. |
| tensorflow | 8 yaml entries (CVE-2022-21740 / 29210 / 35939 / 41910 / 23-25664 / 23-25668 / GHSA-pg59-2f92-5cph / GHSA-v6r6-84gr-92rm) | python_api class — kernel-level overflows; would need a TF Python build. ISSUE-115308 (the C++ TFLite case) is the only TF instance built so far. |
| ollama | 5 yaml entries | server class + Go panic crash model; sanitizer-trace fingerprint approach doesn't directly apply. No instances built. |
| ncnn | ISSUE-3503 / ISSUE-6214-darknet | `fix_commit` field is empty (both still open in upstream tracker as of master `d0d50631`). Not a bug — the vuln *is* unfixed. yaml's `vulnerable_commit` correctly pins to that commit. |
| tensorflow | ISSUE-115308 | Same — open in upstream tracker, no fix_commit yet. yaml is correct. |

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
