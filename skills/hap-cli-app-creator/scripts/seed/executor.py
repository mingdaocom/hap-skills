"""Push an AI-authored seed data file into a live app.

Input data shape (``_seed_data.json``)::

    { "<worksheetName>": [ { "_ref": "M1", "<field>": <value>, ... }, ... ], ... }

* ``_ref`` is an optional per-row logical label.
* Relation fields reference other rows by ``"@label"`` (single) or
  ``["@l1", "@l2"]`` (multi). ``"@me"`` resolves to the current user.
* Everything else is passed verbatim to ``hap record batch-create`` —
  the CLI serializes each cell by its field type (option label -> key,
  relation rowId -> [{sid}], etc.).

The executor topologically orders tables by relation dependency, pushes
each via batch-create, captures the real rowIds and substitutes them
into downstream ``@label`` references. A self-relation (tree) table is
seeded LAYER BY LAYER — roots first, then repeatedly whatever rows whose
self-parent has just been created — so trees of arbitrary depth work
(not just two levels).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from scripts import hap
from scripts.errors import ResolveError
from scripts.seed.template import build_fill_template

logger = logging.getLogger("scripts.seed")

# Bundled sample attachments (sample.pdf / sample.docx …) live here. The
# preset ``documents`` in resources/attachments.json reference them by a
# RELATIVE name (e.g. "sample.pdf"); we resolve those against this dir so the
# upload's open() finds them regardless of the process CWD.
_RESOURCES_DIR = Path(__file__).resolve().parent / "resources"


def _resolve_attachment_path(desc: Any) -> Any:
    """Resolve a relative local-file ``path`` in an attachment descriptor to
    an absolute path under the bundled resources dir.

    - ``{name, url}`` (remote) → unchanged.
    - ``{name, path}`` with an ABSOLUTE existing path → unchanged.
    - ``{name, path}`` with a RELATIVE path → resolved against resources/ if
      that file exists there (so presets like "sample.pdf" just work); the
      project CWD is tried as a fallback before giving up (left as-is).
    """
    if not isinstance(desc, dict):
        return desc
    path = desc.get("path")
    if not path or desc.get("url"):
        return desc
    p = Path(path)
    if p.is_absolute():
        return desc
    bundled = _RESOURCES_DIR / path
    if bundled.is_file():
        return {**desc, "path": str(bundled)}
    cwd_rel = Path.cwd() / path
    if cwd_rel.is_file():
        return {**desc, "path": str(cwd_rel.resolve())}
    return desc  # leave as-is; upload will surface a clear file-not-found

# Virtual-user tokens (INSTRUCTIONS.md). The HAP server accepts them as
# real placeholder accounts (verified live: virtualuser-cn-1 -> 赵子轩), so
# member fields pass them straight through to batch-create.
_VIRTUAL_USER_PREFIX = "virtualuser-"


def _topo_order(tables: list[str], deps: dict[str, set[str]]) -> list[str]:
    """Order tables so a table's relation targets come first. Only deps
    that are themselves being seeded count. Cycles fall back to input
    order for the unresolved remainder (logged)."""
    pending = list(tables)
    done: set[str] = set()
    order: list[str] = []
    while pending:
        progressed = False
        for name in list(pending):
            if deps.get(name, set()) <= done:
                order.append(name)
                done.add(name)
                pending.remove(name)
                progressed = True
        if not progressed:
            logger.warning(
                "seed: relation cycle among %s — seeding in input order; "
                "unresolved @refs will error", pending)
            order.extend(pending)
            break
    return order


class _Resolver:
    """Resolves ``@label`` / ``@me`` / virtual-user tokens to real ids."""

    def __init__(self, me_id_fn: Callable[[], str]) -> None:
        self.labels: dict[str, str] = {}
        self._me_id_fn = me_id_fn
        self._me_id: Optional[str] = None

    def me(self) -> str:
        if self._me_id is None:
            self._me_id = self._me_id_fn() or ""
        return self._me_id

    def value(self, v: Any) -> Any:
        if isinstance(v, list):
            return [self.value(x) for x in v]
        if isinstance(v, dict):
            return {k: self.value(x) for k, x in v.items()}
        if isinstance(v, str):
            # Virtual-user tokens pass straight through (server resolves them).
            if v.startswith(_VIRTUAL_USER_PREFIX):
                return v
            if v == "@me":  # optional convenience sentinel (current user)
                return self.me()
            if v.startswith("@"):
                label = v[1:]
                if label not in self.labels:
                    raise ResolveError(
                        f"seed: unresolved relation ref {v!r}; known labels: "
                        f"{', '.join(sorted(self.labels)) or '<none>'}")
                return self.labels[label]
        return v

    def row(self, row: dict[str, Any], *, drop: set[str] = frozenset()) -> tuple[dict[str, Any], Optional[str]]:
        """Return (cleaned row for batch-create, _ref label or None).
        ``drop`` field names are removed (used for self-relation phase A)."""
        ref = row.get("_ref")
        out = {
            k: self.value(v)
            for k, v in row.items()
            if k != "_ref" and k not in drop
        }
        return out, ref


def _record_attachment_cell(descriptors: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap general uploaded-file descriptors into a worksheet Attachment
    (type 14) cell value (mirrors core upload.record_attachment_cell)."""
    attachments = []
    for i, d in enumerate(descriptors):
        attachments.append({
            "fileID": d.get("fileID"), "fileSize": d.get("fileSize"),
            "serverName": d.get("serverName"), "filePath": d.get("filePath"),
            "fileName": d.get("fileName"), "fileExt": d.get("fileExt"),
            "originalFileName": d.get("originalFileName"), "key": d.get("key"),
            "url": d.get("url"), "oldOriginalFileName": d.get("originalFileName"),
            "index": i, "isEdit": False,
        })
    return {"attachmentData": [], "attachments": attachments, "knowledgeAtts": []}


