# Notes — llama.cpp.TALOS-2024-1913

## Status

- triggerable_class: cli_binary
- PoC: MISSING (no PoC public)
- vulnerable_commit: TODO

## What this stub needs to become validated

1. Verify or fix the `fix_commit` field in the yaml (run `scripts/audit_fix_commits.py`).
2. Set `base_commit` in `instance.json` (run `scripts/derive_vuln_commit.py --apply`).
3. Customize `build_sh_sanitizer` / `build_target` / `harness_command` for this case.
4. Drop a working PoC into `repro/` and update `repro/SOURCE.md`.
5. Run `bash scripts/validate_instance.sh llama.cpp.TALOS-2024-1913` until it returns `validated`.
