"""Filesystem and binary-path constants for the hap-app-creator scripts.

Everything is path-independent: the ``hap`` binary is resolved from the
``HAP_BIN`` environment variable (else ``PATH``), and all writable runtime
artifacts go under a working directory that is NEVER inside the skill
package. No machine-specific absolute paths are hard-coded here.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

# The scripts/ package dir and the skill root that contains it.
PKG_DIR = Path(__file__).resolve().parent
SKILL_DIR = PKG_DIR.parent

# The hap binary. LIVE calls must use an install whose keyring can decrypt
# the session token (per the repo CLAUDE.md, a venv-local hap may fail with
# padding errors). Point HAP_BIN at that install; otherwise fall back to the
# first ``hap`` on PATH. ``None`` here surfaces as a clear error in hap.run.
HAP_BIN = os.environ.get("HAP_BIN") or shutil.which("hap")

# Writable working directory for the per-app store + run logs. Must live
# OUTSIDE the skill package. Defaults to ~/.hap-app-creator so the store is
# stable across the working directory; override with HAP_APP_CREATOR_WORKDIR
# (e.g. a project-local ``$PWD/.hap-app-creator``).
WORKDIR = Path(
    os.environ.get("HAP_APP_CREATOR_WORKDIR") or (Path.home() / ".hap-app-creator")
).resolve()

# Captured-resource store: one folder per created app, named by appId.
# This is only the LEGACY / fallback root. By default a ``build`` writes the
# store, runs and reports into the design file's own directory (the project's
# ``{PROJECT_ROOT}/apps/{appName}-{appId}/`` folder) — see ``set_output_root``
# below — so generated app content stays inside the user's project, never the
# home dir.
APPS_DIR = WORKDIR / "apps"

# Per-run logs and reports: one folder per build/step invocation.
RUNS_DIR = WORKDIR / "runs"

# Where deleted app folders are archived by the cleanup command (legacy root).
DELETED_DIR = APPS_DIR / "_deleted"

# A tiny pointer index (NOT app content): maps a created appId to the absolute
# directory that actually holds its store, so ``cleanup``/``seed``/``step``
# can find a project-local store by appId alone. Lives in the home workdir.
REGISTRY_PATH = WORKDIR / "registry.json"

# Output-root override, set by ``build`` to the design file's directory so the
# whole run (store + runs + reports + mirror) lands beside the design doc.
_OUTPUT_ROOT: Path | None = None


def set_output_root(path) -> None:
    """Point all generated artifacts of the current process at ``path``.

    ``build`` calls this with the design file's parent directory so the app
    store, run logs and report all land in the project's app folder instead
    of the home workdir. When unset, the legacy home roots apply.
    """
    global _OUTPUT_ROOT
    _OUTPUT_ROOT = Path(path).resolve() if path else None


def runs_dir() -> Path:
    """Directory for per-run logs/reports (output-root aware)."""
    if _OUTPUT_ROOT is not None:
        return _OUTPUT_ROOT / "runs"
    return RUNS_DIR


def _load_registry() -> dict:
    import json
    try:
        return json.loads(REGISTRY_PATH.read_text("utf-8"))
    except Exception:
        return {}


def register_app_store(app_id: str, store_dir) -> None:
    """Record ``appId -> absolute store dir`` in the home pointer index so a
    later ``cleanup``/``seed``/``step <appId>`` can locate a project-local
    store. Best-effort; failures are non-fatal."""
    import json
    if not app_id:
        return
    try:
        reg = _load_registry()
        reg[app_id] = str(Path(store_dir).resolve())
        WORKDIR.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(
            json.dumps(reg, ensure_ascii=False, indent=2), "utf-8")
    except Exception:
        pass


def deregister_app_store(app_id: str) -> None:
    """Drop an appId from the pointer index (called after cleanup)."""
    import json
    try:
        reg = _load_registry()
        if app_id in reg:
            del reg[app_id]
            REGISTRY_PATH.write_text(
                json.dumps(reg, ensure_ascii=False, indent=2), "utf-8")
    except Exception:
        pass


def _store_id(app_dir: Path) -> str:
    """Read the appId persisted in ``<dir>/app.json`` (empty if absent)."""
    import json
    try:
        return str(json.loads((app_dir / "app.json").read_text("utf-8")).get("id", ""))
    except Exception:
        return ""


def _search_store(root: Path, app_id: str) -> Path | None:
    """Find an immediate subdir of ``root`` whose app.json id == app_id.

    Tolerates a folder renamed to ``{appName}-{appId}`` after the build."""
    try:
        if not root.is_dir():
            return None
        for child in root.iterdir():
            if child.is_dir() and _store_id(child) == app_id:
                return child
    except Exception:
        return None
    return None


def app_store_dir(app_id: str) -> Path:
    """Resolve the store directory for ``app_id``.

    Resolution order:
      1. the active output-root override (a ``build`` in progress) — the
         design file's own directory IS the app store, no appId subfolder;
      2. the home pointer index (a previously built project-local store),
         with a rename-tolerant search of its parent if the exact path moved;
      3. a search of ``$PWD/apps`` (the project's app folders) by app.json id;
      4. the legacy ``~/.hap-app-creator/apps/<appId>`` location.
    """
    if _OUTPUT_ROOT is not None:
        return _OUTPUT_ROOT
    reg = _load_registry()
    if app_id in reg:
        p = Path(reg[app_id])
        if (p / "app.json").is_file():
            return p
        # Stale entry (folder renamed to add the appId suffix): re-find it.
        found = _search_store(p.parent, app_id)
        if found:
            return found
    found = _search_store(Path.cwd() / "apps", app_id)
    if found:
        return found
    return APPS_DIR / app_id

# Design documents + the JSON Schema contract (shipped inside the package).
DESIGN_DIR = PKG_DIR / "design"
SCHEMA_PATH = DESIGN_DIR / "design.schema.json"

# Default subprocess timeout (seconds) for a single hap command.
DEFAULT_TIMEOUT = int(os.environ.get("HAP_APP_CREATOR_TIMEOUT", "120"))
