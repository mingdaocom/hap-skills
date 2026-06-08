"""Drive an ordered list of Steps: resolve, run, capture, record.

The executor owns the run loop. For each step it invokes the registered
handler, measures wall time, and emits a :class:`StepRecord` to every
attached recorder (console / JSONL / report). Failures are recorded and
the run continues so the report shows everything that broke — except an
unauthenticated session or a failed ``app`` step, which abort the run
(nothing downstream can succeed).
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field as dc_field
from typing import Any, Optional, Protocol

from scripts import steps as S
from scripts.errors import NotLoggedInError
from scripts.steps import ExecCtx, Step

STATUS_OK = "ok"
STATUS_ERR = "err"
STATUS_SKIP = "skip"


@dataclass
class StepRecord:
    step_id: str
    kind: str
    name: str
    phase: str
    status: str
    created_id: Optional[str] = None
    summary: str = ""
    command: str = ""
    commands: list[list[str]] = dc_field(default_factory=list)
    resolved_refs: dict[str, Any] = dc_field(default_factory=dict)
    capture_files: list[str] = dc_field(default_factory=list)
    duration_ms: int = 0
    error: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunSummary:
    run_id: str
    app_id: Optional[str] = None
    app_name: str = ""
    org_id: str = ""
    ok: int = 0
    err: int = 0
    skip: int = 0
    records: list[StepRecord] = dc_field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.err == 0 and self.ok > 0


class Recorder(Protocol):
    def on_step(self, rec: StepRecord) -> None: ...
    def on_finish(self, summary: RunSummary) -> None: ...


class Executor:
    def __init__(
        self,
        design: dict[str, Any],
        *,
        run_id: str,
        org_id: str,
        account_id: str,
        ts: str,
        recorders: Optional[list[Recorder]] = None,
        store=None,
    ) -> None:
        self.design = design
        self.run_id = run_id
        self.ctx = ExecCtx(
            org_id=org_id, account_id=account_id, design=design, ts=ts,
            store=store,
        )
        self.recorders = recorders or []
        self.summary = RunSummary(run_id=run_id, org_id=org_id)
        # Resume mode: an existing app store is provided up front.
        if store is not None:
            self.summary.app_id = store.app_id
            self.summary.app_name = store.app_meta().get("name", "")

    def _emit(self, rec: StepRecord) -> None:
        if rec.status == STATUS_OK:
            self.summary.ok += 1
        elif rec.status == STATUS_ERR:
            self.summary.err += 1
        else:
            self.summary.skip += 1
        self.summary.records.append(rec)
        for r in self.recorders:
            r.on_step(rec)

    def run(self, steps: list[Step]) -> RunSummary:
        aborted = False
        failed_worksheets: set[str] = set()  # logical names of worksheets that failed
        for step in steps:
            if aborted:
                self._emit(StepRecord(
                    step_id=step.id, kind=step.kind, name=step.name,
                    phase=step.phase, status=STATUS_SKIP,
                    error="aborted: a prerequisite step failed",
                ))
                continue

            start = time.monotonic()
            try:
                outcome = S.get_handler(step.kind)(self.ctx, step)
            except NotLoggedInError as e:
                # Unrecoverable — stop the whole run.
                self._emit(self._err_record(step, start, str(e)))
                aborted = True
                continue
            except Exception as e:  # noqa: BLE001 — record any handler failure
                msg = f"{type(e).__name__}: {e}"
                # If this failure is merely a knock-on of an earlier failed
                # worksheet (its logical name appears in the error), record it
                # as SKIP with the root cause — so the report shows one root
                # failure instead of a flood of look-alike ResolveErrors.
                dep = next((w for w in failed_worksheets
                            if w and (f"'{w}'" in str(e) or f"{w!r}" in str(e))),
                           None)
                if dep is not None and step.kind != "worksheet":
                    self._emit(StepRecord(
                        step_id=step.id, kind=step.kind, name=step.name,
                        phase=step.phase, status=STATUS_SKIP,
                        error=f"skipped: depends on failed worksheet {dep!r} "
                              f"(root cause). original: {msg}",
                        duration_ms=int((time.monotonic() - start) * 1000),
                    ))
                    continue
                # A PartialStepFailure (or any error carrying ``created_id``)
                # means the entity WAS created but configuring / publishing it
                # failed. Keep the id on the record so the report marks it as
                # "created but not finished" (⚠️) and an in-place repair can
                # target it instead of rebuilding.
                partial_id = getattr(e, "created_id", "") or ""
                self._emit(self._err_record(step, start, msg, created_id=partial_id))
                if step.kind == "worksheet":
                    failed_worksheets.add(step.name)
                if step.kind == "app":
                    aborted = True  # nothing downstream can run without an app
                continue

            duration = int((time.monotonic() - start) * 1000)
            if step.kind == "app":
                self.summary.app_id = outcome.created_id
                self.summary.app_name = (
                    self.design["app"]["name"].replace("{ts}", self.ctx.ts)
                )
            self._emit(StepRecord(
                step_id=step.id, kind=step.kind, name=step.name, phase=step.phase,
                status=STATUS_OK, created_id=outcome.created_id,
                summary=outcome.summary,
                command=" ".join(outcome.commands[0]) if outcome.commands else "",
                commands=outcome.commands, resolved_refs=outcome.resolved_refs,
                capture_files=outcome.capture_files, duration_ms=duration,
            ))

        for r in self.recorders:
            r.on_finish(self.summary)
        return self.summary

    @staticmethod
    def _err_record(
        step: Step, start: float, error: str, created_id: str = ""
    ) -> StepRecord:
        return StepRecord(
            step_id=step.id, kind=step.kind, name=step.name, phase=step.phase,
            status=STATUS_ERR, error=error, created_id=created_id,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
