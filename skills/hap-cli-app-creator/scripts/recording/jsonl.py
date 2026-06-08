"""JSONL step log + run header under ``runs/<runId>/``."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.executor import RunSummary, StepRecord


class JsonlRecorder:
    """Appends one JSON object per step to ``steps.jsonl`` and writes a
    ``run.json`` header on finish."""

    def __init__(self, run_dir: Path, *, design_path: str = "", ts: str = "") -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.steps_path = self.run_dir / "steps.jsonl"
        self.design_path = design_path
        self.ts = ts
        # Truncate any prior content for this run dir.
        self.steps_path.write_text("", encoding="utf-8")

    def on_step(self, rec: StepRecord) -> None:
        with self.steps_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec.to_json(), ensure_ascii=False) + "\n")

    def on_finish(self, summary: RunSummary) -> None:
        header = {
            "runId": summary.run_id,
            "ts": self.ts,
            "design": self.design_path,
            "appId": summary.app_id,
            "appName": summary.app_name,
            "orgId": summary.org_id,
            "counts": {"ok": summary.ok, "err": summary.err, "skip": summary.skip},
            "passed": summary.passed,
        }
        (self.run_dir / "run.json").write_text(
            json.dumps(header, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
