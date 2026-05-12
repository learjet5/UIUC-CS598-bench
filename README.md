# SEC4AI-bench for UIUC CS598 Course

A vulnerability benchmark for **C/C++ memory-safety bugs in the AI software
ecosystem**, built as the course project for **UIUC CS598 (Software
Engineering for GenAI)**.

The benchmark targets the kinds of vulnerabilities that automated PoV
(proof-of-vulnerability) generators and security agents must reason about in
real, modern AI infrastructure: GGUF model parsers, tensor kernels, model
loaders, image/audio decoders, RPC servers, and Python bindings around C++
backends.

## Scope

Each entry in the benchmark satisfies all of:

- **Language**: primary implementation in C or C++ (Python/Go bindings into
  C/C++ allowed when the bug is in the native layer).
- **Bug class**: memory-safety vulnerabilities are in scope by default
  (heap/stack overflows, use-after-free, OOB read/write, integer overflows,
  uninitialised reads, type confusion). Selected non-memory bugs (path
  traversal, deserialization RCE, arbitrary file write) are included where
  they affect AI-specific code paths.
- **Project relevance**: software in the AI training/inference/serving stack
  — frameworks (TensorFlow, PyTorch), inference engines (llama.cpp,
  whisper.cpp, ollama), model formats (ONNX), or foundational libraries
  consumed by AI applications (OpenCV).
- **Project significance**: maintained by major industry/foundation actors or
  with strong academic/community traction; long-tail or hobby projects are
  excluded.

## Repository layout

```
UIUC-CS598-bench/
├── index.yaml              # master index — one row per (project, vuln)
├── projects/
│   └── <project>/
│       ├── project.yaml    # project metadata + build prerequisites
│       └── vulns/
│           └── <vuln-id>.yaml   # one file per vulnerability (editorial source)
├── instances/
│   ├── README.md
│   └── <project>.<vuln-id>/
│       ├── instance.json   # runnable descriptor (loader-friendly)
│       ├── repro/          # ground-truth PoC + provenance (SOURCE.md)
│       ├── notes.md        # case-specific gotchas
│       └── patch.diff      # optional: extracted from fix_commit
├── schema/
│   ├── vuln.schema.yaml         # editorial schema for projects/*/vulns/*.yaml
│   └── instance.schema.json     # JSON Schema for instances/*/instance.json
└── scripts/
    ├── clone_all.sh                  # clone projects under repos-{sanitizer,llvm-cov}/
    ├── derive_vuln_commit.py         # populate vulnerable_commit = fix_commit^
    ├── audit_fix_commits.py          # verify fix_commit SHAs exist in clones
    ├── build_instance_shells.py      # scaffold instance.json for new cases
    ├── validate_instance_schema.py   # JSON Schema check for all instances
    ├── validate_instance.sh          # build + trigger + fingerprint-match one instance
    └── validate_all.sh               # batch-run validate_instance.sh + emit CSV
```

## Two layers: editorial vs. runnable

The benchmark separates **editorial metadata** (under `projects/`) from
**runnable instances** (under `instances/`):

- `projects/<project>/vulns/<id>.yaml` is the human-authored source of truth:
  description, references, CWE, severity, affected versions, PoC notes. Use
  it for documentation, statistics, and cross-references.
- `instances/<project>.<id>/instance.json` is the machine-consumable
  descriptor a benchmark loader (e.g. an automated PoV generator) reads to
  build, run, and validate one case end-to-end. It mirrors a subset of the
  vuln yaml fields plus a fingerprint and runtime status.

Repository checkouts live **outside** the bench tree so that the bench can be
relocated without touching every instance file. By convention:

- `<bench-parent>/repos-sanitizer/<project>/` — sanitizer-instrumented clone
- `<bench-parent>/repos-llvm-cov/<project>/` — coverage-instrumented clone

This dual-clone layout matches the convention used in SEC-bench and lets a
loader derive both paths from a single `--bench-root` argument.

## Per-vulnerability runnable artefacts

Every `instances/<project>.<id>/` records, at a minimum:

- `base_commit`: the SHA at which the bug is reproducible (typically
  `fix_commit^`, populated by `scripts/derive_vuln_commit.py`).
