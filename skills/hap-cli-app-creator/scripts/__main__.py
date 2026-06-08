"""``python -m scripts <build|validate|merge|cleanup|seed-template|seed> ...`` dispatch.

``build`` is the primary entry point: it takes an ID-free design document
and creates the whole app end-to-end via the real ``hap`` binary, capturing
every returned id under the working-directory store. ``smoke`` is kept as an
alias of ``build`` for parity with the underlying framework.
"""
from __future__ import annotations

import sys

_USAGE = (
    "usage: python -m scripts <command> [args]\n"
    "  build         <design.json> [more.json ...]  create a whole app end-to-end (multiple parts are merged)\n"
    "  validate      <design.json> [more.json ...]  validate a design (parts merged) — no API calls\n"
    "  merge         <part.json ...> --out <design.json>  merge design parts into one file (no API calls)\n"
    "  cleanup       <appId> [--purge] [--yes]  delete an app and archive its store\n"
    "  seed-template <appId>                    emit the fill template for an app\n"
    "  seed          <appId> [data.json]        push AI-authored test data into an app\n"
)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0 if argv else 1
    cmd, rest = argv[0], argv[1:]
    if cmd in ("build", "smoke"):
        from scripts.smoke import main as run
    elif cmd == "validate":
        from scripts.validate import main as run
    elif cmd == "merge":
        from scripts.merge import main as run
    elif cmd == "cleanup":
        from scripts.cleanup import main as run
    elif cmd == "seed-template":
        from scripts.seed.cli import template_main as run
    elif cmd == "seed":
        from scripts.seed.cli import seed_main as run
    else:
        print(f"unknown command {cmd!r}\n\n{_USAGE}", file=sys.stderr)
        return 1
    return run(rest)


if __name__ == "__main__":
    raise SystemExit(main())
