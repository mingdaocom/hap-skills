"""Live-test harness for hap-cli.

A standalone, declarative smoke-test runner that drives the REAL ``hap``
binary end-to-end: it walks an ID-free JSON design document, creates a
brand-new app and all its resources, captures every returned id/config
into ``apps/<appId>/`` (a two-tier index+detail store), and records the
run three ways (console table, JSONL log, markdown/html report).

This package is stdlib-only and lives at the repo top level on purpose —
it is NOT collected by ``pytest hap_cli/tests/`` (no ``test_*.py`` files,
not imported by conftest). See ``CLAUDE.md`` in this directory for usage.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
