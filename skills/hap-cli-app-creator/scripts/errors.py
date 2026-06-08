"""Exception types for the live-test harness."""
from __future__ import annotations

from typing import Any, Optional


class LiveTestError(Exception):
    """Base class for all harness errors."""


class HapCommandError(LiveTestError):
    """A ``hap`` subprocess returned a non-zero exit or unparseable output.

    Carries the full argv and captured streams so the recorder can show
    exactly what failed.
    """

    def __init__(
        self,
        message: str,
        *,
        argv: Optional[list[str]] = None,
        returncode: Optional[int] = None,
        stdout: str = "",
        stderr: str = "",
        payload: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.argv = argv or []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        # Parsed JSON error payload from the CLI, when available
        # (e.g. {"error": ..., "type": ..., "not_logged_in": true}).
        self.payload = payload


class NotLoggedInError(HapCommandError):
    """The CLI reported an unauthenticated/expired session.

    Raised eagerly so the runner can abort the whole run instead of
    letting every subsequent step fail the same way.
    """


class ResolveError(LiveTestError):
    """A logical name could not be resolved to a real id in the store."""


class PartialStepFailure(LiveTestError):
    """A step created its top-level entity but then failed while configuring
    or publishing it (e.g. a workflow process was created but adding nodes /
    publishing it failed).

    Carries the real ``created_id`` of the already-created entity so the run
    report can mark the step as "created but not finished" (⚠️) and surface
    the id — enabling an in-place repair (via hap-cli-app-editor) that targets the
    existing entity instead of rebuilding it.
    """

    def __init__(self, message: str, *, created_id: str = "") -> None:
        super().__init__(message)
        self.created_id = created_id or ""


class DesignError(LiveTestError):
    """The design document is invalid (schema violation or bad reference)."""