- `build_sh_sanitizer` / `build_sh_cov`: shell snippets that produce an
  ASAN/UBSan-instrumented binary and an llvm-cov-instrumented binary
  respectively. Local-target-only builds are preferred where possible (e.g.
  the three ggml libraries instead of a full llama.cpp build, or the
  affected OpenCV module instead of a full OpenCV build).
- `harness_command`: a CLI template that feeds a testcase to the build
  artefact. Uses `<path/to/testcase>`, `${REPO}`, and `${POC_DIR}` as
  placeholders that the runner substitutes.
- `vuln_location`: `<file>:<line>` pointer at the vulnerable code, suitable
  for tools that operate in a "vuln-location" mode rather than from a full
  sanitizer report.
- `triggerable_class`: one of `cli_binary`, `library_link`, `python_api`,
  `server` — drives the harness execution strategy.
- `expected_fingerprint`: a multi-line string compared (substring-match) to
  the harness output to decide whether the PoV triggered the **intended**
  vulnerability rather than an unrelated crash.
- `validation_status`: ground-truth label, one of `validated`,
  `invalidated_no_poc`, `invalidated_poc_failed`.

## Validation workflow

Construction proceeds in three stages.

1. **Editorial.** Each new vuln gets a yaml under `projects/<project>/vulns/`
   with description, references, and `fix_commit`. Statistics in
   `index.yaml` are kept consistent.
2. **Scaffold.** Run `scripts/clone_all.sh <project>` to obtain the
   sanitizer + coverage clones. Run `scripts/build_instance_shells.py` to
   create per-instance directories with project-default build/harness
   templates and TODO markers.
3. **Validate.** For each instance, customise the build/harness, drop a
   working PoC into `repro/` (with provenance recorded in `repro/SOURCE.md`),
   then run:
   ```bash
   bash scripts/validate_instance.sh <project>.<vuln-id>
   ```
   The script checks out `base_commit`, runs `build_sh_sanitizer`, executes
   `harness_command` against the PoC, compares output to
   `expected_fingerprint`, and writes back `validation_status`.

For cases without a public PoC, the environment is still built and the
instance is labelled `invalidated_no_poc` so consumers know the build
recipe is usable even though crash reproduction is unverified.

## Quick start

```bash
# 1. Clone the first-tier projects (~1.7 GB; uses --reference to share
#    git objects between repos-sanitizer/ and repos-llvm-cov/).
bash scripts/clone_all.sh

# 2. Verify the schemas for every instance.
python3.12 scripts/validate_instance_schema.py

# 3. Audit fix_commit metadata against the actual clones (catches dropped
#    tags, truncated SHAs, and SHAs absent from the upstream history).
python3.12 scripts/audit_fix_commits.py

# 4. Validate one instance end-to-end.
bash scripts/validate_instance.sh llama.cpp.GHSA-vgg9-87g3-85w8

# 5. Or batch-validate everything (writes validation_summary.csv).
bash scripts/validate_all.sh
```

## Schema

- `schema/vuln.schema.yaml` — annotated reference for editorial fields under
  `projects/<project>/vulns/`.
- `schema/instance.schema.json` — JSON Schema (draft 2020-12) enforcing the
  shape of every `instance.json`. Used by
  `scripts/validate_instance_schema.py`.

## Status

**25 runnable instances** across 6 projects (llama.cpp, whisper.cpp, opencv,
ncnn, onnx, tensorflow): **20 `validated`** (canonical sanitizer / abort
trace reproduced) + **5 `invalidated_no_poc`** (env builds cleanly, no
public PoC). The editorial layer under `projects/<proj>/vulns/` catalogues
45 vulnerabilities across 8 projects in total (ollama and pytorch are
catalogued but not yet built).

### Ready instances (25 / 25)

`validated` = bench locally reproduced the canonical sanitizer / abort
trace. `invalidated_no_poc` = env builds cleanly but no public PoC
exists; build_sh + harness + vuln_location are usable for tools that
generate their own PoVs from `vuln_location` alone.

