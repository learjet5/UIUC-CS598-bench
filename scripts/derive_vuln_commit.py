#!/usr/bin/env python3.12
"""Derive vulnerable_commit candidates for every vuln yaml.

For each `projects/*/vulns/*.yaml`:

  1. Read `fix_commit`. Accept a full commit URL, a 40-hex SHA, or a short SHA / tag.
  2. If a 40-hex SHA can be extracted directly, the candidate is `<sha>^`. Done.
  3. Otherwise (tag, release ref, short SHA, empty), try to resolve via the local
     clone at <bench_root>/../repos-sanitizer/<project>/. If that clone exists,
     `git rev-parse <ref>^` is used. If the clone is missing or the ref doesn't
     resolve, the entry is reported as TODO — humans must fill it in.
  4. Print a summary table; with --apply, write each candidate back to the yaml
     under `vulnerable_commit:` (only if the field is missing or empty — this script
     never overwrites existing values).

The script does NOT run `git fetch`; it expects the clone to already have the
fix_commit reachable. Run this AFTER scripts/clone_all.sh.

Usage:
    python3.12 scripts/derive_vuln_commit.py            # dry-run, print table
    python3.12 scripts/derive_vuln_commit.py --apply    # write back to yamls
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

BENCH_ROOT = Path(__file__).resolve().parent.parent  # UIUC-CS598-bench/
REPOS_ROOT = BENCH_ROOT.parent / "repos-sanitizer"   # AI4PoV/CS598/repos-sanitizer/

SHA_RE = re.compile(r"\b([0-9a-f]{40})\b", re.IGNORECASE)
# Allow 7..39 too — some yaml entries have truncated SHAs (e.g. CVE-2023-25668 has 39 chars).
SHORT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
# A "looks like a commit-ish" ref: 7+ hex, or "b<digits>" (llama.cpp build tag), or "v<semver>".
REF_RE = re.compile(r"^([0-9a-f]{7,}|b\d{3,}|v\d+(\.\d+)*)$", re.IGNORECASE)


def extract_sha_from_fix_commit(fix_commit: str) -> str | None:
    """Pull a 40-hex SHA out of fix_commit. Returns None if it's a ref/tag/empty."""
    if not fix_commit:
        return None
    m = SHA_RE.search(fix_commit)
    if m:
        return m.group(1)
    return None


def resolve_via_git(project_id: str, ref: str) -> tuple[str | None, str]:
    """Try to resolve `ref^` in the local clone. Returns (sha, note)."""
    repo = REPOS_ROOT / project_id
    if not repo.exists():
        return None, f"clone missing: {repo}"
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", f"{ref}^"],
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        ).strip()
        return out, "resolved-via-clone"
    except subprocess.CalledProcessError as e:
        return None, f"git rev-parse failed: {e.stderr.strip()[:120]}"
    except subprocess.TimeoutExpired:
        return None, "git rev-parse timed out"


def derive(fix_commit: str, project_id: str) -> tuple[str | None, str]:
    """Return (vulnerable_commit_sha, note)."""
    sha = extract_sha_from_fix_commit(fix_commit)
    if sha:
        # Try to verify + get parent via clone (more accurate). Fall back to "<sha>^" string.
        resolved, note = resolve_via_git(project_id, sha)
        if resolved:
            return resolved, note
        return f"{sha}^", note + " (using <sha>^ literal)"

    # Maybe it's a short SHA, a truncated SHA, or a tag like "b4057"/"v0.7.0".
    raw = (fix_commit or "").strip().rstrip("/")
    candidate_ref = raw.split("/")[-1] if "/" in raw else raw
    if not candidate_ref or candidate_ref == "...":
        return None, "fix_commit empty or placeholder"
    if REF_RE.match(candidate_ref):
        return resolve_via_git(project_id, candidate_ref)
    return None, f"unrecognized fix_commit format: {raw[:80]}"


def find_vuln_yamls() -> list[Path]:
    return sorted((BENCH_ROOT / "projects").glob("*/vulns/*.yaml"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Write resolved SHAs back to yamls (only fills empty fields)")
    args = ap.parse_args()

    rows: list[tuple[str, str, str, str, str]] = []
    for ypath in find_vuln_yamls():
        data = yaml.safe_load(ypath.read_text())
        vid = data.get("id", ypath.stem)
        proj = data.get("project", ypath.parent.parent.name)
        fix = (data.get("fix_commit") or "").strip()
        existing = (data.get("vulnerable_commit") or "").strip()
        if existing:
            rows.append((proj, vid, fix[:40], existing, "already set"))
            continue
        sha, note = derive(fix, proj)
        rows.append((proj, vid, fix[:40], sha or "-", note))
        if args.apply and sha:
            # Insert vulnerable_commit immediately after fix_commit if possible; else append.
            text = ypath.read_text()
            new_line = f'vulnerable_commit: "{sha}"\n'
            if "vulnerable_commit:" in text:
                text = re.sub(r'^vulnerable_commit:.*$', new_line.rstrip(),
                              text, count=1, flags=re.MULTILINE)
            else:
                text = re.sub(
                    r'^(fix_commit:.*\n)',
                    r'\1' + new_line,
                    text, count=1, flags=re.MULTILINE,
                )
            ypath.write_text(text)

    # Print table
    w_proj = max(len(r[0]) for r in rows)
    w_id = max(len(r[1]) for r in rows)
    print(f"{'project':<{w_proj}}  {'id':<{w_id}}  fix_commit (head)  vulnerable_commit  note")
    print("-" * 110)
    for proj, vid, fix, vc, note in rows:
        print(f"{proj:<{w_proj}}  {vid:<{w_id}}  {fix[:18]:<18}  {vc[:40]:<40}  {note}")

    n_resolved = sum(1 for r in rows if r[3] not in ("-",))
    print(f"\nResolved {n_resolved}/{len(rows)} vulnerable_commits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
