"""Delete a smoke-created app; keep its design source files by default.

    python -m scripts.cleanup <appId> [--destroy] [--yes]

Reads ``apps/<appName-ts>/app.json`` for the appId + org, deletes the app via
``hap app delete``, then:

  * default (no ``--destroy``): deletes the SERVER app and archives only the
    generated **store artifacts** (worksheet/role/workflow/page json, run
    reports, _last_run …) to ``apps/_deleted/<name>/`` — the **design source
    files stay in place** (``*.design.json`` / ``overview.md`` / the
    ``validation-result.txt`` / ``build-result.txt`` / ``build-output*.log``
    records / ``SPEC.md``), so the folder can be re-built later.
  * ``--destroy``: removes the entire folder, design included.

Never invoked automatically — smoke runs KEEP their app.
"""
from __future__ import annotations

import argparse
import shutil
import sys

from scripts import config, hap
from scripts.errors import HapCommandError
from scripts.store import Store


def _is_design_source(fname: str) -> bool:
    """Design/record files that survive a default (non-destroy) cleanup."""
    return (
        fname.endswith(".design.json")
        or fname.startswith("build-output")
        or fname in {"overview.md", "validation-result.txt",
                     "build-result.txt", "SPEC.md"}
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scripts.cleanup")
    p.add_argument("app_id")
    p.add_argument("--destroy", action="store_true",
                   help="also delete the design source files (full removal); "
                        "default keeps them and archives only store artifacts")
    # Back-compat alias: --purge used to mean "rmtree the whole folder".
    p.add_argument("--purge", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")
    args = p.parse_args(argv)
    destroy = args.destroy or args.purge

    store = Store.for_app(args.app_id)
    if not store.exists():
        print(f"✗ no captured app at {store.dir}", file=sys.stderr)
        return 2
    meta = store.app_meta()
    app_id = meta["id"]
    org_id = meta.get("org_id", "")
    name = meta.get("name", "")

    if not args.yes:
        what = "app + design folder" if destroy else "app (keep design)"
        ans = input(f"Delete {what} {name!r} ({app_id}) on org {org_id}? [y/N] ")
        if ans.strip().lower() not in ("y", "yes"):
            print("aborted.")
            return 0

    argv_del = ["app", "delete", app_id, "--yes"]
    if org_id:
        argv_del += ["--org-id", org_id]
    try:
        hap.run(argv_del)
        print(f"✓ deleted app {app_id}")
    except HapCommandError as e:
        print(f"✗ delete failed: {e}", file=sys.stderr)
        return 1

    if destroy:
        shutil.rmtree(store.dir, ignore_errors=True)
        print(f"✓ destroyed {store.dir} (design included)")
    else:
        # Archive only the generated store artifacts to ``.../apps/_deleted/``;
        # leave the design source files in place so the folder can be re-built.
        deleted_dir = store.dir.parent / "_deleted" / store.dir.name
        deleted_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        for entry in list(store.dir.iterdir()):
            if entry.is_file() and _is_design_source(entry.name):
                continue
            dest = deleted_dir / entry.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest, ignore_errors=True)
                else:
                    dest.unlink()
            shutil.move(str(entry), str(dest))
            moved += 1
        print(f"✓ kept design source in {store.dir}; "
              f"archived {moved} store artifact(s) to {deleted_dir}")
    config.deregister_app_store(app_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
