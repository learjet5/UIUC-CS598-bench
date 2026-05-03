#!/usr/bin/env python3.12
"""Validate every instances/*/instance.json against schema/instance.schema.json.

Exit non-zero if any file fails validation. Useful as a pre-commit check.

Usage:
    python3.12 scripts/validate_instance_schema.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    sys.exit("jsonschema not installed; run: python3.12 -m pip install --user jsonschema")

BENCH = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((BENCH / "schema" / "instance.schema.json").read_text())


def main() -> int:
    instances = sorted((BENCH / "instances").glob("*/instance.json"))
    if not instances:
        print("no instances/*/instance.json found", file=sys.stderr)
        return 0

    n_ok = n_bad = 0
    for ipath in instances:
        try:
            inst = json.loads(ipath.read_text())
        except json.JSONDecodeError as e:
            print(f"FAIL  {ipath.parent.name}: invalid JSON — {e}")
            n_bad += 1
            continue
        try:
            jsonschema.validate(inst, SCHEMA)
            print(f"OK    {ipath.parent.name}")
            n_ok += 1
        except jsonschema.ValidationError as e:
            print(f"FAIL  {ipath.parent.name}: {e.message} (path: {list(e.absolute_path)})")
            n_bad += 1

    print(f"\n{n_ok} ok, {n_bad} bad")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