| project | instance_id | class | status | fingerprint hint |
|---|---|---|---|---|
| llama.cpp | `llama.cpp.CVE-2024-42477` | server | validated | ASAN global-buffer-overflow in `ggml_blck_size` via RPC `rpc_server::deserialize_tensor` |
| llama.cpp | `llama.cpp.CVE-2024-42479` | server | validated | RPC `Assertion 'ne % ggml_blck_size(type) == 0' failed` |
| llama.cpp | `llama.cpp.CVE-2026-27940` | library_link | validated | ASAN allocation-size-too-big in `posix_memalign` from `ggml_aligned_malloc` |
| llama.cpp | `llama.cpp.CVE-2026-33298` | library_link | validated | `failed to read tensor data binary blob` (nbytes wraparound) |
| llama.cpp | `llama.cpp.GHSA-19856-arrexh` | library_link | validated | `gguf_read_emplace_helper: encountered length_error while reading value for key` |
| llama.cpp | `llama.cpp.GHSA-19856-strexh` | library_link | validated | `terminate called after throwing an instance of std::length_error` |
| llama.cpp | `llama.cpp.GHSA-g4cc-763q-h9h6` | cli_binary | validated | ASAN heap-buffer-overflow in `llama_vocab` print_info → id_to_token |
| llama.cpp | `llama.cpp.GHSA-vgg9-87g3-85w8` | library_link | validated | wrap-around behavioural check (`gguf_init_from_file OK; n_tensors=2`) — concept PoV; see `notes.md` |
| llama.cpp | `llama.cpp.TALOS-2024-1913` | library_link | validated | ASAN heap-buffer-overflow in `gguf_fread_str` |
| llama.cpp | `llama.cpp.CVE-2024-42478` | server | invalidated_no_poc | env ready; bench-internal PoC offset didn't match RPC ALLOC_BUFFER reply |
| llama.cpp | `llama.cpp.CVE-2025-52566` | cli_binary | invalidated_no_poc | env ready; PoC needs jinja template producing > INT32_MAX tokens |
| llama.cpp | `llama.cpp.GHSA-8wwf-w4qm-gpqr` | cli_binary | invalidated_no_poc | env ready; advisory describes trigger but ships no exploit |
| ncnn | `ncnn.ISSUE-3503` | cli_binary | validated | ASAN SEGV in `ncnn::Net::load_param` after `find_blob_index_by_name conv1 failed` |
| ncnn | `ncnn.ISSUE-6214-darknet` | library_link | validated | UBSan null-deref `member access within null pointer of type 'Section'` in `load_cfg` |
| onnx | `onnx.CVE-2022-25882` | python_api | validated | `LEAK_DETECTED: /etc/passwd contents read` (onnx 1.12.0) |
| onnx | `onnx.CVE-2024-27318` | python_api | validated | same exploit on onnx 1.15.0 (lstrip-bypass disclosure) |
| opencv | `opencv.CVE-2019-5063` | library_link | validated | ASAN heap-buffer-overflow in `__asan_memcpy` from `createJSONParser` |
| opencv | `opencv.CVE-2019-5064` | library_link | validated | ASAN heap-buffer-overflow in `__asan_memcpy` (XML parseValue / unknown entity) |
| opencv | `opencv.CVE-2023-2617` | library_link | validated | UBSan null reference binding in `wechat_qrcode/zxing/common/array.hpp:41` |
| opencv | `opencv.CVE-2023-2618` | library_link | invalidated_no_poc | env ready; advisory describes wechat_qrcode `decodeHanziSegment` leak class only |
| tensorflow | `tensorflow.ISSUE-115308` | library_link | validated | ASAN heap-buffer-overflow in `flatbuffers::ReadScalar` → `Model::buffers` → `ValidateModelBuffers` → `BuildFromAllocation` |
| whisper.cpp | `whisper.cpp.CVE-2025-14569` | library_link | validated | ASAN bad-free (`free on address which was not malloc()-ed`) in `ma_decoder_init_file` |
| whisper.cpp | `whisper.cpp.GHSA-ggml-2025-parser` | library_link | validated | UBSan `index 5 out of bounds for type 'uint64_t [4]'` in `gguf_init_from_file` |
| whisper.cpp | `whisper.cpp.TALOS-2024-1914` | library_link | validated | ASAN heap-buffer-overflow in `gguf_fread_str` |
| whisper.cpp | `whisper.cpp.TALOS-2024-1914B` | cli_binary | invalidated_no_poc | env ready; whisper_full_parallel refactored, no compatible PoC; needs >30 min audio + specific `-p` |
