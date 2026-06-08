"""Full smoke run: build a brand-new app from a design document.

    python -m scripts.smoke [design.json]

Defaults to ``examples/minimal.design.json``. Creates the app
and all its resources end-to-end via the real ``hap`` binary, captures
every id/config under ``apps/<appId>/``, and writes a console summary +
``runs/<runId>/`` (steps.jsonl, run.json, report.md/html). The created
app is KEPT — clean it up with ``python -m scripts.cleanup <appId>``.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from scripts import compiler, config, hap, schema
from scripts.errors import DesignError, NotLoggedInError
from scripts.executor import Executor
from scripts.recording.console import ConsoleRecorder
from scripts.recording.jsonl import JsonlRecorder
from scripts.recording.mirror import AppMirrorRecorder
from scripts.recording.report import ReportRecorder


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scripts.smoke")
    # One OR MORE design files. Multiple files are merged (split-generation
    # workflow: foundation + independently-authored parts) before building.
    # A build is always a full, single end-to-end run from a clean design:
    # there is deliberately no phase-window / resume option. A mid-run failure
    # is recorded and the run continues to the end; broken elements are fixed
    # in place afterwards with the hap-cli-app-editor skill, never by re-running a
    # build phase (which would pile up duplicate views / workflows).
    p.add_argument("design", nargs="*",
                   help="design doc(s); multiple are merged into one before build")
    args = p.parse_args(argv)
    design_args = args.design or [str(config.SKILL_DIR / "examples" / "minimal.design.json")]
    design_paths = [Path(d).resolve() for d in design_args]
    # The first file's folder is the project app folder; all parts should live
    # there. Output (store/runs/report/mirror) lands beside it, not in home.
    design_path = design_paths[0]

    if "HAP_APP_CREATOR_WORKDIR" not in os.environ:
        config.set_output_root(design_path.parent)

    try:
        design = schema.load_designs(design_paths)
    except DesignError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    try:
        who = hap.whoami()
    except NotLoggedInError as e:
        print(f"✗ {e}\n  Run 'hap auth login' first.", file=sys.stderr)
        return 3
    org_id = who.get("current_org_id", "")
    account_id = who.get("id", "")
    if not org_id:
        print("✗ no current organization — run 'hap auth switch-org'", file=sys.stderr)
        return 3

    ts = time.strftime("%Y%m%d-%H%M%S")
    run_id = f"smoke-{ts}"
    run_dir = config.runs_dir() / run_id

    steps = compiler.compile_design(design)
    design_label = " + ".join(p.name for p in design_paths)
    print(f"▶ smoke: {design_label} — {len(steps)} steps, org={org_id}, run={run_id}\n")

    recorders = [
        ConsoleRecorder(),
        JsonlRecorder(run_dir, design_path=design_label, ts=ts),
        ReportRecorder(run_dir, ts=ts, design=design_label),
        AppMirrorRecorder(ts=ts, design=design_label),
    ]
    ex = Executor(
        design, run_id=run_id, org_id=org_id, account_id=account_id,
        ts=ts, recorders=recorders,
    )
    summary = ex.run(steps)

    print(f"\n  report: {run_dir / 'report.html'}")
    if summary.app_id:
        print(f"  store:  {config.app_store_dir(summary.app_id)}")
        print(f"  cleanup: python -m scripts.cleanup {summary.app_id}")
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
