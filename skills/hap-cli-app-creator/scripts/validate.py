"""Validate a design document against the schema — no API calls, no login.

    python -m scripts validate <design.json> [more.json ...]

One file validates that file. Multiple files are MERGED (the split-generation
workflow: foundation + independently-authored parts) and the combined document
is validated as a whole — so cross-part logical-name references are checked.

Exit code 0 = valid, 2 = validation errors (printed with their JSON paths).
Run this after authoring a design and before ``build`` so structural
problems are caught locally instead of mid-build.
"""
from __future__ import annotations

import sys
from pathlib import Path

from scripts import schema
from scripts.errors import DesignError


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m scripts validate <design.json> [more.json ...]",
              file=sys.stderr)
        return 2
    paths = [Path(a) for a in argv]
    try:
        schema.load_designs(paths)
    except DesignError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    label = " + ".join(p.name for p in paths)
    if len(paths) == 1:
        print(f"✓ {label} is valid against the design schema")
    else:
        print(f"✓ {len(paths)} parts merge + validate cleanly: {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
