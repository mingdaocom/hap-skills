"""Entry points for ``python -m scripts seed-template`` and ``seed``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.errors import HapCommandError, NotLoggedInError
from scripts.store import Store
from scripts.seed.template import build_fill_template
from scripts.seed.executor import seed_app

_INSTRUCTIONS = Path(__file__).with_name("INSTRUCTIONS.md")


def template_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scripts seed-template")
    p.add_argument("app_id")
    p.add_argument(
        "--out",
        help="output path (default: the app's project folder, "
             "{PROJECT_ROOT}/apps/{appName}-{ts}/_seed_template.json)")
    args = p.parse_args(argv)

    store = Store.for_app(args.app_id)
    if not store.exists():
        print(f"✗ no captured app at {store.dir}", file=sys.stderr)
        return 2

    templates = build_fill_template(store)
    out_path = Path(args.out) if args.out else store.dir / "_seed_template.json"
    out_path.write_text(
        json.dumps(templates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"📋 fill template for {len(templates)} worksheet(s) -> {out_path}")
    for t in templates:
        deps = f"  deps: {', '.join(t['relationDeps'])}" if t["relationDeps"] else ""
        print(f"  • {t['worksheetName']}: {t['fieldCount']} fillable field(s){deps}")
    print(f"\nNext: author {store.dir / '_seed_data.json'} following")
    print(f"      {_INSTRUCTIONS}")
    print(f"Then: python -m scripts seed {args.app_id}")
    return 0


def seed_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scripts seed")
    p.add_argument("app_id")
    p.add_argument("data_file", nargs="?",
                   help="seed data JSON (default: the app's project folder, "
                        "{PROJECT_ROOT}/apps/{appName}-{ts}/_seed_data.json)")
    p.add_argument("--trigger-workflow", action="store_true",
                   help="fire workflows on each created record (default off)")
    args = p.parse_args(argv)

    store = Store.for_app(args.app_id)
    if not store.exists():
        print(f"✗ no captured app at {store.dir}", file=sys.stderr)
        return 2

    data_path = Path(args.data_file) if args.data_file else store.dir / "_seed_data.json"
    if not data_path.is_file():
        print(f"✗ no seed data file at {data_path}", file=sys.stderr)
        return 2
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("✗ seed data must be a {worksheetName: [rows]} object", file=sys.stderr)
        return 2

    try:
        result = seed_app(store, data, trigger_workflow=args.trigger_workflow)
    except NotLoggedInError:
        print("✗ not logged in — run `hap auth login` first", file=sys.stderr)
        return 3
    except (HapCommandError, Exception) as e:  # surface but don't traceback
        print(f"✗ seed failed: {e}", file=sys.stderr)
        return 1

    print(f"✓ seeded {result['total']} record(s) across {len(result['tables'])} table(s)")
    for t in result["tables"]:
        flag = "" if t["created"] == t["requested"] else "  ⚠ partial"
        print(f"  • {t['name']}: {t['created']}/{t['requested']}{flag}")
    print(f"  rowIds -> {store.dir / '_seed_rows.json'}")
    return 0
