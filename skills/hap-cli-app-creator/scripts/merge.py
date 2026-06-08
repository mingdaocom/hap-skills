"""Merge several partial design docs into one — no API calls, no login.

    python -m scripts merge <part1.json> <part2.json> ... --out <design.json>

For the split-generation workflow: author a foundation part (app + optionsets
+ worksheets) plus independent parts (views, roles, workflows + custom_actions,
pages…) — often in parallel — then merge them here into a single design that
``build`` consumes. ``build``/``validate`` already accept multiple parts
directly; this command is for when you want the combined file written to disk
(to inspect, diff, or keep alongside the parts).

The merged document is validated as a WHOLE before writing, so cross-part
logical-name references are checked. Exit 0 = written, 2 = error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts import schema
from scripts.errors import DesignError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scripts merge")
    p.add_argument("parts", nargs="+", help="design part files to merge")
    p.add_argument("--out", required=True, help="path to write the merged design")
    args = p.parse_args(argv)

    paths = [Path(a) for a in args.parts]
    try:
        # load_designs merges AND validates the combined document.
        merged = schema.load_designs(paths)
    except DesignError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    label = " + ".join(p.name for p in paths)
    print(f"✓ merged {len(paths)} parts ({label}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
