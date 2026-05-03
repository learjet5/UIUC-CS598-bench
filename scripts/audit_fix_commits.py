#!/usr/bin/env python3.12
"""Audit every yaml's fix_commit against the local clone.

For each projects/<proj>/vulns/<id>.yaml:
  - Pull the SHA / ref out of fix_commit.
  - If a clone exists at <bench_root>/../repos-sanitizer/<proj>/, verify with
    `git cat-file -t` that the ref is a real commit in that clone.
  - Report per-case: OK / BAD / NO_CLONE / EMPTY.

Bench reality check: opencv CVE-2019-5063 / CVE-2019-5064 reference a
fix_commit SHA that does NOT exist in opencv/opencv. llama.cpp b4057 is a
metal-debug-message commit, not the int-overflow fix. Run this script after
each metadata edit to catch such drift early.

Usage:
    python3.12 scripts/audit_fix_commits.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

BENCH = Path(__file__).resolve().parent.parent
REPOS = BENCH.parent / "repos-sanitizer"

SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b", re.IGNORECASE)


def extract_ref(fix_commit: str) -> str | None:
    if not fix_commit or not fix_commit.strip():
        return None
    fc = fix_commit.strip().rstrip("/")
    # If URL, take the last path component (commit/<ref> or releases/tag/<ref>).
    if "/" in fc:
        last = fc.split("/")[-1]
        # Skip obvious placeholders
        if last in ("...", ""):
            return None
        return last
    return fc


def cat_file_type(repo: Path, ref: str) -> tuple[bool, str]:
    """Returns (exists_as_commit, info)."""
    p = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-t", ref],
        capture_output=True, text=True, timeout=15,
    )
    if p.returncode != 0:
        return False, p.stderr.strip().splitlines()[0][:120]
    kind = p.stdout.strip()
    if kind != "commit":
        return False, f"ref resolves to {kind!r}, not commit"
    return True, "commit"


def main() -> int:
    counts: dict[str, int] = defaultdict(int)
    rows = []
    for ypath in sorted(BENCH.glob("projects/*/vulns/*.yaml")):
        d = yaml.safe_load(ypath.read_text())
        vid = d.get("id")
        proj = d.get("project")
        fix = (d.get("fix_commit") or "").strip()

        ref = extract_ref(fix)
        if not ref:
            counts["EMPTY"] += 1
            rows.append((proj, vid, "EMPTY", "fix_commit empty/placeholder", fix[:60]))
            continue

        repo = REPOS / proj
        if not repo.exists():
            counts["NO_CLONE"] += 1
            rows.append((proj, vid, "NO_CLONE", f"clone missing: {repo.name}", fix[:60]))
            continue

        ok, info = cat_file_type(repo, ref)
        if ok:
            counts["OK"] += 1
            rows.append((proj, vid, "OK", info, fix[:60]))
        else:
            counts["BAD"] += 1
            rows.append((proj, vid, "BAD", info, fix[:60]))

    # Print
    w_p = max(len(r[0]) for r in rows)
    w_i = max(len(r[1]) for r in rows)
    print(f"{'project':<{w_p}}  {'id':<{w_i}}  status     note")
    print("-" * 110)
    for proj, vid, status, info, fix in rows:
        print(f"{proj:<{w_p}}  {vid:<{w_i}}  {status:<8}   {info}")
    print()
    print("Summary:", dict(counts))
    print("\nBAD entries need yaml metadata fix (find correct fix_commit upstream).")
    print("EMPTY entries have no fix_commit recorded — populate from advisory.")
    return 0 if counts.get("BAD", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
