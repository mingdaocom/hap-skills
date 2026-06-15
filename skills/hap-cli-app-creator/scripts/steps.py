"""Step model + per-resource handler registry.

A :class:`Step` is one unit of work the compiler emits from the design
document. Each step has a ``kind`` that selects a handler from the
registry. A handler resolves the step's logical references to real ids
(via the store), runs the matching ``hap`` command(s), captures the
returned ids/config into the store, and returns a :class:`StepOutcome`
the executor records.

Handlers are intentionally small and call :func:`scripts.hap.run`
directly so the exact end-to-end command path is exercised.
"""
from __future__ import annotations

import copy
import json
import logging
import re
import uuid
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Optional

from scripts import charts as CH
from scripts import config
from scripts import fields as F
from scripts import hap
from scripts import workflow_dsl as WD
from scripts.errors import PartialStepFailure, ResolveError
from scripts.store import Store

logger = logging.getLogger("hap_app_creator.steps")


def _bridge_source_control(
    store: Store, via_ctrl: dict[str, Any], field_name: str
) -> dict[str, Any]:
    """Resolve the far-side column a Rollup/Lookup aggregates or mirrors.

    Two bridge shapes:

    * **SubTable (type 34)** — the child columns are embedded directly in
      the SUB_LIST control's ``relationControls`` (with their real saved
      controlIds). The inline child worksheet is NOT independently
      queryable (``worksheet fields`` on its id returns empty), so resolve
      the column from ``relationControls``.
    * **multi-Relation (type 29)** — the column lives on the related
      target worksheet, which the store has captured.
    """
    if via_ctrl.get("type") == 34:  # SUB_LIST
        for c in via_ctrl.get("relationControls") or []:
            if (c.get("controlName") or c.get("name")) == field_name:
                return c
        raise ResolveError(
            f"column {field_name!r} not found in SubTable "
            f"{via_ctrl.get('controlName')!r}")
    target_wsid = via_ctrl.get("dataSource")
    if not target_wsid:
        raise ResolveError(
            f"bridge {via_ctrl.get('controlName')!r} has no dataSource")
    return store.get_control(target_wsid, field_name)


@dataclass
class Step:
    """One unit of work in the smoke plan."""

    id: str            # unique, e.g. "worksheet:客户表"
    kind: str          # selects the handler
    name: str          # human label
    phase: str         # grouping label for the report
    spec: dict[str, Any]


@dataclass
class StepOutcome:
    """What a handler produced (recorded by the executor)."""

    created_id: Optional[str] = None
    summary: str = ""
    commands: list[list[str]] = dc_field(default_factory=list)
    capture_files: list[str] = dc_field(default_factory=list)
    resolved_refs: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class ExecCtx:
    """Shared state passed to every handler. ``store``/``app_id`` are set
    by the app handler once the new app id is known."""

    org_id: str
    account_id: str
    design: dict[str, Any]
    ts: str
    store: Optional[Store] = None


HandlerFn = Callable[[ExecCtx, Step], StepOutcome]
_REGISTRY: dict[str, HandlerFn] = {}


def handler(kind: str) -> Callable[[HandlerFn], HandlerFn]:
    def deco(fn: HandlerFn) -> HandlerFn:
        _REGISTRY[kind] = fn
        return fn
    return deco


def get_handler(kind: str) -> HandlerFn:
    if kind not in _REGISTRY:
        raise KeyError(f"no handler registered for step kind {kind!r}")
    return _REGISTRY[kind]


def _require_store(ctx: ExecCtx) -> Store:
    if ctx.store is None:
        raise RuntimeError("store not initialised — the app step must run first")
    return ctx.store


def _extract_id(data: Any, candidates: list[str]) -> Optional[str]:
    """Find the first present id key, checking the top level and a nested
    ``data`` envelope (v3 responses sometimes wrap)."""
    # Some v3 commands return the id bare as ``{"data": "<uuid>", ...}``.
    if isinstance(data, dict) and isinstance(data.get("data"), str) and data["data"]:
        return data["data"]
    sources = [data]
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        sources.append(data["data"])
    for src in sources:
        if not isinstance(src, dict):
            continue
        for key in candidates:
            if src.get(key):
                return str(src[key])
    return None


def _lookup_role_id(app_id: str, name: str) -> str:
    """Return the real id of an existing app role by name (via ``role list``).

    Used when ``role create`` returns no id because the role already exists.
    """
    res = hap.run(["app", "role", "list", "-a", app_id], check=False)
    data = res.data if isinstance(res.data, dict) else {}
    inner = data.get("data")
    roles = (inner.get("roles") if isinstance(inner, dict) else None) \
        or (inner if isinstance(inner, list) else None) \
        or data.get("roles") or []
    for r in roles:
        if isinstance(r, dict) and r.get("name") == name:
            return r.get("id") or r.get("roleId") or ""
    return ""


# ── helpers shared by worksheet handlers ────────────────────────────────

def _read_and_store_controls(store: Store, worksheet_id: str) -> list[dict[str, Any]]:
    """Re-read a worksheet's wire controls and refresh controlsByName.

    The server replaces our client-side controlIds on save, so we must
    read them back before any cross-sheet field references them.
    """
    res = hap.run(["worksheet", "fields", worksheet_id, "--raw"])
    controls = res.data if isinstance(res.data, list) else res.data.get("controls", [])
    store.put_controls(worksheet_id, controls)
    return controls


# Multi-record relations shown as a table/tab_table need display columns.
_TABLE_DISPLAYS = {"table", "tab_table"}
_DEFAULT_SHOW_FIELDS = 5


def _show_field_ids(
    store: Store,
    sheet_id: str,
    show_fields: Optional[list[str]],
    multi: bool,
    display: Optional[str],
) -> list[str]:
    """Resolve a relation's display columns to controlIds.

    If ``show_fields`` is given, resolve each logical name. Otherwise, for
    a multi-record table/tab_table relation, default to the first
    ``_DEFAULT_SHOW_FIELDS`` columns of the target sheet (the rule: take
    the target's first 5 fields). Single relations need none.

    Resolution is TOLERANT: a name that does not resolve yet (e.g. a
    derived Rollup/Lookup column built in a later phase) is skipped with a
    warning rather than aborting the whole relation. The compiler defers
    non-bridge reverse relations until after the Derived pass so this only
    bites the rare bridge-reverse case (BUILD-09).
    """
    if show_fields:
        ids: list[str] = []
        for n in show_fields:
            try:
                ids.append(store.resolve_control(sheet_id, n))
            except ResolveError:
                logger.warning(
                    "show_fields: column %r not found on worksheet %s yet "
                    "(likely a derived field built later) — skipping it from "
                    "the relation display", n, sheet_id,
                )
        return ids
    if multi and display in _TABLE_DISPLAYS:
        return store.first_control_ids(sheet_id, _DEFAULT_SHOW_FIELDS)
    return []


# A real HAP controlId is a 24-hex MongoDB ObjectId (pd-openweb
# WORKSHEET_OBJECT_ID_REG). Anything else is a client-side placeholder.
_OBJECT_ID_RE = re.compile(r"^[a-f0-9]{24}$", re.IGNORECASE)


