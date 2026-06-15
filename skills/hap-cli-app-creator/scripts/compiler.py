"""Compile a validated design document into an ordered list of Steps.

Dependency ordering (the heart of breaking cross-sheet cycles)::

    app
    → worksheets        (each created with its INTRA-sheet fields only)
    → relations         (2nd pass: Relation fields, targets now all exist)
    → derived           (3rd pass: Lookup/Rollup, bridge relations exist)
    → custom_actions (buttons; a view/page can surface one, and a
                      trigger_workflow button derives a shadow process)
    → views          (may surface a custom-action button via view.actions)
    → custom_pages   (may embed a button referencing a custom action)
    → chatbots
    → roles          (before workflows: approve nodes reference app roles)
    → workflows      (LAST; button-triggered ones ride the shadow process
                      derived by their custom action above)

Only the phases with a registered handler are emitted; the rest are
added as the corresponding handlers land (see plan §6).
"""
from __future__ import annotations

import re
from typing import Any

from scripts import fields as F
from scripts import steps as S
from scripts.steps import Step

# Phases that already have handlers. Extended as handlers are added.
_ACTIVE_KINDS = set()

_FORMULA_REF = re.compile(r"\$\{([^}]+)\}")


def _emit(steps: list[Step], step: Step) -> None:
    steps.append(step)


