# `instances/` — per-vuln self-contained directories

One subdirectory per vulnerability case, named `<project_name>.<vuln_id>` (e.g.
`opencv.CVE-2023-2617`). Each subdirectory is meant to be **self-contained
enough that a benchmark loader can consume it without re-reading the original
`projects/<project>/vulns/<id>.yaml`** — though the yaml remains the editorial
source of truth for the human-readable description, references, and metadata.

## Layout

```
instances/<project>.<vuln_id>/
├── instance.json        # required, conforms to schema/instance.schema.json
├── repro/               # ground-truth PoC inputs (only when poc_available=true)
│   ├── SOURCE.md        # provenance: URL, fetch date, hash, license, edits
│   ├── poc_advisory.py  # naming convention: poc_<source>[_<hash8>].<ext>
│   ├── crash.wav        # binary blobs land here too
│   └── ...
├── patch.diff           # optional: extracted from fix_commit, for fix-then-rerun reverse-validation
└── notes.md             # optional: case-specific gotchas (deps, GPU, large files, etc.)
```

## Repository paths (NOT in instance.json)

By convention every loader resolves:

- **sanitizer build** at `<bench_root>/../repos-sanitizer/<project_name>/`
- **coverage build** at `<bench_root>/../repos-llvm-cov/<project_name>/`

These paths are intentionally *not* recorded in `instance.json` so the bench
can be relocated without touching every instance file. Loaders should accept a
single `--bench-root` argument and derive both paths from it.

## `repro/SOURCE.md` template

Every PoC artifact must be traceable. Use this template:

```markdown
# PoC source provenance for instance <project>.<vuln_id>

| file | source URL | fetched | sha256 (full) | license | modifications |
|------|-----------|---------|---------------|---------|---------------|
| poc_advisory.py | https://github.com/.../security/advisories/GHSA-... | 2026-05-03 | abc123... | (advisory body, no license stated; treated as fair-use exhibit) | none |
```

If a PoC was minimised or adapted (e.g. shortened from a fuzzer corpus, edited
to remove placeholders), set `modifications` to a brief description.

## Status

The `validation_status` in `instance.json` is the ground-truth label *for this
bench*. It can be one of:

| value | meaning |
|---|---|
| `validated` | env builds + curated PoC triggers + sanitizer trace matches `expected_fingerprint` |
| `invalidated_no_poc` | env builds, but no public PoC was found; case left in bench for completeness |
| `invalidated_poc_failed` | env builds and a PoC was tried but it didn't trigger / triggered something else |
| `pending` | not yet attempted |

Update via `scripts/validate_instance.sh` (writes `instance.json::validation_status`
+ appends a row to `validation_report.md`).