def _upload_row_attachments(
    row: dict[str, Any], attach_fields: set[str], wsid: str, app_id: str,
    run: Callable[..., Any],
) -> dict[str, Any]:
    """Replace a row's [{name,url}] attachment descriptors with an uploaded
    Attachment cell. Files are uploaded via the general ``hap upload``
    command; the returned descriptors are wrapped into the type-14 cell.
    Non-attachment keys and empty attachment fields pass through."""
    out = dict(row)
    for field in attach_fields:
        desc = row.get(field)
        if not desc:
            continue
        files = desc if isinstance(desc, list) else [desc]
        # Resolve bundled/relative local-file paths to absolute before upload
        # (a remote {name,url} descriptor passes through untouched).
        files = [_resolve_attachment_path(f) for f in files]
        try:
            result = run([
                "upload", "--worksheet-id", wsid, "--app-id", app_id,
                "--files", json.dumps(files, ensure_ascii=False),
            ])
            descriptors = getattr(result, "data", None)
        except Exception as e:  # one bad source must not abort the whole seed
            logger.warning("seed: attachment upload for %s failed (%s); dropped", field, e)
            descriptors = None
        if isinstance(descriptors, list) and descriptors:
            out[field] = _record_attachment_cell(descriptors)
        else:
            out.pop(field, None)  # nothing uploaded — drop, don't crash the row
            if not isinstance(descriptors, list):
                logger.warning("seed: attachment upload for %s returned nothing; dropped", field)
    return out


def _extract_row_ids(data: Any) -> list[str]:
    if isinstance(data, dict):
        ids = data.get("rowIds")
        if isinstance(ids, list):
            return [str(i) for i in ids]
    return []