def _ordered_derived(worksheets: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Return (worksheet_name, field) for every derived field, sorted so a
    derived field that depends on another derived field comes AFTER it.

    Dependencies (only edges to OTHER derived fields matter):
      * Rollup / Lookup: aggregates ``cfg.field`` on the worksheet reached
        through the bridge ``cfg.via`` (a forward relation or a two-way
        reverse name). If that target column is itself derived -> edge.
      * Formula / DateFormula / Concatenate / FunctionFormula: each
        ``${name}`` references a column on the SAME worksheet; if derived
        -> edge.

    A stable Kahn sort preserves document order among independent fields;
    an unresolvable bridge (e.g. a SubTable child, or a missing name) just
    yields no edge, so the field keeps its document position. A dependency
    cycle (should not happen) degrades gracefully to document order."""
    # relation/reverse name -> target worksheet, per host worksheet
    rel_target: dict[tuple[str, str], str] = {}
    for ws in worksheets:
        for f in ws.get("fields", []) or []:
            if f.get("type") == "Relation" and f.get("relation"):
                rel = f["relation"]
                rel_target[(ws["name"], f["name"])] = rel["worksheet"]
                tw = rel.get("two_way")
                if tw and tw.get("name"):
                    rel_target[(rel["worksheet"], tw["name"])] = ws["name"]

    order: list[tuple[str, str]] = []          # doc order of derived keys
    node: dict[tuple[str, str], dict[str, Any]] = {}
    for ws in worksheets:
        for f in ws.get("fields", []) or []:
            if F.categorize(f) == "derived":
                key = (ws["name"], f["name"])
                node[key] = f
                order.append(key)

    def deps(key: tuple[str, str]) -> set[tuple[str, str]]:
        ws_name, _ = key
        f = node[key]
        out: set[tuple[str, str]] = set()
        cfg = f.get("rollup") or f.get("lookup")
        if cfg and cfg.get("via") and cfg.get("field"):
            tgt = rel_target.get((ws_name, cfg["via"]))
            if tgt and (tgt, cfg["field"]) in node:
                out.add((tgt, cfg["field"]))
        # AmountInWords binds a same-sheet source numeric field; if that
        # source is itself derived (e.g. a Rollup), build it first.
        src = f.get("source")
        if f.get("type") == "AmountInWords" and src and (ws_name, src) in node:
            out.add((ws_name, src))
        formula = f.get("formula")
        if isinstance(formula, str):
            for ref in _FORMULA_REF.findall(formula):
                ref_key = (ws_name, ref.strip())
                if ref_key in node and ref_key != key:
                    out.add(ref_key)
        return out

    dep_map = {k: deps(k) for k in order}
    emitted: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    # Iterate in doc order; emit a field once all its derived deps are out.
    # Repeat passes until fixpoint; any leftovers (cycle) are appended as-is.
    progress = True
    while progress and len(result) < len(order):
        progress = False
        for k in order:
            if k in emitted:
                continue
            if dep_map[k] <= emitted:
                result.append(k)
                emitted.add(k)
                progress = True
    for k in order:                      # cycle fallback: keep doc order
        if k not in emitted:
            result.append(k)
            emitted.add(k)
    return [(ws_name, node[(ws_name, fname)]) for (ws_name, fname) in result]


def _ordered_worksheets(
    worksheets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Order worksheet *creation* so a worksheet that is the target of a
    SubTable child Relation is created BEFORE the worksheet hosting that
    SubTable.

    Top-level Relation fields are built in a deferred second pass, so they
    impose no constraint on creation order. But a SubTable's child Relation
    is baked into the host worksheet at creation time (``steps._wire_subtable
    _child_relations`` resolves the target's worksheetId right then), so the
    target must already exist in the store. The design may declare them in
    any order, so we topologically sort by these child-relation edges.

    A stable fixpoint sort preserves document order among independent
    worksheets; a dependency cycle (or a child relation to an unknown name)
    degrades gracefully to document order — the build then surfaces the same
    clear ResolveError instead of silently misbuilding."""
    names = {ws["name"] for ws in worksheets}

    def child_relation_targets(ws: dict[str, Any]) -> set[str]:
        out: set[str] = set()
        for f in ws.get("fields", []) or []:
            if f.get("type") != "SubTable":
                continue
            for cf in f.get("child_fields", []) or []:
                if cf.get("type") == "Relation":
                    tgt = (cf.get("relation") or {}).get("worksheet")
                    if tgt and tgt in names and tgt != ws["name"]:
                        out.add(tgt)
        return out

    deps = {ws["name"]: child_relation_targets(ws) for ws in worksheets}
    by_name = {ws["name"]: ws for ws in worksheets}
    emitted: set[str] = set()
    result: list[dict[str, Any]] = []
    progress = True
    while progress and len(result) < len(worksheets):
        progress = False
        for ws in worksheets:                # iterate in doc order (stable)
            n = ws["name"]
            if n in emitted:
                continue
            if deps[n] <= emitted:
                result.append(ws)
                emitted.add(n)
                progress = True
    for ws in worksheets:                    # cycle fallback: keep doc order
        if ws["name"] not in emitted:
            result.append(ws)
            emitted.add(ws["name"])
    return result


def compile_design(design: dict[str, Any]) -> list[Step]:
    steps: list[Step] = []

    # 1. app (+ sections)
    _emit(steps, Step(id="app", kind="app", name=design["app"]["name"],
                      phase="App", spec={}))

    worksheets = design.get("worksheets", []) or []

    # 1b. optionsets — created before worksheets so a select field can
    #     bind to a shared collection by logical name.
    for o in design.get("optionsets", []) or []:
        _emit(steps, Step(
            id=f"optionset:{o['name']}", kind="optionset", name=o["name"],
            phase="Optionsets", spec={"optionset": o},
        ))

    # 2. worksheets (intra-sheet fields baked into create). Ordered so a
    #    SubTable child Relation's target worksheet is created first (its id
    #    is resolved at host-worksheet create time). Top-level relations are
    #    deferred below, so they don't constrain this order.
    for ws in _ordered_worksheets(worksheets):
        _emit(steps, Step(
            id=f"worksheet:{ws['name']}", kind="worksheet", name=ws["name"],
            phase="Worksheets", spec={"worksheet": ws},
        ))

    # 3. relations (forward Relation fields — second pass). A two-way
    #    relation creates BOTH halves in its forward step (the forward
    #    carries its reverse as an embedded sourceControl, saved in one
    #    SaveWorksheetControls call). The reverse therefore EXISTS after the
    #    forward step — available to any derived field that bridges through
    #    it. The separate ``relation_reverse`` step is deferred to AFTER the
    #    Derived pass purely to REFRESH the reverse's display columns once
    #    two_way.show_fields pointing at rollup/lookup columns have been
    #    built (BUILD-09); it is a no-op otherwise.
    deferred_reverses: list[Step] = []
    for ws in worksheets:
        for f in ws.get("fields", []) or []:
            if F.categorize(f) != "relation":
                continue
            _emit(steps, Step(
                id=f"relation:{ws['name']}.{f['name']}", kind="relation",
                name=f"{ws['name']}.{f['name']}", phase="Relations",
                spec={"worksheet": ws["name"], "field": f},
            ))
            two_way = (f.get("relation") or {}).get("two_way")
            if not two_way:
                continue
            deferred_reverses.append(Step(
                id=f"relation_reverse:{ws['name']}.{f['name']}",
                kind="relation_reverse",
                name=f"{f['relation']['worksheet']}.{two_way['name']}",
                phase="Reverse relations",
                spec={"worksheet": ws["name"], "field": f},
            ))

    # 4. derived (Lookup/Rollup/Formula — third pass), in DEPENDENCY order so
    #    a derived field that references another derived field builds after it
    #    (BUILD-12: a Rollup-of-Rollup, or a Formula ${ref} to a rollup, failed
    #    when emitted in document order before the column it reads existed).
    for ws_name, f in _ordered_derived(worksheets):
        _emit(steps, Step(
            id=f"derived:{ws_name}.{f['name']}", kind="derived",
            name=f"{ws_name}.{f['name']}", phase="Derived fields",
            spec={"worksheet": ws_name, "field": f},
        ))

    # 4b. deferred reverse relations — built AFTER derived so their
    #     show_fields can surface rollup/lookup columns (BUILD-09).
    for rev_step in deferred_reverses:
        _emit(steps, rev_step)

    # 5. custom actions — emitted BEFORE views/pages/roles/workflows. The
    #    button depends only on worksheets/relations/derived (all above), so
    #    it can come this early. Doing so lets a VIEW surface a custom-action
    #    button (view.actions) and a page embed one (button component), both
    #    of which need the action's btnId; and a `trigger_workflow` button
    #    derives the shadow process its workflow rides in the Workflows phase.
    custom_actions = design.get("custom_actions", []) or []
    for ca in custom_actions:
        label = f"{ca['worksheet']}.{ca['name']}"
        _emit(steps, Step(
            id=f"custom_action:{label}", kind="custom_action", name=label,
            phase="Custom actions", spec={"custom_action": ca},
        ))

    # 6. views (may surface a custom-action button via view.actions).
    for v in design.get("views", []) or []:
        _emit(steps, Step(
            id=f"view:{v['worksheet']}.{v['name']}", kind="view",
            name=f"{v['worksheet']}.{v['name']}", phase="Views",
            spec={"worksheet": v["worksheet"], "view": v},
        ))

    # 7. custom pages (may embed a button that references a custom action).
    for cp in design.get("custom_pages", []) or []:
        _emit(steps, Step(
            id=f"custom_page:{cp['name']}", kind="custom_page", name=cp["name"],
            phase="Custom pages", spec={"custom_page": cp},
        ))

    # 8. chatbots
    for cb in design.get("chatbots", []) or []:
        _emit(steps, Step(
            id=f"chatbot:{cb['name']}", kind="chatbot", name=cb["name"],
            phase="Chatbots", spec={"chatbot": cb},
        ))

    # 9. roles — emitted BEFORE workflows. Top-level workflows (incl. the
    #    button-triggered ones) can have approve / approval-block nodes whose
    #    approvers are app roles (accounts kind="role"); those roles must
    #    already exist so the node DSL can resolve the role name to its id.
    for r in design.get("roles", []) or []:
        _emit(steps, Step(
            id=f"role:{r['name']}", kind="role", name=r["name"],
            phase="Roles", spec={"role": r},
        ))

    # 10. workflows (LAST). record/scheduled/date workflows create their own
    #     process here; a `button`-triggered workflow instead rides the shadow
    #     process derived by the custom action that points at it (built above)
    #     — link each one back to its triggering action so the handler can
    #     find that process. Then nodes are batch-added and published.
    wf_by_name = {wf["name"]: wf for wf in design.get("workflows", []) or []}
    action_for_workflow: dict[str, dict[str, str]] = {}
    for ca in custom_actions:
        if ca.get("type") == "trigger_workflow" and ca.get("workflow"):
            action_for_workflow[ca["workflow"]] = {
                "worksheet": ca["worksheet"], "name": ca["name"]}
    for wf in design.get("workflows", []) or []:
        spec: dict[str, Any] = {"workflow": wf}
        if wf.get("trigger", {}).get("type") == "button":
            spec["trigger_action"] = action_for_workflow.get(wf["name"])
        _emit(steps, Step(
            id=f"workflow:{wf['name']}", kind="workflow", name=wf["name"],
            phase="Workflows", spec=spec,
        ))

    return steps
