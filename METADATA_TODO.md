# Metadata TODO — fix_commit corrections

Generated: 2026-05-03
Tooling: `python3.12 scripts/audit_fix_commits.py`

This file tracks `fix_commit` field issues found while building the runnable
benchmark environment. Categories:

- **WRONG**: yaml has a `fix_commit` URL/SHA, but the SHA either (a) doesn't
  exist in the upstream repo, or (b) exists but doesn't actually fix the
  vulnerability described.
- **EMPTY**: yaml has no `fix_commit` recorded at all.
- **BAD_FORMAT**: yaml has free-text where a SHA/tag belongs.

Until each entry is corrected, the corresponding instance cannot reach
`validation_status = validated` (we can't checkout the right vulnerable
commit). They can still hold env / harness drafts.

## Known WRONG

| project | id | yaml fix_commit | actual fix (verified upstream) | notes |
|---|---|---|---|---|
| llama.cpp | GHSA-vgg9-87g3-85w8 | `b4057` | **`26a48ad69` (PR #14595, 2025-07-09)** | b4057 in yaml resolves to commit `46323fa9` "metal : hide debug messages" — totally unrelated. The real `ctx->size += ggml_nbytes(t)` int-overflow fix was added later when GGUF was refactored into ggml/src/gguf.cpp. Vulnerable commit (parent of fix) = `ffd59e7d18a76459d5c31ba97073c7c9d73cb752`. |
| llama.cpp | GHSA-8wwf-w4qm-gpqr | `b4455` | **`3cfbbdb44`** ("Merge commit from fork — vocab : prevent integer overflow during load", 2025-06-13) | yaml + instance.json now updated. Vulnerable commit = `80709b70a2f87c13ccaf1480b799393109996789`. No public PoC, instance marked `invalidated_no_poc`. |
| opencv | CVE-2019-5063 | `2eb60f1de4b684c42c46e29aee93c0bbc8b3f96a` | _TODO_ | SHA absent from `opencv/opencv` repo; possibly orphaned by force-push or wrong repo (might be `opencv_contrib`?). Need to find real persistence.cpp fix. |
| opencv | CVE-2019-5064 | `2eb60f1de4b684c42c46e29aee93c0bbc8b3f96a` | _TODO_ | Same SHA as above, same problem. |
| whisper.cpp | GHSA-ggml-2025-parser | `Multiple incremental ggml commits` | _TODO_ | Free text instead of SHA. Need to either pick the canonical fix or list a SHA range. |

## EMPTY (no fix_commit)

| project | id | type | priority |
|---|---|---|---|
| llama.cpp | TALOS-2024-1913 | heap-buffer-overflow | first-tier (cli_binary) |
| whisper.cpp | CVE-2025-14569 | use-after-free | first-tier (cli_binary) |
| whisper.cpp | TALOS-2024-1914 | heap-buffer-overflow | first-tier (cli_binary) |
| whisper.cpp | TALOS-2024-1914B | stack-buffer-overflow | first-tier (cli_binary) |
| opencv | CVE-2023-2617 | null-ptr-deref | first-tier (library_link) — fix in opencv_contrib |
| opencv | CVE-2023-2618 | memory-leak | first-tier (library_link) |
| opencv | CVE-2025-53644 | heap-buffer-overflow | first-tier (cli_binary) |
| onnx | ORT-2024-HIDDENLAYER | out-of-bounds-read | first-tier (library_link) |
| onnx | CVE-2024-5187 | arbitrary-file-write | python_api (deferred) |
| pytorch | CVE-2024-48063 | deserialization-rce | python_api (deferred) |
| ollama | CVE-2024-12055 / 2025-15514 / 2025-66959 | various | server (deferred) |

## How to fix one

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
