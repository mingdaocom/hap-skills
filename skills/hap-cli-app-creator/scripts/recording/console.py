"""Live console output + a final phase-grouped summary table.

Each step is reported twice for live feedback: a ``▶`` "in progress" line
the moment it starts (so a slow step — custom page, workflow publish — isn't
a silent multi-second wait), then a ``✓``/``✗``/``–`` result line when it
finishes. Every write is flushed immediately so progress streams out even
when stdout is a pipe (a parent process / agent polling the build), instead
of being block-buffered until the run ends. On an interactive terminal the
result line overwrites the in-progress line in place, keeping one line per
step; when piped, both lines are emitted so the log reads cleanly.
"""
from __future__ import annotations

import sys
from collections import OrderedDict

from scripts.executor import STATUS_ERR, STATUS_OK, STATUS_SKIP, RunSummary, StepRecord
from scripts.steps import Step

_MARK = {STATUS_OK: "✓", STATUS_ERR: "✗", STATUS_SKIP: "–"}


class ConsoleRecorder:
    """Prints a start + result line per step (flushed), then a grouped table."""

    def __init__(self, stream=None) -> None:
        self.stream = stream or sys.stdout
        try:
            self._tty = bool(self.stream.isatty())
        except Exception:
            self._tty = False
        self._pending = False  # a TTY in-progress line awaits its result

    def _flush(self) -> None:
        try:
            self.stream.flush()
        except Exception:
            pass

    def _w(self, text: str = "") -> None:
        print(text, file=self.stream)
        self._flush()

    def on_start(self, step: Step) -> None:
        line = f"  ▶ [{step.phase}] {step.name}"
        if self._tty:
            # No newline: the result line overwrites this in place.
            self.stream.write(line + "\r")
            self._flush()
            self._pending = True
        else:
            self._w(line)

    def on_step(self, rec: StepRecord) -> None:
        if self._pending:
            self.stream.write("\r\033[K")  # erase the in-progress line
            self._pending = False
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
