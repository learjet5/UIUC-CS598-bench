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
    """Resolve `ref^` to a real commit in the local clone, with strict validation.

    Order of operations:
      1. `git cat-file -t <ref>` — bail if ref isn't an object known to the clone.
      2. `git rev-parse <ref>^{commit}^` — get the parent commit unambiguously
         (the {commit} disambiguator avoids `2eb60f1...^` being read as a path).
      3. Verify the resolved SHA is also a real commit object (defensive).
    """
    repo = REPOS_ROOT / project_id
    if not repo.exists():
        return None, f"clone missing: {repo}"

    def git(*args: str) -> tuple[int, str, str]:
        p = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=15,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()

    rc, _, err = git("cat-file", "-t", ref)
    if rc != 0:
        return None, f"ref not in clone: {err.splitlines()[0][:120]}"

    rc, sha, err = git("rev-parse", f"{ref}^{{commit}}^")
    if rc != 0:
        return None, f"git rev-parse {ref}^ failed: {err.splitlines()[0][:120]}"

    rc, kind, err = git("cat-file", "-t", sha)
    if rc != 0 or kind != "commit":
        return None, f"parent {sha} is not a commit: {err.splitlines()[0][:120]}"

    return sha, "resolved-via-clone"


def derive(fix_commit: str, project_id: str) -> tuple[str | None, str]:
    """Return (vulnerable_commit_sha, note)."""
    sha = extract_sha_from_fix_commit(fix_commit)
    if sha:
        # Validate via clone. Do NOT silently fall back to '<sha>^' — if the
        # clone says the SHA isn't real, the SHA is wrong and a human needs to
        # look at it (yaml metadata bug). Returning the literal would just kick
        # the can down the road.
        return resolve_via_git(project_id, sha)

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
