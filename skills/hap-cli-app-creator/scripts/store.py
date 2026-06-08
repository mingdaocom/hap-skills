"""Two-tier captured-resource store: ``apps/<appId>/``.

Every resource the smoke run creates is persisted here so that (a) later
steps can resolve a logical name (e.g. worksheet "客户表") to the real
server id, and (b) the dev-phase single-step runner can pull all
upstream ids without re-creating anything.

Layout per app folder::

    apps/<appId>/
      app.json                       # self-contained: id, org, sections
      worksheets.json                # index: byName + items
      worksheet_<id>.json            # detail: full config + controlsByName
      custom_pages.json / custom_page_<id>.json
      chatbots.json    / chatbot_<id>.json
      workflows.json   / workflow_<id>.json     (detail carries nodes)
      roles.json       / role_<id>.json
      optionsets.json                # index only (no per-id detail)
      worksheet_<wid>_custom_action_<aid>.json  # action detail

Each index file is ``{kind, byName, items}`` where ``byName`` maps a
logical name to its real id (the O(1) resolve table). Each detail file
is ``{kind, id, name, detail, ...}``. Worksheet details additionally
carry ``controlsByName`` (logical column -> real controlId) and embedded
``views`` so cross-sheet references resolve cleanly.

All writes are atomic (temp file + ``os.replace``) and JSON is written
with a stable shape (sorted keys, indent=2, ``ensure_ascii=False``) so
diffs stay readable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Optional

from scripts import config
from scripts.errors import ResolveError

# kind -> (index filename, detail filename template). A None detail
# template means the kind is index-only (e.g. optionsets).
_KIND_SPECS: dict[str, tuple[str, Optional[str]]] = {
    "worksheet": ("worksheets.json", "worksheet_{id}.json"),
    "custom_page": ("custom_pages.json", "custom_page_{id}.json"),
    "chatbot": ("chatbots.json", "chatbot_{id}.json"),
    "workflow": ("workflows.json", "workflow_{id}.json"),
    "role": ("roles.json", "role_{id}.json"),
    "optionset": ("optionsets.json", None),
}


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    tmp.write_text(text + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _controls_by_name(controls: Iterable[dict[str, Any]]) -> dict[str, str]:
    """Map each control's display name to its real controlId.

    Skips layout-only controls (split line 22, section/tab 52) which have
    no addressable value, and entries missing a name or id.
    """
    out: dict[str, str] = {}
    for c in controls:
        name = c.get("controlName") or c.get("name")
        cid = c.get("controlId") or c.get("id")
        if name and cid and c.get("type") not in (22, 52):
            out[str(name)] = str(cid)
    return out


class Store:
    """Read/write facade over a single ``apps/<appId>/`` folder."""

    def __init__(self, app_dir: Path, app_id: str = "") -> None:
        self.dir = Path(app_dir)
        # Explicit appId is authoritative — the store dir is NOT necessarily
        # named by appId (a project-local store folder is ``{appName}-{appId}``).
        self._app_id = app_id

    # ── construction ────────────────────────────────────────────────
    @classmethod
    def for_app(cls, app_id: str) -> "Store":
        # Output-root aware: during a build the store lives in the design
        # file's own directory; otherwise it's resolved via the pointer index
        # or the legacy home location (see config.app_store_dir).
        return cls(config.app_store_dir(app_id), app_id=app_id)

    @property
    def app_id(self) -> str:
        # Prefer the explicit id, then the persisted app.json id, and only
        # fall back to the folder name (legacy ``apps/<appId>`` layout).
        if self._app_id:
            return self._app_id
        if (self.dir / "app.json").is_file():
            try:
                aid = self.app_meta().get("id")
                if aid:
                    return str(aid)
            except Exception:
                pass
        return self.dir.name

    def exists(self) -> bool:
        return (self.dir / "app.json").is_file()

    # ── app + sections ──────────────────────────────────────────────
    def put_app(
        self,
        app_id: str,
        name: str,
        org_id: str,
        sections: list[dict[str, Any]],
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        """Write ``app.json`` (self-contained, includes sections)."""
        by_name = {
            s["name"]: s["id"]
            for s in sections
            if s.get("name") and s.get("id")
        }
        _atomic_write_json(
            self.dir / "app.json",
            {
                "kind": "app",
                "id": app_id,
                "name": name,
                "org_id": org_id,
                "sections": sections,
                "sectionsByName": by_name,
                "detail": detail or {},
            },
        )

    def app_meta(self) -> dict[str, Any]:
        return _read_json(self.dir / "app.json")

    def resolve_section(self, name: str) -> str:
        meta = self.app_meta()
        sid = meta.get("sectionsByName", {}).get(name)
        if not sid:
            raise ResolveError(
                f"section {name!r} not found in {self.dir.name}/app.json"
            )
        return sid

    # ── generic entity put/resolve ──────────────────────────────────
    def _index_path(self, kind: str) -> Path:
        idx_name, _ = _KIND_SPECS[kind]
        return self.dir / idx_name

    def _detail_path(self, kind: str, entity_id: str) -> Optional[Path]:
        _, detail_tpl = _KIND_SPECS[kind]
        if detail_tpl is None:
            return None
        return self.dir / detail_tpl.format(id=entity_id)

    def index(self, kind: str) -> dict[str, Any]:
        path = self._index_path(kind)
        if path.is_file():
            return _read_json(path)
        return {"kind": kind, "byName": {}, "items": []}

    def _write_index(self, kind: str, idx: dict[str, Any]) -> None:
        _atomic_write_json(self._index_path(kind), idx)

    def put_entity(
        self,
        kind: str,
        entity_id: str,
        name: str,
        detail: dict[str, Any],
        summary: Optional[dict[str, Any]] = None,
        extra_detail: Optional[dict[str, Any]] = None,
    ) -> None:
        """Upsert one entity: update the index and write its detail file.

        ``extra_detail`` lets callers stash derived lookup tables (e.g.
        ``controlsByName``) alongside ``detail`` in the detail file.
        """
        if kind not in _KIND_SPECS:
            raise KeyError(f"unknown store kind: {kind!r}")

        idx = self.index(kind)
        # Never downgrade a known id to empty: re-creating an entity that
        # already exists can return no id. Keep the previously captured id so
        # the index stays resolvable.
        eid = entity_id or idx.get("byName", {}).get(name) or ""
        idx.setdefault("byName", {})[name] = eid
        # Dedup by BOTH id and name (logical names are unique per kind) so a
        # re-run can't leave a duplicate / empty-id entry behind.
        items = [i for i in idx.get("items", [])
                 if i.get("id") != eid and i.get("name") != name]
        items.append({"id": eid, "name": name, "summary": summary or {}})
        idx["items"] = sorted(items, key=lambda i: i.get("name", ""))
        idx["kind"] = kind
        self._write_index(kind, idx)

        # Only (re)write the detail file when this run produced a fresh id; a
        # recovered existing id means the detail file on disk is already good.
        detail_path = self._detail_path(kind, entity_id) if entity_id else None
        if detail_path is not None:
            doc = {
                "kind": kind,
                "id": entity_id,
                "name": name,
                "detail": detail,
            }
            if extra_detail:
                doc.update(extra_detail)
            _atomic_write_json(detail_path, doc)

    def resolve(self, kind: str, name: str) -> str:
        idx = self.index(kind)
        rid = idx.get("byName", {}).get(name)
        if not rid:
            known = ", ".join(sorted(idx.get("byName", {}))) or "<none>"
            raise ResolveError(
                f"{kind} {name!r} not found in {self.dir.name}. Known: {known}"
            )
        return rid

    def get(self, kind: str, entity_id: str) -> dict[str, Any]:
        path = self._detail_path(kind, entity_id)
        if path is None or not path.is_file():
            raise ResolveError(f"no detail file for {kind} {entity_id}")
        return _read_json(path)

    def list(self, kind: str) -> list[dict[str, Any]]:
        return self.index(kind).get("items", [])

    # ── worksheet controls ──────────────────────────────────────────
    def put_controls(
        self, worksheet_id: str, controls: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Refresh a worksheet detail's ``controlsByName`` from a fresh
        controls read. Returns the resulting name->controlId map.
        """
        doc = self.get("worksheet", worksheet_id)
        doc.setdefault("detail", {})["controls"] = controls
        mapping = _controls_by_name(controls)
        doc["controlsByName"] = mapping
        _atomic_write_json(
            self._detail_path("worksheet", worksheet_id), doc  # type: ignore[arg-type]
        )
        return mapping

    def get_control(self, worksheet_id: str, field_name: str) -> dict[str, Any]:
        """Return the full saved control dict for a column by its name.

        Used by the cross-sheet pass to read a bridge Relation's real
        ``dataSource`` (target worksheetId) when wiring Lookup/Rollup.
        """
        doc = self.get("worksheet", worksheet_id)
        # A layout-only control (Divider 22 / Section 52) may share a name with a
        # real field — e.g. a section Divider「诊疗项目」introducing a SubTable
        #「诊疗项目」. Prefer the real field; fall back to a layout control only
        # if that is the only match. (controlsByName already skips 22/52, so this
        # keeps get_control consistent with resolve_control.)
        layout_match: Optional[dict[str, Any]] = None
        for c in doc.get("detail", {}).get("controls", []):
            if (c.get("controlName") or c.get("name")) == field_name:
                if c.get("type") in (22, 52):
                    if layout_match is None:
                        layout_match = c
                    continue
                return c
        if layout_match is not None:
            return layout_match
        raise ResolveError(
            f"control {field_name!r} not found on worksheet {worksheet_id}"
        )

    def worksheet_controls(self, worksheet_id: str) -> list[dict[str, Any]]:
        """Return the saved raw controls list captured for a worksheet."""
        doc = self.get("worksheet", worksheet_id)
        return doc.get("detail", {}).get("controls", [])

    def first_control_ids(self, worksheet_id: str, n: int = 5) -> list[str]:
        """Return the first ``n`` real controlIds of a worksheet, in layout
        order, skipping layout-only controls (split line 22, section 52).

        Used as the default display columns for a multi-record relation's
        table / tab_table view when the design omits show_fields.
        """
        out: list[str] = []
        for c in self.worksheet_controls(worksheet_id):
            if c.get("type") in (22, 52):
                continue
            cid = c.get("controlId") or c.get("id")
            if cid:
                out.append(str(cid))
            if len(out) >= n:
                break
        return out

    def resolve_control(self, worksheet_id: str, field_name: str) -> str:
        doc = self.get("worksheet", worksheet_id)
        cid = doc.get("controlsByName", {}).get(field_name)
        if not cid:
            known = ", ".join(sorted(doc.get("controlsByName", {}))) or "<none>"
            raise ResolveError(
                f"control {field_name!r} not found on worksheet "
                f"{worksheet_id}. Known: {known}"
            )
        return cid

    # ── worksheet-scoped sub-entities: views ────────────────────────
    def put_view(
        self, worksheet_id: str, view_id: str, name: str, detail: dict[str, Any]
    ) -> None:
        doc = self.get("worksheet", worksheet_id)
        views = doc.setdefault("views", {})
        views[name] = {"id": view_id, "detail": detail}
        _atomic_write_json(
            self._detail_path("worksheet", worksheet_id), doc  # type: ignore[arg-type]
        )

    def resolve_view(self, worksheet_id: str, name: str) -> str:
        doc = self.get("worksheet", worksheet_id)
        view = doc.get("views", {}).get(name)
        if not view:
            known = ", ".join(sorted(doc.get("views", {}))) or "<none>"
            raise ResolveError(
                f"view {name!r} not found on worksheet {worksheet_id}. "
                f"Known: {known}"
            )
        return view["id"]

    # ── worksheet-scoped sub-entities: custom actions ───────────────
    def put_custom_action(
        self,
        worksheet_id: str,
        action_id: str,
        name: str,
        detail: dict[str, Any],
    ) -> None:
        path = self.dir / f"worksheet_{worksheet_id}_custom_action_{action_id}.json"
        _atomic_write_json(
            path,
            {
                "kind": "custom_action",
                "id": action_id,
                "name": name,
                "worksheet_id": worksheet_id,
                "detail": detail,
            },
        )

    def resolve_custom_action(self, worksheet_id: str, name: str) -> str:
        """Resolve a worksheet's custom-action button logical name -> btnId."""
        prefix = f"worksheet_{worksheet_id}_custom_action_"
        known = []
        for path in sorted(self.dir.glob(f"{prefix}*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            known.append(doc.get("name"))
            if doc.get("name") == name:
                return doc["id"]
        raise ResolveError(
            f"custom action {name!r} not found on worksheet {worksheet_id}. "
            f"Known: {', '.join(filter(None, known)) or '<none>'}"
        )

    def custom_action_shadow(self, worksheet_id: str, name: str) -> dict[str, str]:
        """Return the shadow-process refs ``{processId, triggerNodeId}`` captured
        when a ``trigger_workflow`` custom-action button was created. The
        button-triggered workflow rides this process to add its nodes."""
        prefix = f"worksheet_{worksheet_id}_custom_action_"
        for path in sorted(self.dir.glob(f"{prefix}*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("name") == name:
                det = doc.get("detail") or {}
                return {"processId": det.get("processId", "") or "",
                        "triggerNodeId": det.get("triggerNodeId", "") or ""}
        raise ResolveError(
            f"custom action {name!r} not found on worksheet {worksheet_id}")