def _strip_client_control_ids(controls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop client-generated controlIds before AddWorksheetControls.

    pd-openweb's quick-add path sends ``_.omit(control, ['controlId'])``
    and reads the real id back from the response — AddWorksheetControls
    only mints a proper 24-hex ObjectId when the caller omits the id.
    If we send our own ``uuid4().hex`` (32 chars, no dashes) the server
    persists it verbatim, leaving an invalid controlId that the grid /
    relation renderer can't resolve, so related-record cells stay blank
    until a later SaveWorksheetControls re-mints the id (the symptom a
    manual "save form layout twice" was working around).

    A controlId that IS a valid ObjectId is kept untouched — that is a
    server-reserved id (a two-way relation's reverse placeholder, which
    HAP pairs the forward/reverse halves by). Mutates in place.
    """
    for c in controls:
        cid = c.get("controlId")
        if cid and not _OBJECT_ID_RE.match(cid):
            c.pop("controlId", None)
    return controls


def _layout_new_controls(
    existing: list[dict[str, Any]], new_controls: list[dict[str, Any]]
) -> None:
    """Assign row/col to ``new_controls`` relative to ``existing`` (mutates).

    Layout strategy:
      * a new control with an explicit design ``__row__`` slots into THAT
        row (the design controls the whole form), col = next free slot;
      * the rest auto-pack into the 12-grid AFTER the existing layout —
        fill the last row while width remains, else wrap — so they land
        below the intra fields, half-widths side-by-side.
    """
    rows_map: dict[int, list[dict[str, Any]]] = {}
    for c in existing:
        rows_map.setdefault(c.get("row", 0), []).append(c)

    placed = [c for c in new_controls if "__row__" in c]
    floating = [c for c in new_controls if "__row__" not in c]
    for c in placed:
        r = c.pop("__row__")
        c.pop("__col__", None)
        c["row"] = r
        c["col"] = len(rows_map.get(r, []))
        rows_map.setdefault(r, []).append(c)

    last_row = max(rows_map.keys(), default=-1)
    in_last = rows_map.get(last_row, [])
    used = sum(int(c.get("size", 12)) for c in in_last)
    slot = len(in_last)
    cur_row = last_row if last_row >= 0 else 0
    if last_row < 0:
        used, slot = 0, 0
    for c in floating:
        size = int(c.get("size", 12))
        if used + size > 12:
            cur_row += 1
            used, slot = 0, 0
        c["row"] = cur_row
        c["col"] = slot
        used += size
        slot += 1


def _append_controls_pass(
    store: Store, worksheet_id: str, new_controls: list[dict[str, Any]]
) -> list[str]:
    """Append raw controls to a worksheet via ``add-fields --controls``.

    Sends ONLY the new controls (incremental AddWorksheetControls). The
    existing saved controls are read purely to compute layout (row/col)
    for the additions — they are NOT re-sent. Used for one-way relations
    and derived (lookup/rollup/barcode/cascade) controls. Returns the argv.
    """
    existing = store.worksheet_controls(worksheet_id)
    _layout_new_controls(existing, new_controls)
    _strip_client_control_ids(new_controls)
    argv = ["worksheet", "add-fields", worksheet_id,
            "--controls", json.dumps(new_controls, ensure_ascii=False)]
    hap.run(argv)
    _read_and_store_controls(store, worksheet_id)
    return argv


def _new_placeholder() -> str:
    """A dashed uuid4 placeholder controlId. SaveWorksheetControls detects
    the ``-`` separators, treats the control as new, and re-mints it to a
    real 24-hex ObjectId (and pairs a two-way relation's two halves)."""
    return str(uuid.uuid4())


def _save_controls_pass(
    store: Store, worksheet_id: str, new_controls: list[dict[str, Any]]
) -> list[str]:
    """Add new controls via a FULL SaveWorksheetControls (update-fields).

    Re-sends the worksheet's existing controls verbatim plus the new
    control(s). Used for two-way relations: the forward control carries
    its reverse half as an embedded ``sourceControl`` and the server only
    creates BOTH halves correctly paired on SaveWorksheetControls
    (AddWorksheetControls overwrites the reverse's back-link with a
    dangling placeholder). Client placeholder ids are NOT stripped — the
    server re-mints dashed-uuid placeholders itself.

    Re-sending existing controls is safe against the historical "drops new
    additions / duplicates when >=3 reverse controls exist" quirk: that
    quirk is triggered by re-sending a reverse whose back-link is DANGLING,
    and controls created via this path are never dangling (verified live:
    re-saving a clean reverse neither duplicates nor drops).
    """
    existing = store.worksheet_controls(worksheet_id)
    _layout_new_controls(existing, new_controls)
    full = list(existing) + list(new_controls)
    argv = ["worksheet", "update-fields", worksheet_id,
            "--controls", json.dumps(full, ensure_ascii=False)]
    hap.run(argv)
    _read_and_store_controls(store, worksheet_id)
    return argv


# ── handlers ────────────────────────────────────────────────────────────

# App PC navigation layout (design ``app.nav_layout``) -> HomeApp/EditAppInfo
# ``pcNaviStyle`` int. top=经典(导航在上方), group=左侧分组导航,
# card=卡片, tree=树形.
_NAV_LAYOUT_TO_PCNAVISTYLE = {"top": 0, "group": 1, "card": 2, "tree": 3}


@handler("app")
def _h_app(ctx: ExecCtx, step: Step) -> StepOutcome:
    app = ctx.design["app"]
    name = app["name"].replace("{ts}", ctx.ts)
    sections = app.get("sections", []) or []

    argv = ["app", "create", "-n", name, "--org-id", ctx.org_id]
    if app.get("icon"):
        argv += ["--icon", app["icon"]]
    if app.get("icon_color"):
        argv += ["--icon-color", app["icon_color"]]
    if app.get("nav_color"):
        argv += ["--nav-color", app["nav_color"]]
    if sections:
        argv += ["--sections", json.dumps(sections, ensure_ascii=False)]

    data = hap.run(argv).data
    # Some environments echo the raw HAP envelope ({state, data:{id}}) rather
    # than the unwrapped app object — check both levels.
    app_id = _extract_id(data, ["appId", "id"])
    if not app_id:
        raise RuntimeError(f"app create returned no appId: {data!r}")
    inner = data.get("data") if isinstance(data.get("data"), dict) else data
    by_name = inner.get("sectionIdByName", {}) or {}
    section_list = [{"id": by_name[n], "name": n} for n in sections if n in by_name]

    # PC navigation layout. `app create` can't set it, so apply it via a
    # follow-up `app update` (HomeApp/EditAppInfo pcNaviStyle) when the
    # design asks for a non-default layout.
    nav_layout = app.get("nav_layout")
    nav_cmd: list[str] | None = None
    if nav_layout:
        pc_nav = _NAV_LAYOUT_TO_PCNAVISTYLE.get(nav_layout)
        if pc_nav is None:
            raise RuntimeError(
                f"unknown app.nav_layout {nav_layout!r}; "
                f"expected one of {sorted(_NAV_LAYOUT_TO_PCNAVISTYLE)}")
        nav_cmd = ["app", "update", app_id, "--pc-nav-style", str(pc_nav)]
        hap.run(nav_cmd)

    # A blank new app ships with one auto-created empty-named section
    # ("未命名分组"). Our named sections are added on top, so remove any
    # leftover empty-named section to leave a clean sidebar.
    removed = _remove_unnamed_sections(app_id, keep_names=set(sections))

    store = Store.for_app(app_id)
    store.put_app(app_id, name, ctx.org_id, section_list, detail=data)
    ctx.store = store
    # Record appId -> store dir so a later cleanup/seed/step <appId> can find
    # a project-local store (the build writes everything beside the design doc).
    config.register_app_store(app_id, store.dir)

    extra = f", removed {len(removed)} unnamed" if removed else ""
    if nav_layout:
        extra += f", nav={nav_layout}"
    return StepOutcome(
        created_id=app_id,
        summary=f"app {name!r} ({len(section_list)} sections{extra})",
        commands=[argv] + ([nav_cmd] if nav_cmd else []),
        capture_files=["app.json"],
    )


def _remove_unnamed_sections(app_id: str, keep_names: set[str]) -> list[str]:
    """Delete the auto-created empty-named section(s) on a fresh app.

    Reads the real section list and deletes any section whose name is
    blank and that we did not request. Returns the deleted ids.
    """
    info = hap.run(["app", "info", "-a", app_id], check=False).data
    payload = info.get("data", info) if isinstance(info, dict) else {}
    sections = payload.get("sections", []) if isinstance(payload, dict) else []
    removed: list[str] = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        name = (sec.get("name") or "").strip()
        sid = sec.get("appSectionId") or sec.get("id")
        if sid and not name and name not in keep_names:
            try:
                hap.run(["app", "delete-section", app_id, sid, "-y"])
                removed.append(sid)
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass
    return removed


def _wire_subtable_child_relations(
    spec: dict[str, Any], design_field: dict[str, Any], store
) -> None:
    """Inject ``data_source`` (target worksheetId) into a SubTable's child
    Relation specs. ``intra_field_spec`` recurses into ``child_fields`` but
    cannot resolve a child Relation's target (no store access), so the child
    control would hit build_control's "RELATE_SHEET requires data_source".

    Resolves each child Relation's target by logical name. Targets are
    sibling top-level worksheets; ``compiler._ordered_worksheets`` sorts the
    Worksheets phase so a child-relation target is created before its host,
    so it's in the store by the time this worksheet builds. Mutates ``spec``
    in place.
    """
    child_specs = spec.get("child_fields") or []
    child_designs = design_field.get("child_fields") or []
    for cspec, cdesign in zip(child_specs, child_designs):
        if cdesign.get("type") != "Relation":
            continue
        rel = cdesign.get("relation") or {}
        target = rel.get("worksheet")
        if not target:
            continue
        # snake_case: child specs are passed verbatim to build_control.
        cspec["data_source"] = store.resolve("worksheet", target)
        if rel.get("display"):
            adv = dict(cspec.get("advanced_setting") or {})
            adv["showtype"] = F.DISPLAY_TO_SHOWTYPE[rel["display"]]
            cspec["advanced_setting"] = adv
        if rel.get("multi"):
            cspec["multi"] = True


@handler("worksheet")
def _h_worksheet(ctx: ExecCtx, step: Step) -> StepOutcome:
    store = _require_store(ctx)
    ws = step.spec["worksheet"]
    name = ws["name"]
    all_fields = ws.get("fields", []) or []
    intra = [f for f in all_fields if F.categorize(f) == "intra"]

    def _build_spec(f: dict[str, Any]) -> dict[str, Any]:
        oid = store.resolve("optionset", f["optionset"]) if f.get("optionset") else None
        spec = F.intra_field_spec(f, optionset_id=oid)
        if f.get("type") == "SubTable" and f.get("child_fields"):
            _wire_subtable_child_relations(spec, f, store)
        return spec

    field_specs = F.assign_explicit_cols([_build_spec(f) for f in intra])
    title_name = next((f["name"] for f in intra if f.get("is_title")), None)

    # AddWorkSheet requires a section; default to the first app section.
    if ws.get("section"):
        section_id = store.resolve_section(ws["section"])
    else:
        secs = store.app_meta().get("sections", [])
        if not secs:
            raise RuntimeError("worksheet needs a section but the app has none")
        section_id = secs[0]["id"]

    argv = ["worksheet", "create", ctx.store.app_id, name, "--section-id", section_id]
    if ws.get("icon"):
        argv += ["--icon", ws["icon"]]
    if field_specs:
        argv += ["--fields", json.dumps(field_specs, ensure_ascii=False)]
        if title_name:
            argv += ["--title-name", title_name]

    data = hap.run(argv).data
    wsid = data.get("worksheetId") or data.get("id")
    if not wsid:
        raise RuntimeError(f"worksheet create returned no worksheetId: {data!r}")

    store.put_entity("worksheet", wsid, name, detail=data,
                     summary={"section": ws.get("section")})
    controls = _read_and_store_controls(store, wsid)

    return StepOutcome(
        created_id=wsid,
        summary=f"worksheet {name!r} ({len(controls)} controls)",
        commands=[argv],
        capture_files=[f"worksheet_{wsid}.json", "worksheets.json"],
    )


@handler("relation")
def _h_relation(ctx: ExecCtx, step: Step) -> StepOutcome:
    """Forward half of a Relation field.

    One-way: appended via AddWorksheetControls (server mints the id).

    Two-way: the forward carries its reverse half as an embedded
    ``sourceControl`` and is sent via SaveWorksheetControls (see
    :func:`fields.bidirectional_relation_control`). The server creates BOTH
    halves correctly paired in one call, so the reverse's back-link never
    dangles (the bug that left a multi/tab_table reverse blank in the grid).
    The reverse therefore EXISTS after this step — the deferred
    ``relation_reverse`` step only refreshes its display columns once any
    derived ``two_way.show_fields`` have been built."""
    store = _require_store(ctx)
    host = step.spec["worksheet"]
    field = step.spec["field"]
    rel = field["relation"]

    host_wsid = store.resolve("worksheet", host)
    target_wsid = store.resolve("worksheet", rel["worksheet"])
    two_way = rel.get("two_way")
    multi = rel.get("multi", False)
    show_ids = _show_field_ids(store, target_wsid, rel.get("show_fields"),
                               multi, rel.get("display"))
    summary = f"relation {host}.{field['name']} -> {rel['worksheet']}"
    refs: dict[str, Any] = {"target": target_wsid, "show_controls": show_ids}

    if two_way:
        # Reverse display columns (host columns shown in the reverse
        # tab_table). Derived columns that don't exist yet are skipped here
        # and filled in by the deferred relation_reverse step.
        rev_show = _show_field_ids(store, host_wsid, two_way.get("show_fields"),
                                   True, two_way.get("display"))
        ctrl = F.bidirectional_relation_control(
            field["name"],
            target_worksheet_id=target_wsid,
            host_worksheet_id=host_wsid,
            forward_id=_new_placeholder(),
            reverse_id=_new_placeholder(),
            reverse_name=two_way["name"],
            multi=multi,
            display=rel.get("display"),
            show_control_ids=show_ids,
            reverse_display=two_way.get("display"),
            reverse_show_control_ids=rev_show,
            required=field.get("required", False),
        )
        F.apply_permission(ctrl, field)
        commands = [_save_controls_pass(store, host_wsid, [ctrl])]
        # The reverse now lives on the target worksheet — refresh its store.
        _read_and_store_controls(store, target_wsid)
        refs["reverse_show_controls"] = rev_show
    else:
        ctrl = F.relation_control(
            field["name"],
            target_worksheet_id=target_wsid,
            multi=multi,
            display=rel.get("display"),
            show_control_ids=show_ids,
            required=field.get("required", False),
            bidirectional=False,
        )
        F.apply_permission(ctrl, field)
        commands = [_append_controls_pass(store, host_wsid, [ctrl])]

    return StepOutcome(
        created_id=host_wsid,
        summary=summary,
        commands=commands,
        capture_files=[f"worksheet_{host_wsid}.json", f"worksheet_{target_wsid}.json"],
        resolved_refs=refs,
    )


@handler("relation_reverse")
def _h_relation_reverse(ctx: ExecCtx, step: Step) -> StepOutcome:
    """Deferred refresh of a two-way relation's reverse display columns.

    The reverse control is now created together with the forward (see
    :func:`_h_relation`), so it already exists on the target worksheet by
    the time this runs. This step exists only to run AFTER the Derived pass
    and fill in any ``two_way.show_fields`` that point at rollup / lookup
    columns of the host — columns that did not exist at relation-build time
    (BUILD-09). It is a no-op when the reverse's display columns are already
    complete (the common case: show_fields are plain columns, or omitted).
    """
    store = _require_store(ctx)
    host = step.spec["worksheet"]
    field = step.spec["field"]
    rel = field["relation"]
    two_way = rel["two_way"]

    host_wsid = store.resolve("worksheet", host)
    target_wsid = store.resolve("worksheet", rel["worksheet"])
    summary = f"reverse {rel['worksheet']}.{two_way['name']} <- {host}.{field['name']}"

    rev_show = _show_field_ids(store, host_wsid, two_way.get("show_fields"),
                               True, two_way.get("display"))
    try:
        rev = store.get_control(target_wsid, two_way["name"])
    except ResolveError:
        rev = None
    # Nothing to refresh: reverse missing (shouldn't happen), no show_fields
    # to resolve, or the display columns already match.
    if not rev or not rev_show or rev.get("showControls") == rev_show:
        return StepOutcome(
            created_id=target_wsid, summary=f"{summary} (display up to date)",
            commands=[], capture_files=[f"worksheet_{target_wsid}.json"],
            resolved_refs={"reverse_control": rev.get("controlId") if rev else None},
        )

    rev_id = rev["controlId"]
    controls = copy.deepcopy(store.worksheet_controls(target_wsid))
    for c in controls:
        if c.get("controlId") == rev_id:
            c["showControls"] = rev_show
    # Re-save the target's full layout with the reverse's display columns
    # updated. The reverse is clean (created paired), so the re-save neither
    # duplicates nor drops it.
    argv = ["worksheet", "update-fields", target_wsid,
            "--controls", json.dumps(controls, ensure_ascii=False)]
    hap.run(argv)
    _read_and_store_controls(store, target_wsid)
    return StepOutcome(
        created_id=target_wsid,
        summary=f"{summary} (display refreshed)",
        commands=[argv],
        capture_files=[f"worksheet_{host_wsid}.json", f"worksheet_{target_wsid}.json"],
        resolved_refs={"reverse_control": rev_id, "show_controls": rev_show},
    )


@handler("derived")
def _h_derived(ctx: ExecCtx, step: Step) -> StepOutcome:
    """Lookup (他表字段) / Rollup (汇总) / Barcode — all reference another
    control whose real id only exists after the worksheet is saved, so
    they are wired in this deferred pass."""
    store = _require_store(ctx)
    host = step.spec["worksheet"]
    field = step.spec["field"]
    host_wsid = store.resolve("worksheet", host)

    if field["type"] == "Barcode":
        source_cid = store.resolve_control(host_wsid, field["source"])
        ctrl = F.barcode_control(field["name"], source_control_id=source_cid)
        F.apply_permission(ctrl, field)
        argv = _append_controls_pass(store, host_wsid, [ctrl])
        return StepOutcome(
            created_id=host_wsid,
            summary=f"barcode {host}.{field['name']} <- {field['source']}",
            commands=[argv], capture_files=[f"worksheet_{host_wsid}.json"],
            resolved_refs={"source": source_cid},
        )

    if field["type"] == "AmountInWords":
        source_cid = store.resolve_control(host_wsid, field["source"])
        ctrl = F.amount_in_words_control(field["name"], source_control_id=source_cid)
        F.apply_attrs(ctrl, field)
        F.apply_permission(ctrl, field)
        argv = _append_controls_pass(store, host_wsid, [ctrl])
        return StepOutcome(
            created_id=host_wsid,
            summary=f"amount-in-words {host}.{field['name']} <- {field['source']}",
            commands=[argv], capture_files=[f"worksheet_{host_wsid}.json"],
            resolved_refs={"source": source_cid},
        )

    if field["type"] == "CascadingSelect":
        cfg = field["cascade"]
        source_wsid = store.resolve("worksheet", cfg["source"])
        # dataSource is the SOURCE WORKSHEET id at create time — the server
        # binds it to that table's self-relation hierarchy itself (verified
        # live: passing the self-relation control id instead returns 服务异常).
        show_ids = [store.resolve_control(source_wsid, n)
                    for n in (cfg.get("show_fields") or [])]
        ctrl = F.cascade_control(
            field["name"], source_worksheet_id=source_wsid,
            source_entity_name=cfg["source"], show_control_ids=show_ids,
            required=field.get("required", False),
        )
        F.apply_attrs(ctrl, field)
        F.apply_permission(ctrl, field)
        argv = _append_controls_pass(store, host_wsid, [ctrl])
        return StepOutcome(
            created_id=host_wsid,
            summary=f"cascade {host}.{field['name']} <- {cfg['source']}",
            commands=[argv], capture_files=[f"worksheet_{host_wsid}.json"],
            resolved_refs={"source_ws": source_wsid, "show": show_ids},
        )

    if field["type"] == "Lookup":
        cfg = field["lookup"]
        via_ctrl = store.get_control(host_wsid, cfg["via"])
        via_cid = via_ctrl["controlId"]
        target_wsid = via_ctrl.get("dataSource")
        if not target_wsid:
            raise RuntimeError(
                f"bridge {cfg['via']!r} has no dataSource on {host}"
            )
        source_cid = store.resolve_control(target_wsid, cfg["field"])
        ctrl = F.lookup_control(
            field["name"], via_control_id=via_cid,
            source_control_id=source_cid, required=field.get("required", False),
        )
        summary = f"lookup {host}.{field['name']} via {cfg['via']}->{cfg['field']}"
        refs = {"via": via_cid, "source": source_cid, "target": target_wsid}
    else:  # Rollup
        cfg = field["rollup"]
        via_ctrl = store.get_control(host_wsid, cfg["via"])
        via_cid = via_ctrl["controlId"]
        target_wsid = via_ctrl.get("dataSource")
        # Aggregated column: on the related worksheet (multi-Relation bridge)
        # or embedded in relationControls (SubTable bridge).
        source_cid = _bridge_source_control(store, via_ctrl, cfg["field"])["controlId"]
        # Optional filter on the aggregated sheet (conditions reference
        # columns on the target/subtable worksheet).
        filters = None
        if cfg.get("filter"):
            def _resolve(fname: str, _v=via_ctrl):
                return _bridge_source_control(store, _v, fname)
            filters = F.build_filter_conditions(cfg["filter"], _resolve)
        ctrl = F.rollup_control(
            field["name"], via_control_id=via_cid, source_control_id=source_cid,
            aggregate=cfg.get("aggregate", "sum"),
            required=field.get("required", False), filters=filters,
        )
        summary = f"rollup {host}.{field['name']} via {cfg['via']}->{cfg['field']} ({cfg.get('aggregate','sum')})"
        refs = {"via": via_cid, "source": source_cid, "target": target_wsid}

    F.apply_permission(ctrl, field)
    argv = _append_controls_pass(store, host_wsid, [ctrl])
    return StepOutcome(
        created_id=host_wsid, summary=summary, commands=[argv],
        capture_files=[f"worksheet_{host_wsid}.json"], resolved_refs=refs,
    )


# Design view_type -> high-level view-spec viewType (the server's wire names).
# Most design names match the wire verbatim; these few are friendlier aliases
# we translate back to what the CLI/server expects.
_VIEW_TYPE_MAP = {"table": "sheet", "kanban": "board", "hierarchy": "structure"}


def _build_view_spec(store: Store, wsid: str, view: dict[str, Any]) -> dict[str, Any]:
    """Compile a design view into the CLI's high-level --view-spec JSON.

    Every field reference is resolved to its real controlId here (the
    store has the worksheet's controlsByName). We resolve ourselves —
    rather than leaning on the CLI's name resolver — because some wire
    slots are JSON strings (e.g. calendar ``calendarcids``) the CLI
    resolver can't reach into.
    """
    rf = lambda name: store.resolve_control(wsid, name)  # noqa: E731

    vt = _VIEW_TYPE_MAP.get(view["view_type"], view["view_type"])
    spec: dict[str, Any] = {"viewType": vt, "name": view["name"]}
    config: dict[str, Any] = {}
    card: dict[str, Any] = {}

    if view.get("group_by"):
        if vt == "sheet":
            spec["group"] = rf(view["group_by"])          # table group-by
        else:
            config["groupField"] = rf(view["group_by"])   # kanban group-by
    if view.get("hierarchy_field"):
        config["relationField"] = rf(view["hierarchy_field"])
        config["childType"] = 1 if view.get("hierarchy_type", "self") == "self" else 2
    if view.get("location"):
        config["locationField"] = rf(view["location"])
    if view.get("dates"):
        config["dates"] = [
            {"startField": rf(d["start"]),
             "endField": rf(d["end"]) if d.get("end") else ""}
            for d in view["dates"]
        ]
    if view.get("start_date"):
        config["startField"] = rf(view["start_date"])
    if view.get("end_date"):
        config["endField"] = rf(view["end_date"])
    if view.get("resource_field"):
        config["resourceField"] = rf(view["resource_field"])
    if view.get("detail_mode"):
        config["mode"] = view["detail_mode"]

    if view.get("cover"):
        card["coverField"] = rf(view["cover"])
        card["coverDirection"] = view.get("cover_direction", "top")
        card["coverDisplayMode"] = view.get("cover_display", "full")
    for src, dst in (("title", "titleField"), ("summary", "summaryField")):
        if (view.get("card") or {}).get(src):
            card[dst] = rf(view["card"][src])
    if (view.get("card") or {}).get("display_fields"):
        card["displayFields"] = [rf(n) for n in view["card"]["display_fields"]]
    if (view.get("card") or {}).get("show_field_names") is not None:
        card["showFieldNames"] = bool(view["card"]["show_field_names"])

    if config:
        spec["config"] = config
    if card:
        spec["card"] = card
    if view.get("filter_list"):
        spec["filterList"] = [rf(n) for n in view["filter_list"]]
    if view.get("filter"):
        def _resolve(fname: str):
            return store.get_control(wsid, fname)
        spec["filters"] = F.build_filter_conditions(view["filter"], _resolve)
    # Surface custom-action buttons in the view's row action column. Custom
    # actions build before views (see compiler), so the btnIds are available.
    if view.get("actions"):
        btn_ids = [store.resolve_custom_action(wsid, a) for a in view["actions"]]
        spec["actions"] = {
            "quickActions": [{"type": "action", "id": b} for b in btn_ids]}
    return spec


def _builtin_all_view_id(wsid: str) -> str:
    """Return the platform auto-created "全部" table view's id (every
    worksheet is born with one), or "" when it's gone/renamed already."""
    data = hap.run(["worksheet", "view", "list", wsid]).data
    views = data if isinstance(data, list) else (
        (data or {}).get("views") or (data or {}).get("data") or [])
    for v in views:
        if v.get("name") in ("全部", "All") and v.get("viewType", 0) == 0:
            return v.get("viewId") or v.get("id") or ""
    return ""


@handler("view")
def _h_view(ctx: ExecCtx, step: Step) -> StepOutcome:
    store = _require_store(ctx)
    host = step.spec["worksheet"]
    view = step.spec["view"]
    wsid = store.resolve("worksheet", host)
    spec = _build_view_spec(store, wsid, view)

    # An unfiltered table view IS the worksheet's "all records" view — and
    # the platform already created one ("全部") with the worksheet. Adopt it
    # in place (rename + configure) instead of creating a duplicate. The
    # schema validator caps unfiltered table views at one per worksheet, and
    # once adopted the built-in name is gone, so adoption happens at most
    # once even on reruns.
    adopted = ""
    if view["view_type"] == "table" and not view.get("filter"):
        adopted = _builtin_all_view_id(wsid)

    if adopted:
        argv = ["worksheet", "view", "update", wsid, adopted,
                "--view-spec", json.dumps(spec, ensure_ascii=False)]
        hap.run(argv)
        view_id = adopted
        data: Any = {"viewId": adopted, "adoptedBuiltinAllView": True}
        summary = (f"view {host}.{view['name']} ({view['view_type']}, "
                   f"adopted built-in 全部)")
    else:
        argv = ["worksheet", "view", "create", wsid, view["name"],
                "--view-spec", json.dumps(spec, ensure_ascii=False)]
        data = hap.run(argv).data
        view_id = _extract_id(data, ["viewId", "id"]) or ""
        summary = f"view {host}.{view['name']} ({view['view_type']})"
    store.put_view(wsid, view_id, view["name"], detail=data)
    return StepOutcome(
        created_id=view_id, summary=summary,
        commands=[argv], capture_files=[f"worksheet_{wsid}.json"],
    )


# v3 globalPermissions requires all 8 boolean keys when provided.
_GLOBAL_PERM_KEYS = ("addRecord", "share", "import", "export", "log",
                     "attachmentDownload", "systemPrint", "discuss")
_WS_ACTION_KEYS = ("shareView", "import", "export", "discuss", "batchOperation")
_RECORD_ACTION_KEYS = ("add", "share", "discuss", "systemPrint",
                       "attachmentDownload", "log")


def _build_ws_perm(store: Store, wp: dict[str, Any]) -> dict[str, Any]:
    """Build one v3 worksheetPermissions item, resolving worksheet/field/
    view logical names to ids and filling required sub-objects.

    fieldPermissions is populated with ALL of the worksheet's fields (the
    design's ``fields`` list provides per-field overrides; the rest get
    full access). The server ignores a worksheet permission whose
    fieldPermissions is empty — so an empty list would silently drop the
    whole entry back to defaults.
    """
    wsid = store.resolve("worksheet", wp["worksheet"])
    ds = wp.get("data_scope", {}) or {}
    actions = wp.get("actions", {}) or {}
    ra = wp.get("record_actions", {}) or {}
    overrides = {f["field"]: f for f in wp.get("fields", []) or []}

    field_perms: list[dict[str, Any]] = []
    for c in store.worksheet_controls(wsid):
        if c.get("type") in (22, 52):  # layout-only controls
            continue
        cid = c.get("controlId") or c.get("id")
        cname = c.get("controlName") or c.get("name")
        if not cid:
            continue
        o = overrides.get(cname, {})
        field_perms.append({
            "id": cid, "read": o.get("read", True), "edit": o.get("edit", True),
            "add": o.get("add", True), "decrypt": o.get("decrypt", False),
        })

    # Populate ALL of the worksheet's views (incl. the default 全部 view),
    # like the UI does — a worksheet permission with an empty view list is
    # treated as uncustomised and falls back to scope defaults. Design
    # ``views`` entries override the matching view by name.
    view_overrides: dict[str, dict[str, Any]] = {}
    for v in wp.get("views", []) or []:
        view_overrides[store.resolve_view(wsid, v["view"])] = v
    view_perms: list[dict[str, Any]] = []
    try:
        vl = hap.run(["worksheet", "view", "list", wsid]).data
        views = vl if isinstance(vl, list) else (vl.get("views") or vl.get("data") or [])
        for v in views:
            vid = v.get("viewId") or v.get("id")
            if not vid:
                continue
            o = view_overrides.get(vid, {})
            view_perms.append({
                "viewId": vid, "read": o.get("read", True),
                "edit": o.get("edit", True), "delete": o.get("delete", True),
            })
    except Exception:  # noqa: BLE001 — best-effort
        view_perms = [
            {"viewId": vid, "read": o.get("read", True),
             "edit": o.get("edit", True), "delete": o.get("delete", True)}
            for vid, o in view_overrides.items()
        ]

    return {
        "id": wsid,
        "recordDataScope": {
            "read": ds.get("read", 100),
            "edit": ds.get("edit", 100),
            "delete": ds.get("delete", 100),
        },
        "worksheetActions": {k: actions.get(k, False) for k in _WS_ACTION_KEYS},
        "recordActions": {k: ra.get(k, False) for k in _RECORD_ACTION_KEYS},
        "paymentActions": {"pay": wp.get("pay", False)},
        "fieldPermissions": field_perms,
        "recordPermissionInViews": view_perms,
    }


@handler("role")
def _h_role(ctx: ExecCtx, step: Step) -> StepOutcome:
    store = _require_store(ctx)
    role = step.spec["role"]
    name = role["name"]
    scope = role["permission_scope"]

    argv = ["app", "role", "create", "-a", ctx.store.app_id,
            "--name", name, "--description", role.get("description", "") or name,
            "--type", "0", "--permission-scope", scope]
    if role.get("hide_app_for_members"):
        argv += ["--hide-app-for-members", "true"]

    if scope != "0" and role.get("global_permissions"):
        gp = {k: role["global_permissions"].get(k, False) for k in _GLOBAL_PERM_KEYS}
        argv += ["--global-permissions-json", json.dumps(gp, ensure_ascii=False)]

    if scope == "0":
        ws_perms = [_build_ws_perm(store, wp)
                    for wp in role.get("worksheet_permissions", []) or []]
        if ws_perms:
            argv += ["--worksheet-permissions-json",
                     json.dumps(ws_perms, ensure_ascii=False)]
        page_perms = [
            {"id": store.resolve("custom_page", p["page"]),
             "enable": p.get("enable", True)}
            for p in role.get("page_permissions", []) or []
        ]
        if page_perms:
            argv += ["--page-permissions-json",
                     json.dumps(page_perms, ensure_ascii=False)]

    data = hap.run(argv).data
    role_id = _extract_id(data, ["id", "roleId"]) or ""
    if not role_id:
        # The role already exists (its create returns no id): recover the
        # real id from the role list so the store
        # keeps a resolvable id instead of an empty one (otherwise every later
        # reference to this role — e.g. an approve node — fails to resolve).
        role_id = _lookup_role_id(ctx.store.app_id, name)
        logger.info("role %r existed; recovered id from list: %r", name, role_id)
    store.put_entity("role", role_id, name, detail=data)

    commands = [argv]
    members = role.get("members") or {}
    if role_id and members:
        m_argv = ["app", "role", "add-member", role_id, "-a", ctx.store.app_id]
        for opt, key in (
            ("--user-ids", "users"), ("--department-ids", "departments"),
            ("--department-tree-ids", "department_trees"),
            ("--job-ids", "jobs"), ("--project-organize-ids", "org_roles"),
        ):
            vals = members.get(key)
            if vals:
                m_argv += [opt, ",".join(vals)]
        if len(m_argv) > 5:  # at least one member option present
            hap.run(m_argv)
            commands.append(m_argv)

    return StepOutcome(
        created_id=role_id, summary=f"role {name!r} scope={scope}",
        commands=commands, capture_files=[f"role_{role_id}.json", "roles.json"],
    )


@handler("optionset")
def _h_optionset(ctx: ExecCtx, step: Step) -> StepOutcome:
    store = _require_store(ctx)
    os_spec = step.spec["optionset"]
    name = os_spec["name"]
    options = []
    for i, o in enumerate(os_spec["options"]):
        opt = {"value": o["value"], "index": o.get("index", i + 1)}
        if "color" in o:
            opt["color"] = o["color"]
        if "score" in o:
            opt["score"] = o["score"]
        options.append(opt)

    argv = ["app", "optionset", "create", "-a", ctx.store.app_id,
            "--name", name, "--options-json", json.dumps(options, ensure_ascii=False)]
    if os_spec.get("enable_color", True):
        argv += ["--enable-color"]
    if os_spec.get("enable_score", False):
        argv += ["--enable-score"]

    data = hap.run(argv).data
    os_id = _extract_id(data, ["optionsetId", "collectionId", "id"]) or ""
    store.put_entity("optionset", os_id, name, detail=data)
    return StepOutcome(
        created_id=os_id, summary=f"optionset {name!r} ({len(options)} options)",
        commands=[argv], capture_files=["optionsets.json"],
    )


@handler("chatbot")
def _h_chatbot(ctx: ExecCtx, step: Step) -> StepOutcome:
    store = _require_store(ctx)
    cb = step.spec["chatbot"]
    name = cb["name"]
    # AddWorkSheet(type=3) requires both org (projectId) and a section.
    if cb.get("section"):
        section_id = store.resolve_section(cb["section"])
    else:
        sections = store.app_meta().get("sections", [])
        if not sections:
            raise RuntimeError("chatbot needs a section but the app has none")
        section_id = sections[0]["id"]

    argv = ["app", "chatbot", "create", ctx.store.app_id, name,
            "--org-id", ctx.org_id, "--section-id", section_id]
    prompt = cb.get("prompt") or cb.get("description") or name
    argv += ["--prompt", prompt]
    if cb.get("description"):
        argv += ["--remark", cb["description"]]
    if cb.get("greeting"):
        argv += ["--welcome-text", cb["greeting"]]
    for q in cb.get("preset_questions", []) or []:
        argv += ["--preset-question", q]

    data = hap.run(argv).data
    cb_id = _extract_id(data, ["chatbotId", "worksheetId", "id"]) or ""
    store.put_entity("chatbot", cb_id, name, detail=data)
    return StepOutcome(
        created_id=cb_id, summary=f"chatbot {name!r}",
        commands=[argv], capture_files=[f"chatbot_{cb_id}.json", "chatbots.json"],
    )


# workflow trigger.type -> startEventAppType (workflow create supports 1/5/6/7).
_TRIGGER_TO_APPTYPE = {
    "record_create": 1, "record_update": 1, "record_create_or_update": 1,
    "scheduled": 5, "date": 6, "webhook": 7,
}
# Worksheet-event trigger -> batch-add --trigger-event value.
_TRIGGER_TO_EVENT = {
    "record_create": "create", "record_update": "update",
    "record_create_or_update": "create_or_update",
}
def _batch_add_inner_pids(ba_data: Any) -> list[str]:
    """Pull inner sub-process / approval-block process ids out of a batch-add
    response (``created[].innerProcessId``) — the reliable source, since a
    published workflow structure does NOT echo a sub_process's inner pid."""
    created = (ba_data or {}).get("created", []) if isinstance(ba_data, dict) else []
    return [c["innerProcessId"] for c in created
            if isinstance(c, dict) and c.get("innerProcessId")]


def _publish_workflow(store, proc_id: str, inner_pids: list[str]) -> list[list[str]]:
    """Publish a workflow. When it contains sub_process / approval_block
    nodes, publish each inner process first (else the server flags the
    container node 103), then the main flow."""
    cmds: list[list[str]] = []
    for inner_pid in inner_pids or []:
        argv = ["workflow", "publish", inner_pid]
        hap.run(argv, check=False)  # best-effort; inner may already be live
        cmds.append(argv)
    argv = ["workflow", "publish", proc_id]
    hap.run(argv)
    cmds.append(argv)
    return cmds


def _add_nodes_and_publish(store, proc_id: str, wsid: str, trigger_node: str,
                           nodes: list[dict[str, Any]]) -> list[list[str]]:
    """Translate + batch-add nodes onto an existing process (the button's
    shadow flow), registering the trigger record under alias ``trigger``,
    then publish (inner processes first). Returns the hap commands run."""
    translated = WD.translate_nodes(store, nodes)
    ba_argv = ["workflow", "node", "batch-add", proc_id,
               "--nodes", json.dumps(translated, ensure_ascii=False),
               "--trigger-node-id", trigger_node, "--trigger-alias", "trigger",
               "--app-id", wsid]
    ba = hap.run(ba_argv)
    return [ba_argv] + _publish_workflow(store, proc_id, _batch_add_inner_pids(ba.data))


@handler("workflow")
def _h_workflow(ctx: ExecCtx, step: Step) -> StepOutcome:
    """Build a workflow's nodes and publish.

    record/scheduled/date triggers create their own process here. A
    ``button`` trigger instead rides the shadow process derived by the
    custom action that points at this workflow (built in the earlier Custom
    actions phase) — the compiler attaches that action as ``trigger_action``.
    """
    store = _require_store(ctx)
    wf = step.spec["workflow"]
    name = wf["name"]
    trig = wf["trigger"]
    trig_type = trig["type"]
    nodes = wf.get("nodes", []) or []

    # ── button-triggered: ride the custom action's shadow process ──────────
    if trig_type == "button":
        action = step.spec.get("trigger_action")
        if not action:
            raise RuntimeError(
                f"button-triggered workflow {name!r} has no custom action "
                f"pointing to it — add a trigger_workflow custom_action whose "
                f"`workflow` is {name!r}.")
        wsid = store.resolve("worksheet", action["worksheet"])
        shadow = store.custom_action_shadow(wsid, action["name"])
        proc_id, trigger_node = shadow["processId"], shadow["triggerNodeId"]
        if not (proc_id and trigger_node):
            raise RuntimeError(
                f"custom action {action['worksheet']}.{action['name']} derived no "
                f"shadow process for workflow {name!r}")
        store.put_entity("workflow", proc_id, name,
                         detail={"shadowOf": action}, summary={"trigger": "button"})
        commands: list[list[str]] = []
        summary = (f"workflow {name!r} (button via "
                   f"{action['worksheet']}.{action['name']})")
        if nodes:
            # The shadow process already exists; adding nodes / publishing it
            # may still fail. Surface proc_id so the failure is repairable in
            # place (don't lose the id behind a generic error).
            try:
                commands += _add_nodes_and_publish(store, proc_id, wsid, trigger_node, nodes)
            except Exception as e:  # noqa: BLE001 — re-raise carrying the id
                raise PartialStepFailure(
                    f"workflow {name!r}: process created but adding nodes / "
                    f"publishing failed: {type(e).__name__}: {e}",
                    created_id=proc_id) from e
            summary += f" + {len(nodes)} nodes, published"
        return StepOutcome(
            created_id=proc_id, summary=summary, commands=commands,
            capture_files=[f"workflow_{proc_id}.json", "workflows.json"])

    # ── record / scheduled / date / webhook: create a new process ──────────
    app_type = _TRIGGER_TO_APPTYPE.get(trig_type)
    if app_type is None:
        raise RuntimeError(
            f"trigger type {trig_type!r} not yet supported by 'workflow create'"
        )

    # Dedup safety net: if a process for this workflow name is already recorded
    # in the store, delete it before recreating so we never pile up duplicate
    # workflows. (`hap workflow create` always makes a NEW process; it never
    # upserts. A clean single-run build has nothing recorded yet, so this is a
    # no-op there; it matters for the custom-action shadow-flow path that may
    # register a name earlier in the same run.)
    prior_id = store.index("workflow").get("byName", {}).get(name)
    if prior_id:
        # Best-effort cleanup — must NEVER abort the build. The prior process
        # may already be gone (a previous rerun deleted it then failed before
        # recreating), and `hap workflow delete` on a missing id can surface
        # an error that hap.run would otherwise raise (incl. a misclassified
        # NotLoggedInError, which fires even with check=False). Swallow all.
        try:
            hap.run(["workflow", "delete", prior_id, "--yes"], check=False)
            logger.info("workflow %r: deleted prior process %s before recreate",
                        name, prior_id)
        except Exception as e:  # noqa: BLE001 — dedup is best-effort
            logger.info("workflow %r: prior process %s not deleted (%s); continuing",
                        name, prior_id, e)

    argv = ["workflow", "create", "-c", ctx.org_id, "-n", name,
            "-a", ctx.store.app_id, "--type", str(app_type)]
    data = hap.run(argv).data
    proc_id = _extract_id(data, ["id", "processId"]) or ""
    if not proc_id:
        raise RuntimeError(f"workflow create returned no processId: {data!r}")

    store.put_entity("workflow", proc_id, name,
                     detail=data, summary={"trigger": trig_type})

    commands = [argv]
    summary = f"workflow {name!r} (trigger={trig_type})"
    nodes = wf.get("nodes", []) or []
    if nodes:
        # The process now exists; everything below (node translation, trigger
        # wiring, batch-add, publish) configures it and may still fail. Wrap so
        # any failure carries proc_id — the run report then marks this workflow
        # "created but not finished" (⚠️) and the id can be repaired in place.
        try:
            translated = WD.translate_nodes(store, nodes)
            ws_name = wf["trigger"].get("worksheet")
            wsid = store.resolve("worksheet", ws_name) if ws_name else ""
            event = _TRIGGER_TO_EVENT.get(trig_type, "create")
            # Register the trigger node under the fixed alias "trigger" so the
            # design DSL can reference the trigger record uniformly via
            # {nodeAlias:"trigger"} / $trigger-工作表/字段$.
            ba_argv = ["workflow", "node", "batch-add", proc_id,
                       "--nodes", json.dumps(translated, ensure_ascii=False),
                       "--trigger-alias", "trigger"]
            if wsid:
                ba_argv += ["--trigger-worksheet", wsid, "--trigger-event", event,
                            "--app-id", wsid]
                # Narrow an update trigger to specific columns: resolve the
                # design's field names to controlIds for assignFieldIds.
                tfields = wf["trigger"].get("fields") or []
                if tfields:
                    cids = [store.resolve_control(wsid, f) for f in tfields]
                    ba_argv += ["--trigger-fields", ",".join(cids)]
                # Trigger filter: only matching records enter the flow.
                if wf["trigger"].get("filter"):
                    tf = WD.translate_filter(store, wf["trigger"]["filter"])
                    ba_argv += ["--trigger-filter", json.dumps(tf, ensure_ascii=False)]
            # Cyclic (定时) trigger: pass the schedule so the appType-5 trigger
            # is configured and the workflow can publish.
            if trig_type == "scheduled" and wf["trigger"].get("schedule"):
                ba_argv += ["--trigger-schedule",
                            json.dumps(wf["trigger"]["schedule"], ensure_ascii=False)]
            # Webhook (appType 7) trigger: POST the design's sample body to the
            # trigger's hook URL so the server derives the inbound param schema.
            if trig_type == "webhook":
                wh = {"sample": wf["trigger"].get("sample") or {}}
                ba_argv += ["--trigger-webhook", json.dumps(wh, ensure_ascii=False)]
            # Date-driven (按日期字段) trigger: resolve the date column name → id.
            if trig_type == "date" and wf["trigger"].get("date_field"):
                dwsid = store.resolve("worksheet", wf["trigger"]["worksheet"])
                dconf = dict(wf["trigger"].get("date_config") or {})
                dconf["worksheet"] = dwsid
                # date_field should be a BARE field name (it is already scoped to
                # the trigger worksheet). Tolerate a stray "工作表名/字段名"
                # prefix by stripping to the last path segment.
                dfield = wf["trigger"]["date_field"]
                if isinstance(dfield, str) and "/" in dfield:
                    dfield = dfield.split("/")[-1]
                dconf["date_field_id"] = store.resolve_control(dwsid, dfield)
                ba_argv += ["--trigger-date", json.dumps(dconf, ensure_ascii=False)]
            ba = hap.run(ba_argv)
            commands.append(ba_argv)
            commands += _publish_workflow(store, proc_id, _batch_add_inner_pids(ba.data))
        except Exception as e:  # noqa: BLE001 — re-raise carrying the id
            raise PartialStepFailure(
                f"workflow {name!r}: process created but configuring / "
                f"publishing failed: {type(e).__name__}: {e}",
                created_id=proc_id) from e
        summary += f" + {len(nodes)} nodes, published"

    return StepOutcome(
        created_id=proc_id, summary=summary,
        commands=commands, capture_files=[f"workflow_{proc_id}.json", "workflows.json"],
    )


# custom-action friendly type -> action_spec_adapter type.
_ACTION_TYPE_MAP = {
    "update_record": "updateCurrentRecord",
    "create_related": "createRelatedRecord",
    "trigger_workflow": "triggerWorkflow",
}


@handler("custom_action")
def _h_custom_action(ctx: ExecCtx, step: Step) -> StepOutcome:
    """Create a custom-action button; optionally build a fully custom
    workflow (any node topology) on its derived shadow flow."""
    store = _require_store(ctx)
    ca = step.spec["custom_action"]
    host = ca["worksheet"]
    name = ca["name"]
    wsid = store.resolve("worksheet", host)

    action_type = _ACTION_TYPE_MAP[ca["type"]]
    spec: dict[str, Any] = {"name": name, "type": action_type}
    if ca["type"] == "update_record":
        spec["updateFields"] = [store.resolve_control(wsid, f) for f in ca.get("update_fields", [])]
    elif ca["type"] == "create_related":
        spec["relationField"] = store.resolve_control(wsid, ca["relation_field"])
    if ca.get("confirm"):
        spec["confirm"] = True
    if ca.get("confirm_msg"):
        spec["confirmMsg"] = ca["confirm_msg"]
    if ca.get("enable_when"):
        # Build the enableWhen gate to wire ourselves (resolving field names
        # against the host worksheet's controls) and pass it as `filters`
        # wire-passthrough — same path as view filters. Ground truth
        # (sources/captured/warehouse-exec-approval-flows/06_*SaveWorksheetBtn.json):
        # an option field (dataType 9) "是其中之一" gate is filterType 2 +
        # values=[optionKey...], NOT the *_FOR_SINGLE 51/52 codes the core
        # action_spec_adapter would emit. Building wire here keeps it correct.
        spec["filters"] = F.build_filter_conditions(
            ca["enable_when"], lambda n: store.get_control(wsid, n))

    argv = ["worksheet", "create-custom-action", wsid,
            "-a", ctx.store.app_id, "--action-spec", json.dumps(spec, ensure_ascii=False)]
    data = hap.run(argv).data
    action_id = _extract_id(data, ["actionId", "id"]) or ""
    process_id = (data or {}).get("processId", "") if isinstance(data, dict) else ""
    trigger_node = (data or {}).get("triggerNodeId", "") if isinstance(data, dict) else ""
    store.put_custom_action(wsid, action_id, name,
                            detail={**(data if isinstance(data, dict) else {}),
                                    "worksheet": host})

    commands = [argv]
    summary = f"action {host}.{name} ({ca['type']})"
    refs: dict[str, Any] = {"processId": process_id, "triggerNodeId": trigger_node}

    # For trigger_workflow the button derives an (empty) shadow process here;
    # its node topology lives in a top-level `button`-triggered workflow that
    # rides this process in the LATER Workflows phase (see _h_workflow). The
    # processId/triggerNodeId captured above (persisted in the action detail)
    # is how that phase finds this shadow flow.
    if ca["type"] == "trigger_workflow":
        if ca.get("workflow"):
            summary += f" -> workflow {ca['workflow']!r}"
        if not (process_id and trigger_node):
            # The button itself was created; only its derived shadow flow is
            # missing. Carry action_id so the failure is repairable in place.
            raise PartialStepFailure(
                f"trigger_workflow button {host}.{name}: button created but "
                f"derived no shadow flow (processId/triggerNodeId missing): "
                f"{data!r}", created_id=action_id)

    return StepOutcome(
        created_id=action_id, summary=summary, commands=commands,
        capture_files=[f"worksheet_{wsid}_custom_action_{action_id}.json"],
        resolved_refs=refs,
    )


def _default_view_id(wsid: str) -> str:
    """Return a worksheet's default (全部) view id for chart binding."""
    data = hap.run(["worksheet", "view", "list", wsid]).data
    views = data if isinstance(data, list) else (data.get("views") or data.get("data") or [])
    if not views:
        return ""
    for v in views:
        if v.get("name") == "全部":
            return v.get("viewId") or v.get("id") or ""
    return views[0].get("viewId") or views[0].get("id") or ""


def _build_page_components(ctx: ExecCtx, comps: list[dict[str, Any]]) -> tuple[list, list]:
    """Create each chart (saveReportConfig) and assemble the page component
    array. Returns (components, hap_commands)."""
    store = ctx.store
    cursor = {"x": 0, "y": 0, "row_h": 0}
    out: list[dict[str, Any]] = []
    commands: list[list[str]] = []
    # chart component name -> {objectId, worksheetId}; filled as charts build,
    # consumed by deferred filter components (they bind charts by objectId).
    chart_map: dict[str, dict[str, str]] = {}
    # (index in `out`, comp spec, resolved layout) for filter components,
    # built in a second pass once chart_map is complete.
    deferred_filters: list[tuple[int, dict[str, Any], dict[str, int]]] = []

    def _layout(comp: dict[str, Any], kind_key: str) -> dict[str, int]:
        w = (comp.get("layout") or {}).get("w") or CH._DEFAULT_W.get(kind_key, 24)
        if comp.get("layout"):
            lay = comp["layout"]
            h = lay.get("h", CH._DEFAULT_H.get(kind_key, 8))
            y = lay.get("y", cursor["y"])
            # honour the explicit layout but advance the cursor below it so
            # subsequent auto-laid components don't overlap.
            cursor.update(x=0, y=y + h, row_h=0)
            return {"x": lay.get("x", 0), "y": y, "w": w, "h": h}
        return CH.auto_layout(kind_key, w, cursor)

    for comp in comps:
        kind = comp["type"]
        if kind == "chart":
            cfg = comp["chart"]
            host = cfg["worksheet"]
            wsid = store.resolve("worksheet", host)
            rtype_int = CH.REPORT_TYPE.get(cfg["report_type"])
            if rtype_int is None:
                raise RuntimeError(f"chart report_type {cfg['report_type']!r} not supported yet")
            filters = None
            # ``filters`` is the plural alias of ``filter`` (same shape; either
            # an array of conditions/groups, or a single condition/group object
            # which build_filter_conditions tolerates).
            chart_filter = cfg.get("filters")
            if chart_filter is None:
                chart_filter = cfg.get("filter")
            if chart_filter:
                filters = F.build_filter_conditions(
                    chart_filter, lambda n, _w=wsid: store.get_control(_w, n))
            spec = CH.chart_spec(
                cfg, view_id=_default_view_id(wsid),
                resolve=lambda n, _w=wsid: store.get_control(_w, n), filters=filters)
            c_argv = ["worksheet", "chart", "create", wsid,
                      "--name", comp.get("name", host),
                      "--report-type", str(rtype_int), "--app-id", ctx.store.app_id,
                      "--spec-json", json.dumps(spec, ensure_ascii=False)]
            rid = _extract_id(hap.run(c_argv).data, ["reportId", "id"]) or ""
            commands.append(c_argv)
            kind_key = "number" if cfg["report_type"] == "number" else "chart"
            cname = comp.get("name", host)
            chart_comp = CH.chart_component(
                report_id=rid, worksheet_id=wsid, name=cname,
                report_type=rtype_int, layout=_layout(comp, kind_key))
            out.append(chart_comp)
            chart_map[cname] = {
                "objectId": chart_comp["config"]["objectId"], "worksheetId": wsid,
                "worksheet": host}
        elif kind == "view":
            v = comp["view"]
            wsid = store.resolve("worksheet", v["worksheet"])
            vid = store.resolve_view(wsid, v["view"]) if v.get("view") else _default_view_id(wsid)
            out.append(CH.view_component(worksheet_id=wsid, view_id=vid,
                                         name=comp.get("name", v["worksheet"]),
                                         layout=_layout(comp, "view")))
        elif kind == "rich_text":
            out.append(CH.rich_text_component(html=comp.get("rich_text", ""),
                                              name=comp.get("name", ""),
                                              layout=_layout(comp, "rich_text")))
        elif kind == "embed_url":
            out.append(CH.embed_url_component(url=comp.get("embed_url", ""),
                                              name=comp.get("name", ""),
                                              layout=_layout(comp, "embed_url")))
        elif kind == "button":
            out.append(CH.button_component(
                button=comp["button"], name=comp.get("name", ""),
                layout=_layout(comp, "button"),
                resolve_ws=lambda n: store.resolve("worksheet", n),
                resolve_view=lambda wid, n: store.resolve_view(wid, n),
                resolve_action=lambda wid, n: store.resolve_custom_action(wid, n)))
        elif kind == "filter":
            # defer: filters bind charts by objectId, so build after all charts.
            deferred_filters.append((len(out), comp, _layout(comp, "filter")))
            out.append(None)  # placeholder, replaced in second pass
        else:
            raise RuntimeError(f"page component type {kind!r} not supported yet")

    for idx, comp, layout in deferred_filters:
        out[idx] = CH.filter_component(
            filter_bar=comp["filter"], name=comp.get("name", ""), layout=layout,
            chart_map=chart_map,
            resolve_control=lambda wid, n: store.get_control(wid, n))
    return out, commands


@handler("custom_page")
def _h_custom_page(ctx: ExecCtx, step: Step) -> StepOutcome:
    store = _require_store(ctx)
    cp = step.spec["custom_page"]
    name = cp["name"]
    argv = ["custom-page", "create", ctx.store.app_id, name]
    if cp.get("section"):
        argv += ["--section-id", store.resolve_section(cp["section"])]
    if cp.get("icon"):
        argv += ["--icon", cp["icon"]]

    data = hap.run(argv).data
    page_id = _extract_id(data, ["pageId", "worksheetId", "id"]) or ""
    store.put_entity("custom_page", page_id, name, detail=data)

    commands = [argv]
    summary = f"custom page {name!r}"
    if cp.get("components"):
        comps, chart_cmds = _build_page_components(ctx, cp["components"])
        commands += chart_cmds
        save_argv = ["custom-page", "save", page_id, "--version", "1",
                     "--components", json.dumps(comps, ensure_ascii=False),
                     "--config", json.dumps({"webNewCols": 48}, ensure_ascii=False),
                     # required when a type=6 filter component is present: lets
                     # the CLI mint the filtersGroupId via SaveFiltersGroup.
                     "--owner-app-id", ctx.store.app_id]
        hap.run(save_argv)
        commands.append(save_argv)
        summary += f" ({len(comps)} components)"

    return StepOutcome(
        created_id=page_id, summary=summary,
        commands=commands, capture_files=[f"custom_page_{page_id}.json", "custom_pages.json"],
    )
