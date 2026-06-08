"""Live console output + a final phase-grouped summary table."""
from __future__ import annotations

import sys
from collections import OrderedDict

from scripts.executor import STATUS_ERR, STATUS_OK, STATUS_SKIP, RunSummary, StepRecord

_MARK = {STATUS_OK: "✓", STATUS_ERR: "✗", STATUS_SKIP: "–"}


class ConsoleRecorder:
    """Prints one line per step as it runs, then a grouped table."""

    def __init__(self, stream=None) -> None:
        self.stream = stream or sys.stdout

    def _w(self, text: str = "") -> None:
        print(text, file=self.stream)

    def on_step(self, rec: StepRecord) -> None:
        mark = _MARK.get(rec.status, "?")
        line = f"  {mark} [{rec.phase}] {rec.name}"
        if rec.created_id:
            line += f"  id={rec.created_id}"
        if rec.duration_ms:
            line += f"  {rec.duration_ms}ms"
        self._w(line)
        if rec.summary and rec.status == STATUS_OK:
            self._w(f"      {rec.summary}")
        if rec.error:
            self._w(f"      ! {rec.error}")
            if rec.command:
                self._w(f"      $ {rec.command}")

    def on_finish(self, summary: RunSummary) -> None:
        self._w("")
        self._w("─" * 60)
        # group by phase preserving first-seen order
        groups: "OrderedDict[str, list[StepRecord]]" = OrderedDict()
        for rec in summary.records:
            groups.setdefault(rec.phase, []).append(rec)
        for phase, recs in groups.items():
            ok = sum(1 for r in recs if r.status == STATUS_OK)
            err = sum(1 for r in recs if r.status == STATUS_ERR)
            skip = sum(1 for r in recs if r.status == STATUS_SKIP)
            tail = f"{ok} ok"
            if err:
                tail += f", {err} err"
            if skip:
                tail += f", {skip} skip"
            self._w(f"  {phase:<18} {tail}")
        self._w("─" * 60)
        verdict = "PASS" if summary.passed else "FAIL"
        self._w(
            f"  {verdict}  ok={summary.ok} err={summary.err} skip={summary.skip}"
        )
        if summary.app_id:
            self._w(f"  app: {summary.app_name}  ({summary.app_id})")