def seed_app(
    store,
    data: dict[str, list[dict[str, Any]]],
    *,
    trigger_workflow: bool = False,
    hap_run: Optional[Callable[..., Any]] = None,
    me_id: Optional[str] = None,
) -> dict[str, Any]:
    """Seed ``data`` into the app captured in ``store``. Returns a summary
    ``{tables: [{name, requested, created}], total, rowsByWorksheet}``.

    ``hap_run`` / ``me_id`` are injectable for offline tests.
    """
    run = hap_run or hap.run
    me_fn = (lambda: me_id) if me_id is not None else (lambda: hap.whoami().get("id", ""))
    resolver = _Resolver(me_fn)

    templates = {t["worksheetName"]: t for t in build_fill_template(store)}

    # Dependency graph among the tables actually present in the data.
    present = [name for name in data if data[name]]
    deps: dict[str, set[str]] = {}
    self_rel: dict[str, set[str]] = {}
    # Attachment fields carry friendly [{name,url}] descriptors that must
    # be uploaded to the file store first (the server needs a fileID, not a
    # bare URL). Each is replaced in-place with the assembled cell via the
    # general `hap upload` command before batch-create.
    attach_fields: dict[str, set[str]] = {}
    for name in present:
        t = templates.get(name, {})
        deps[name] = {
            d for d in t.get("relationDeps", []) if d in present
        }
        self_rel[name] = {
            f["name"] for f in t.get("fillableFields", [])
            if f.get("isSelfRelation")
        }
        attach_fields[name] = {
            f["name"] for f in t.get("fillableFields", [])
            if f.get("type") == "Attachment"
        }
    order = _topo_order(present, deps)

    rows_by_ws: dict[str, list[str]] = {}
    summary: list[dict[str, Any]] = []

    def _push(wsid: str, rows: list[dict[str, Any]], *, drop: set[str] = frozenset()) -> None:
        if not rows:
            return
        payload: list[dict[str, Any]] = []
        refs: list[Optional[str]] = []
        for r in rows:
            cleaned, ref = resolver.row(r, drop=drop)
            payload.append(cleaned)
            refs.append(ref)
        argv = ["worksheet", "record", "batch-create", wsid,
                "--rows", json.dumps(payload, ensure_ascii=False)]
        if not trigger_workflow:
            argv.append("--no-workflow")
        result = run(argv)
        new_ids = _extract_row_ids(getattr(result, "data", None))
        rows_by_ws.setdefault(wsid, []).extend(new_ids)
        for ref, rid in zip(refs, new_ids):
            if ref:
                resolver.labels[ref] = rid

    for name in order:
        wsid = store.resolve("worksheet", name)
        rows = data[name]
        # Upload Attachment cells: turn [{name,url}] descriptors into the
        # real cell value via the general `hap upload` command.
        af = attach_fields.get(name, set())
        if af and any(k in af for r in rows for k in r):
            rows = [_upload_row_attachments(r, af, wsid, store.app_id, run)
                    for r in rows]
        sr = self_rel.get(name, set())
        if sr:
            # Self-relation tree of ARBITRARY depth. A row can only be created
            # once every row it points at (its self-relation parent) already
            # has a real rowid — because batch-create resolves all @refs up
            # front and registers labels only afterwards. So push in layers:
            # roots first, then repeatedly whatever rows whose parents now
            # exist. (The old two-phase "roots then all children at once"
            # capped trees at 2 levels: a level-3 row referencing a level-2
            # row in the same batch couldn't resolve it.)
            def _has_self(row: dict[str, Any]) -> bool:
                return any(row.get(f) for f in sr)

            def _self_parent_labels(row: dict[str, Any]) -> set:
                labels: set = set()
                for f in sr:
                    v = row.get(f)
                    for x in (v if isinstance(v, list) else [v]):
                        if isinstance(x, str) and x.startswith("@") and x != "@me":
                            labels.add(x[1:])
                return labels

            roots = [r for r in rows if not _has_self(r)]
            _push(wsid, roots, drop=sr)      # drop empty self fields on roots
            pending = [r for r in rows if _has_self(r)]
            while pending:
                # Rows whose every self-parent @label is already created.
                ready = [r for r in pending
                         if _self_parent_labels(r) <= set(resolver.labels)]
                if not ready:
                    # Cycle or a parent label that's never defined — push the
                    # rest as-is so the resolver raises a clear @ref error.
                    logger.warning(
                        "seed: %s self-relation: %d row(s) with unresolved "
                        "parent @ref (cycle or missing label); pushing as-is",
                        name, len(pending))
                    _push(wsid, pending)
                    break
                _push(wsid, ready)
                ready_ids = {id(r) for r in ready}
                pending = [r for r in pending if id(r) not in ready_ids]
        else:
            _push(wsid, rows)
        summary.append({
            "name": name,
            "requested": len(rows),
            "created": len(rows_by_ws.get(wsid, [])),
        })

    # Persist rowIds for resume / inspection.
    out_path = store.dir / "_seed_rows.json"
    out_path.write_text(
        json.dumps(rows_by_ws, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    return {
        "tables": summary,
        "total": sum(len(v) for v in rows_by_ws.values()),
        "rowsByWorksheet": rows_by_ws,
    }
