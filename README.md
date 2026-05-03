# UIUC-CS598-bench

A vulnerability benchmark for **C/C++ memory-safety bugs in the AI software
ecosystem**, built as the course project for UIUC CS598.

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

## Current contents (2026-05-03)

**7 projects · 35 vulnerabilities** across 12 distinct bug classes.

| project | vulns | category |
|---|---|---|
| TensorFlow | 8 | Training framework (Python API → C++ kernels) |
| llama.cpp | 5 | LLM inference engine |
| ollama | 5 | LLM inference server |
| OpenCV | 5 | Computer vision library |
| ONNX / ONNX Runtime | 4 | Model format & inference framework |
| PyTorch | 4 | Training framework |
| whisper.cpp | 4 | Speech recognition engine |

Severity distribution: 3 CRITICAL, 25 HIGH, 7 MEDIUM. PoC coverage:
30 of 35 cases have a public PoC (18 inline, 12 by external link); see
[`POC_COVERAGE.md`](POC_COVERAGE.md) for the breakdown.

By trigger pattern (`triggerable_class`): 14 `python_api`, 10 `cli_binary`,
7 `server`, 4 `library_link`.

## Repository layout

```
UIUC-CS598-bench/
├── index.yaml              # master index — one row per (project, vuln)
├── POC_COVERAGE.md         # PoC coverage summary
├── METADATA_TODO.md        # known fix_commit metadata gaps
├── validation_report.md    # auto-generated per-instance validation log
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
  `invalidated_no_poc`, `invalidated_poc_failed`, `pending`.

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
   `expected_fingerprint`, writes back `validation_status`, and appends a row
   to `validation_report.md`.

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
  `projects/<project>/vulns/`. Includes the recently added
  build/trigger/validation fields (`triggerable_class`,
  `build_sh_sanitizer`, `build_sh_cov`, `harness_command`,
  `expected_fingerprint`, `vuln_location`, `validation_status`, etc.).
- `schema/instance.schema.json` — JSON Schema (draft 2020-12) enforcing the
  shape of every `instance.json`. Used by
  `scripts/validate_instance_schema.py`.

## Status

The benchmark is under active construction. As of 2026-05-03:

- 35 vulnerabilities catalogued (editorial layer complete).
- 14 first-tier instances scaffolded (`cli_binary` + `library_link`); 1
  fully `validated`, 1 `invalidated_no_poc`, 12 `pending`.
- The remaining 21 cases (`python_api`, `server`) are scheduled for
  subsequent rounds and require the heavier projects (TensorFlow, PyTorch,
  ONNX Runtime, ollama) to be cloned and instrumented.
- Known editorial gaps in `fix_commit` metadata are tracked in
  [`METADATA_TODO.md`](METADATA_TODO.md).
