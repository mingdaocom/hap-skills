"""The single subprocess wrapper around the real ``hap`` binary.

Every live API call in the harness goes through :func:`run`. It always
runs ``<HAP_BIN> --json <args...>`` (``--json`` first, as the CLI
requires), captures stdout/stderr, and returns the parsed JSON payload.

Why subprocess the installed binary instead of importing core functions:
the homebrew-linked ``hap`` shares the keyring that can decrypt the
session token, and shelling out exercises the exact command-layer +
core + transport path a real user hits — true end-to-end coverage.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Optional

from scripts import config
from scripts.errors import HapCommandError, NotLoggedInError

logger = logging.getLogger("scripts.hap")


@dataclass
class HapResult:
    """Outcome of one ``hap`` invocation."""

    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    data: Any           # parsed JSON payload (dict/list/scalar) or {"_raw": str}
    duration_ms: int


def _parse_stdout(stdout: str) -> Any:
    """Parse the CLI's ``--json`` stdout.

    Returns the decoded JSON when possible; otherwise wraps the raw text
    as ``{"_raw": ...}`` so callers always get a structured value.
    """
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


def _is_not_logged_in(data: Any) -> bool:
    return isinstance(data, dict) and data.get("not_logged_in") is True


def run(
    args: list[str],
    *,
    timeout: Optional[int] = None,
    check: bool = True,
) -> HapResult:
    """Run ``hap --json <args>`` and return a :class:`HapResult`.

    Args:
        args: The command and its options/arguments, WITHOUT the leading
            ``--json`` (added automatically) and WITHOUT the binary path.
        timeout: Per-call timeout in seconds (defaults to config).
        check: When True (default), raise on a non-zero exit or an error
            payload. When False, return the result regardless so the
            caller can inspect ``returncode``/``data``.

    Raises:
        NotLoggedInError: The CLI reported an unauthenticated session.
        HapCommandError: Non-zero exit (and ``check`` is True), or the
            command timed out / the binary is missing.
    """
    if not config.HAP_BIN:
        raise HapCommandError(
            "no 'hap' binary found. Install hap-cli (`pip install hap-cli`) "
            "and/or set HAP_BIN to the install whose keyring can decrypt the "
            "session token.",
            argv=["hap", *args],
        )
    argv = [config.HAP_BIN, "--json", *args]
    timeout = timeout if timeout is not None else config.DEFAULT_TIMEOUT

    logger.info("RUN %s", " ".join(argv))
    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        raise HapCommandError(
            f"hap binary not found at {config.HAP_BIN!r}. "
            f"Set HAP_BIN or install via 'pip install -e .'.",
            argv=argv,
        ) from e
    except subprocess.TimeoutExpired as e:
        raise HapCommandError(
            f"hap command timed out after {timeout}s: {' '.join(args)}",
            argv=argv,
        ) from e
    duration_ms = int((time.monotonic() - start) * 1000)

    data = _parse_stdout(proc.stdout)
    result = HapResult(
        argv=argv,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        data=data,
        duration_ms=duration_ms,
    )
    logger.info("END rc=%s (%dms) %s", proc.returncode, duration_ms, args[:3])

    if _is_not_logged_in(data):
        raise NotLoggedInError(
            "Not logged in or token expired. Run 'hap auth login' first.",
            argv=argv,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            payload=data,
        )

    if check and proc.returncode != 0:
        # Prefer the CLI's structured error message; otherwise surface the
        # real server-side validation info, which the CLI often prints to
        # stdout (not stderr) as a JSON payload — e.g. `workflow node
        # batch-add` returns warnings/errorNodeIds/exception there. Without
        # this, the error collapses to a useless "hap exited 1".
        msg = ""
        if isinstance(data, dict):
            msg = (data.get("error") or data.get("exception")
                   or data.get("message") or data.get("errorMessage") or "")
            if not msg and data:
                snippet = json.dumps(data, ensure_ascii=False)
                msg = snippet if len(snippet) <= 2000 else snippet[:2000] + "…"
        if not msg:
            msg = proc.stderr.strip() or f"hap exited {proc.returncode}"
        raise HapCommandError(
            msg,
            argv=argv,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            payload=data if isinstance(data, dict) else None,
        )

    return result


def whoami() -> dict[str, Any]:
    """Return the logged-in user payload (id, name, current_org_id, ...)."""
    data = run(["auth", "whoami"]).data
    return data if isinstance(data, dict) else {}
