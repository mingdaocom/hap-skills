"""Validate a design document against the schema + verify its icons.

    python -m scripts validate <design.json> [more.json ...]

One file validates that file. Multiple files are MERGED (the split-generation
workflow: foundation + independently-authored parts) and the combined document
is validated as a whole — so cross-part logical-name references are checked.

Two layers run here:
  1. structural + reference validation — pure, offline (``schema.load_designs``).
  2. icon validation — every ``icon`` field (app / worksheet / page / page
     component / button) must be an EXACT, real catalogue icon. We confirm
     each via ``hap icon search <icon> --limit 1`` and require the top hit's
     ``fileName`` to equal the icon byte-for-byte. ``hap icon search`` is a
     LOCAL lookup (no network, no login) — but it does shell out to the
     installed ``hap`` binary, so this layer needs HAP_BIN / a ``hap`` on PATH.
     A fabricated icon (``sys_15_3_user``) or a non-canonical short form
     (``1_2_order`` instead of ``sys_1_2_order``) is rejected — the backend
     only accepts exact catalogue fileNames.

Exit code 0 = valid, 2 = validation errors (printed with their JSON paths).
Run this after authoring a design and before ``build`` so structural and icon
problems are caught locally instead of mid-build.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from scripts import hap, schema
from scripts.errors import DesignError, HapCommandError


def _collect_icons(doc: Any) -> list[tuple[str, str]]:
    """Walk a (merged) design doc and return ``(json_path, icon)`` for every
    ``icon`` string field, wherever it appears — app, worksheets, custom_pages,
    page components, button ``buttons[]``, etc. Keyed strictly on ``"icon"`` so
    ``icon_color`` (a hex color, not a catalogue ref) is never picked up."""
    found: list[tuple[str, str]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                child = f"{path}.{k}" if path else k
                if k == "icon" and isinstance(v, str):
                    found.append((child, v))
                else:
                    walk(v, child)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(doc, "")
    return found


def _icon_is_real(icon: str, runner: Callable[..., Any] = hap.run) -> bool:
    """True iff ``icon`` is a real catalogue icon by EXACT fileName match.

    ``hap icon search <icon> --limit 1`` returns the single best hit. A real
    icon comes back with its exact ``fileName`` and no ``suggested`` flag; a
    fabricated icon yields a random ``suggested: true`` placeholder, and a
    short form (``1_2_order``) resolves to a different canonical fileName
    (``sys_1_2_order``) — both fail the byte-for-byte equality below.
    """
    res = runner(["icon", "search", icon, "--limit", "1"])
    rows = res.data if isinstance(res.data, list) else []
    if not rows:
        return False
    top = rows[0]
    return top.get("fileName") == icon and not top.get("suggested")


def _check_icons(doc: Any, runner: Callable[..., Any] = hap.run) -> list[str]:
    """Return a list of icon-validation errors (empty = every icon is real).

    Distinct icon values are looked up once and cached, so a design that reuses
    one icon across many fields costs a single ``hap icon search`` call."""
    errors: list[str] = []
    cache: dict[str, bool] = {}
    for path, icon in _collect_icons(doc):
        ok = cache.get(icon)
        if ok is None:
            ok = _icon_is_real(icon, runner)
            cache[icon] = ok
        if not ok:
            errors.append(
                f"{path}: icon {icon!r} is not a real catalogue icon — find a "
                f"valid one with `hap icon search <keywords>` and use its exact "
                f"fileName (e.g. `sys_1_2_order`, not `1_2_order`)")
    return errors


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m scripts validate <design.json> [more.json ...]",
              file=sys.stderr)
        return 2
    paths = [Path(a) for a in argv]
    try:
        doc = schema.load_designs(paths)
    except DesignError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    # Icon layer: needs the hap binary (local lookup, no login). A missing
    # binary is an environment problem, not a clean design — fail, don't pass.
    try:
        icon_errors = _check_icons(doc)
    except HapCommandError as e:
        print(f"✗ cannot verify icons: {e}", file=sys.stderr)
        return 2
    if icon_errors:
        joined = "\n  - ".join(icon_errors)
        print(f"✗ design failed icon validation:\n  - {joined}", file=sys.stderr)
        return 2

    label = " + ".join(p.name for p in paths)
    if len(paths) == 1:
        print(f"✓ {label} is valid against the design schema (icons verified)")
    else:
        print(f"✓ {len(paths)} parts merge + validate cleanly: {label} "
              f"(icons verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
