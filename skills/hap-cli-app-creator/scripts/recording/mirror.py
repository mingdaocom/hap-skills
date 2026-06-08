"""Mirror the run outcome into the per-app folder so each
``apps/<appId>/`` is self-describing (``_last_run.json`` + ``_result.md``).
"""
from __future__ import annotations

import json

from scripts import config
from scripts.executor import RunSummary, StepRecord
from scripts.recording.report import render_markdown


class AppMirrorRecorder:
    """On finish, writes a compact run snapshot next to the captured
    resources. No-op if the app was never created."""

    def __init__(self, *, ts: str = "", design: str = "") -> None:
        self.ts = ts
        self.design = design

    def on_step(self, rec: StepRecord) -> None:
        pass

    def on_finish(self, summary: RunSummary) -> None:
        if not summary.app_id:
            return
        app_dir = config.app_store_dir(summary.app_id)
        if not app_dir.is_dir():
            return
        snapshot = {
            "runId": summary.run_id,
            "ts": self.ts,
            "design": self.design,
            "passed": summary.passed,
            "counts": {"ok": summary.ok, "err": summary.err, "skip": summary.skip},
            "steps": [r.to_json() for r in summary.records],
        }
        (app_dir / "_last_run.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (app_dir / "_result.md").write_text(
            render_markdown(summary, ts=self.ts, design=self.design),
            encoding="utf-8",
        )
