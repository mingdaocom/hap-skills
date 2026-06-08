"""Design-document loading + validation against ``design.schema.json``.

The harness is stdlib-only, so rather than depend on the ``jsonschema``
package we ship a small validator covering exactly the draft-07 subset
our schema uses: ``type``, ``properties``, ``required``,
``additionalProperties`` (bool), ``items``, ``enum``, ``const``,
``pattern``, ``minItems``, ``minimum``/``maximum``, ``oneOf``,
``allOf``, ``if``/``then``/``else``, and internal ``$ref``
(``#/$defs/...``).

If a design doc violates the contract, :func:`load_design` raises
:class:`DesignError` listing every problem with its JSON path — caught
before any live API call is made.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from scripts import config
from scripts.errors import DesignError

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    # bool is a subclass of int — exclude it from integer/number.
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class _Validator:
    def __init__(self, root: dict[str, Any]) -> None:
        self.root = root

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
        if not ref.startswith("#/"):
            raise DesignError(f"unsupported $ref (only internal refs): {ref!r}")
        node: Any = self.root
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            node = node[part]
        return node

    def _matches(self, instance: Any, schema: dict[str, Any]) -> bool:
        errs: list[str] = []
        self._check(instance, schema, "", errs)
        return not errs

    def _check(
        self, instance: Any, schema: dict[str, Any], path: str, errors: list[str]
    ) -> None:
        if "$ref" in schema:
            self._check(instance, self._resolve_ref(schema["$ref"]), path, errors)
            return

        # type
        t = schema.get("type")
        if t is not None:
            types = t if isinstance(t, list) else [t]
            if not any(_TYPE_CHECKS[tt](instance) for tt in types):
                errors.append(f"{path or '<root>'}: expected type {t}, got {type(instance).__name__}")
                return  # further keywords assume the type held

        # enum / const
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(f"{path or '<root>'}: {instance!r} not in enum {schema['enum']}")
        if "const" in schema and instance != schema["const"]:
            errors.append(f"{path or '<root>'}: expected const {schema['const']!r}")

        # string pattern
        if isinstance(instance, str) and "pattern" in schema:
            if not re.search(schema["pattern"], instance):
                errors.append(f"{path or '<root>'}: {instance!r} does not match {schema['pattern']!r}")

        # numbers
        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            if "minimum" in schema and instance < schema["minimum"]:
                errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
            if "maximum" in schema and instance > schema["maximum"]:
                errors.append(f"{path}: {instance} > maximum {schema['maximum']}")

        # objects
        if isinstance(instance, dict):
            props: dict[str, Any] = schema.get("properties", {})
            for req in schema.get("required", []):
                if req not in instance:
                    errors.append(f"{path or '<root>'}: missing required property {req!r}")
            addl = schema.get("additionalProperties", True)
            for key, val in instance.items():
                child_path = f"{path}.{key}" if path else key
                if key in props:
                    self._check(val, props[key], child_path, errors)
                elif addl is False:
                    errors.append(f"{path or '<root>'}: unexpected property {key!r}")
                elif isinstance(addl, dict):
                    self._check(val, addl, child_path, errors)

        # arrays
        if isinstance(instance, list):
            if "minItems" in schema and len(instance) < schema["minItems"]:
                errors.append(f"{path}: needs at least {schema['minItems']} items")
            items = schema.get("items")
            if isinstance(items, dict):
                for i, el in enumerate(instance):
                    self._check(el, items, f"{path}[{i}]", errors)

        # combinators
        if "oneOf" in schema:
            n = sum(1 for sub in schema["oneOf"] if self._matches(instance, sub))
            if n != 1:
                errors.append(f"{path or '<root>'}: matched {n} of oneOf (expected exactly 1)")
        if "anyOf" in schema:
            if not any(self._matches(instance, sub) for sub in schema["anyOf"]):
                errors.append(f"{path or '<root>'}: matched none of anyOf")
        for sub in schema.get("allOf", []):
            if "if" in sub:
                if self._matches(instance, sub["if"]):
                    if "then" in sub:
                        self._check(instance, sub["then"], path, errors)
                elif "else" in sub:
                    self._check(instance, sub["else"], path, errors)
            else:
                self._check(instance, sub, path, errors)
        # top-level if/then/else
        if "if" in schema:
            if self._matches(instance, schema["if"]):
                if "then" in schema:
                    self._check(instance, schema["then"], path, errors)
            elif "else" in schema:
                self._check(instance, schema["else"], path, errors)

    def validate(self, instance: Any) -> list[str]:
        errors: list[str] = []
        self._check(instance, self.root, "", errors)
        return errors


def load_schema(path: Optional[Path] = None) -> dict[str, Any]:
    path = path or config.SCHEMA_PATH
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_design(doc: Any, schema: Optional[dict[str, Any]] = None) -> list[str]:
    """Return a list of human-readable validation errors (empty = valid)."""
    schema = schema or load_schema()
    errors = _Validator(schema).validate(doc)
    errors.extend(_semantic_checks(doc))
    errors.extend(_reference_checks(doc))
    return errors


_SINGLE_DISPLAY = {"dropdown", "card"}
_MULTI_DISPLAY = {"tab_table", "card", "list", "table"}
_TABLE_DISPLAY = {"table", "tab_table"}


def _check_relation(where: str, multi: bool, display: Any, show_fields: Any,
                    errors: list[str]) -> None:
    """Validate one relation's display vs cardinality.

    show_fields is optional: for a multi table/tab_table relation the
    executor defaults to the target sheet's first 5 columns when omitted,
    so a missing show_fields is NOT an error.
    """
    ok = _MULTI_DISPLAY if multi else _SINGLE_DISPLAY
    kind = "multi" if multi else "single"
    if display is not None and display not in ok:
        errors.append(f"{where}: display {display!r} invalid for {kind}-record "
                      f"relation (allowed: {sorted(ok)})")


def _semantic_checks(doc: Any) -> list[str]:
    """Cross-field rules the JSON Schema can't express cleanly:

    - relation ``display`` must match cardinality; table/tab_table need
      show_fields (the columns); single relations don't need show_fields.
    - a select field must not carry BOTH inline ``options`` and an
      ``optionset`` reference (shared -> optionset;独占 -> options).
    - two_way reverse display/show_fields validated against the reverse
      cardinality (the reverse half is ALWAYS multi).
    """
    errors: list[str] = []
    if not isinstance(doc, dict):
        return errors
    for ws in doc.get("worksheets", []) or []:
        wsn = ws.get("name")
        for f in ws.get("fields", []) or []:
            fn = f.get("name")
            where = f"worksheets[{wsn!r}].field[{fn!r}]"

            if f.get("options") and f.get("optionset"):
                errors.append(f"{where}: has both options and optionset — pick one "
                              "(shared -> optionset, 独占 -> options)")

            rel = f.get("relation")
            if f.get("type") == "Relation" and isinstance(rel, dict):
                multi = rel.get("multi", False)
                _check_relation(where, multi, rel.get("display"),
                                rel.get("show_fields"), errors)
                tw = rel.get("two_way")
                if isinstance(tw, dict):
                    # The reverse half is ALWAYS multi (the parent/tab_table
                    # side lists every record pointing back). Forward multi
                    # toggles the relationship: false => 1:N, true => M:N
                    # (both halves multi). It is never the "opposite".
                    _check_relation(f"{where}.two_way", True,
                                    tw.get("display"), tw.get("show_fields"), errors)

    # trigger_workflow custom action <-> button-triggered workflow cross-link.
    workflows = doc.get("workflows", []) or []
    wf_by_name = {w.get("name"): w for w in workflows if isinstance(w, dict)}
    button_wf = {n for n, w in wf_by_name.items()
                 if (w.get("trigger") or {}).get("type") == "button"}
    referenced: set[str] = set()
    for ca in doc.get("custom_actions", []) or []:
        if not isinstance(ca, dict) or ca.get("type") != "trigger_workflow":
            continue
        where = f"custom_actions[{ca.get('name')!r}]"
        ref = ca.get("workflow")
        if ref not in wf_by_name:
            errors.append(f"{where}: workflow {ref!r} not found in top-level workflows[]")
        elif ref not in button_wf:
            errors.append(f"{where}: workflow {ref!r} must have trigger.type='button'")
        else:
            if ref in referenced:
                errors.append(f"{where}: workflow {ref!r} is already triggered by "
                              "another custom action (one button per workflow)")
            referenced.add(ref)
    for n in button_wf - referenced:
        errors.append(f"workflows[{n!r}]: trigger.type='button' but no "
                      "trigger_workflow custom action points to it")
    return errors


def _reference_checks(doc: Any) -> list[str]:
    """Cross-object logical-name reference integrity.

    The JSON Schema only checks structure; it can't tell that a page's
    ``section`` actually exists in ``app.sections`` or that a relation points
    at a real worksheet. These references are resolved by logical name at
    build time, so a typo or a forgotten ``sections`` entry only blows up
    mid-build. We catch them here, on the MERGED whole document.

    Conservative on purpose — only worksheet/section/page/optionset-level
    references (never field-level names, which include reverse two_way fields
    that aren't declared as fields).
    """
    errors: list[str] = []
    if not isinstance(doc, dict):
        return errors
    app = doc.get("app") or {}
    sections = set(app.get("sections") or [])
    worksheets = doc.get("worksheets") or []
    ws_names = {w.get("name") for w in worksheets if isinstance(w, dict)}
    optionsets = {o.get("name") for o in (doc.get("optionsets") or [])
                  if isinstance(o, dict)}
    pages = {p.get("name") for p in (doc.get("custom_pages") or [])
             if isinstance(p, dict)}
    # view names defined per worksheet (for embedded-view reference checks)
    views_by_ws: dict[str, set] = {}
    for v in doc.get("views") or []:
        if isinstance(v, dict) and v.get("worksheet") and v.get("name"):
            views_by_ws.setdefault(v["worksheet"], set()).add(v["name"])
    # custom-action names defined per worksheet (a view surfaces its own
    # worksheet's actions via view.actions; checked below). In the split-
    # generation flow the views part and the custom_actions part are authored
    # by different parallel sub-agents, so this catches a naming drift between
    # them at merge/validate time (before build).
    actions_by_ws: dict[str, set] = {}
    for ca in doc.get("custom_actions") or []:
        if isinstance(ca, dict) and ca.get("worksheet") and ca.get("name"):
            actions_by_ws.setdefault(ca["worksheet"], set()).add(ca["name"])

    # field index per worksheet: name -> field dict. Includes the synthesized
    # reverse two_way relation columns (which live on the *target* worksheet
    # but aren't declared there as fields), so cross-object references to them
    # don't false-positive.
    field_index: dict[str, dict[str, dict]] = {}
    for w in worksheets:
        if not isinstance(w, dict):
            continue
        fi = field_index.setdefault(w.get("name"), {})
        for f in w.get("fields") or []:
            if isinstance(f, dict) and f.get("name"):
                fi[f["name"]] = f
    for w in worksheets:
        if not isinstance(w, dict):
            continue
        for f in w.get("fields") or []:
            if not isinstance(f, dict) or f.get("type") != "Relation":
                continue
            tw = (f.get("relation") or {}).get("two_way") or {}
            tgt = (f.get("relation") or {}).get("worksheet")
            if tw.get("name") and tgt in field_index:
                field_index[tgt].setdefault(tw["name"], {
                    "type": "Relation",
                    "relation": {"worksheet": w.get("name")},
                    "_reverse": True,
                })

    # worksheets that have a self-relation (a Relation pointing back to
    # themselves) — required as a CascadingSelect source (parent-child tree).
    self_ref_ws: set = set()
    for w in worksheets:
        if not isinstance(w, dict):
            continue
        for f in w.get("fields") or []:
            if (isinstance(f, dict) and f.get("type") == "Relation"
                    and (f.get("relation") or {}).get("worksheet") == w.get("name")):
                self_ref_ws.add(w.get("name"))

    _DATE_TYPES = {"Date", "DateTime"}

    def chk_field(where: str, ws: str, fname: Any, *, date: bool = False,
                  self_rel: bool = False) -> None:
        """Flag a view/role field reference that can't resolve on ``ws`` (or,
        with date=/self_rel=, has the wrong type). Skips when the worksheet is
        unknown or carries no field index (a fragment validated in isolation)."""
        if not fname or ws not in field_index or not field_index[ws]:
            return
        fld = field_index[ws].get(fname)
        if fld is None:
            errors.append(f"{where}: field {fname!r} not found on worksheet "
                          f"{ws!r}")
            return
        if date and fld.get("type") not in _DATE_TYPES:
            errors.append(f"{where}: field {fname!r} must be a Date/DateTime "
                          f"field (is {fld.get('type')!r})")
        if self_rel:
            rel = fld.get("relation") or {}
            if fld.get("type") != "Relation" or rel.get("worksheet") != ws:
                errors.append(f"{where}: hierarchy_field {fname!r} must be a "
                              f"self-relation (Relation pointing back to "
                              f"{ws!r})")

    def chk_section(where: str, sec: Any) -> None:
        if sec and sections and sec not in sections:
            errors.append(f"{where}: section {sec!r} not in app.sections "
                          f"{sorted(sections)}")

    for w in worksheets:
        if not isinstance(w, dict):
            continue
        wn = w.get("name")
        chk_section(f"worksheets[{wn!r}]", w.get("section"))
        for f in w.get("fields") or []:
            if not isinstance(f, dict):
                continue
            where = f"worksheets[{wn!r}].field[{f.get('name')!r}]"
            os_ref = f.get("optionset")
            if os_ref and optionsets and os_ref not in optionsets:
                errors.append(f"{where}: optionset {os_ref!r} not in "
                              f"optionsets {sorted(optionsets)}")
            rel = f.get("relation")
            if f.get("type") == "Relation" and isinstance(rel, dict):
                tgt = rel.get("worksheet")
                if tgt and tgt not in ws_names:
                    errors.append(f"{where}: relation.worksheet {tgt!r} not "
                                  f"found in worksheets")
            casc = f.get("cascade")
            if f.get("type") == "CascadingSelect" and isinstance(casc, dict):
                src = casc.get("source")
                if src and src not in ws_names:
                    errors.append(f"{where}: cascade.source {src!r} not found "
                                  f"in worksheets")
                elif src and src not in self_ref_ws:
                    errors.append(f"{where}: cascade.source {src!r} must be a "
                                  f"self-referencing (parent-child) worksheet "
                                  f"— add a Relation field on {src!r} pointing "
                                  f"back to {src!r}")
                for sf in casc.get("show_fields") or []:
                    if src in field_index and field_index[src] and sf not in field_index[src]:
                        errors.append(f"{where}: cascade.show_fields {sf!r} not "
                                      f"found on worksheet {src!r}")

    for v in doc.get("views") or []:
        if not isinstance(v, dict):
            continue
        vws = v.get("worksheet")
        if vws and vws not in ws_names:
            errors.append(f"views[{v.get('name')!r}]: worksheet "
                          f"{vws!r} not found in worksheets")
            continue
        # field-level reference + type checks (ISSUE-07/13)
        w = f"views[{v.get('name')!r}]"
        chk_field(f"{w}.group_by", vws, v.get("group_by"))
        chk_field(f"{w}.cover", vws, v.get("cover"))
        chk_field(f"{w}.location", vws, v.get("location"))
        chk_field(f"{w}.start_date", vws, v.get("start_date"), date=True)
        chk_field(f"{w}.end_date", vws, v.get("end_date"), date=True)
        chk_field(f"{w}.resource_field", vws, v.get("resource_field"))
        if v.get("hierarchy_field"):
            chk_field(f"{w}.hierarchy_field", vws, v.get("hierarchy_field"),
                      self_rel=(v.get("hierarchy_type", "self") == "self"))
        for dt in v.get("dates") or []:
            if isinstance(dt, dict):
                chk_field(f"{w}.dates.start", vws, dt.get("start"), date=True)
                chk_field(f"{w}.dates.end", vws, dt.get("end"), date=True)
        card = v.get("card")
        if isinstance(card, dict):
            chk_field(f"{w}.card.title", vws, card.get("title"))
            chk_field(f"{w}.card.summary", vws, card.get("summary"))
            for cf in card.get("display_fields") or []:
                chk_field(f"{w}.card.display_fields", vws, cf)
        for fl in v.get("filter_list") or []:
            chk_field(f"{w}.filter_list", vws, fl)
        # actions surfaced on the view must be custom actions defined on THIS
        # view's worksheet (lenient: only flagged when the worksheet has any
        # custom action defined — so a views-only fragment doesn't false-flag).
        defined_actions = actions_by_ws.get(vws)
        for an in v.get("actions") or []:
            if defined_actions and an not in defined_actions:
                errors.append(
                    f"{w}.actions: custom action {an!r} not defined for "
                    f"worksheet {vws!r} (defined: {sorted(defined_actions)})")

    for ca in doc.get("custom_actions") or []:
        if isinstance(ca, dict) and ca.get("worksheet") and ca["worksheet"] not in ws_names:
            errors.append(f"custom_actions[{ca.get('name')!r}]: worksheet "
                          f"{ca['worksheet']!r} not found in worksheets")

    for p in doc.get("custom_pages") or []:
        if not isinstance(p, dict):
            continue
        chk_section(f"custom_pages[{p.get('name')!r}]", p.get("section"))
        for comp in p.get("components") or []:
            if not isinstance(comp, dict):
                continue
            ch = comp.get("chart")
            if isinstance(ch, dict) and ch.get("worksheet") and ch["worksheet"] not in ws_names:
                errors.append(f"custom_pages[{p.get('name')!r}].component"
                              f"[{comp.get('name')!r}].chart: worksheet "
                              f"{ch['worksheet']!r} not found in worksheets")
            vw = comp.get("view")
            if isinstance(vw, dict) and vw.get("worksheet"):
                if vw["worksheet"] not in ws_names:
                    errors.append(f"custom_pages[{p.get('name')!r}].component"
                                  f"[{comp.get('name')!r}].view: worksheet "
                                  f"{vw['worksheet']!r} not found in worksheets")
                else:
                    # The embedded view name must be a view defined for that
                    # worksheet. When the design declares custom views, the
                    # default '全部' view no longer exists, so referencing it
                    # (or any undeclared name) fails at build (BUILD-10).
                    defined = views_by_ws.get(vw["worksheet"])
                    nm = vw.get("view")
                    if defined and nm and nm not in defined:
                        errors.append(
                            f"custom_pages[{p.get('name')!r}].component"
                            f"[{comp.get('name')!r}].view: view {nm!r} not "
                            f"defined for worksheet {vw['worksheet']!r} "
                            f"(defined: {sorted(defined)})")

    for cb in doc.get("chatbots") or []:
        if isinstance(cb, dict):
            chk_section(f"chatbots[{cb.get('name')!r}]", cb.get("section"))

    for role in doc.get("roles") or []:
        if not isinstance(role, dict):
            continue
        rn = role.get("name")
        for wp in role.get("worksheet_permissions") or []:
            if not isinstance(wp, dict):
                continue
            pws = wp.get("worksheet")
            if pws and pws not in ws_names:
                errors.append(f"roles[{rn!r}].worksheet_permissions: worksheet "
                              f"{pws!r} not found in worksheets")
                continue
            # field-level + view references on this worksheet (ISSUE-08)
            for fperm in wp.get("fields") or []:
                if isinstance(fperm, dict):
                    chk_field(f"roles[{rn!r}].worksheet_permissions[{pws!r}].fields",
                              pws, fperm.get("field"))
            for vperm in wp.get("views") or []:
                if isinstance(vperm, dict) and vperm.get("view"):
                    defined = views_by_ws.get(pws)
                    if defined and vperm["view"] not in defined:
                        errors.append(
                            f"roles[{rn!r}].worksheet_permissions[{pws!r}].views: "
                            f"view {vperm['view']!r} not defined for worksheet "
                            f"{pws!r} (defined: {sorted(defined)})")
        for pp in role.get("page_permissions") or []:
            if isinstance(pp, dict) and pp.get("page") and pages and pp["page"] not in pages:
                errors.append(f"roles[{rn!r}].page_permissions: page "
                              f"{pp['page']!r} not found in custom_pages")

    # Workflow approver/recipient roles must be defined in roles[]. The role can
    # appear deep inside a workflow (approval_block.process.nodes, branch paths,
    # sub_process), so walk the whole workflow recursively for {kind:"role"}.
    role_names = {r.get("name") for r in (doc.get("roles") or [])
                  if isinstance(r, dict)}

    def _scan_roles(obj: Any, where: str) -> None:
        if isinstance(obj, dict):
            if obj.get("kind") == "role" and obj.get("role"):
                if obj["role"] not in role_names:
                    errors.append(f"{where}: references role {obj['role']!r} "
                                  f"({{kind:'role'}}) not defined in roles[] "
                                  f"{sorted(n for n in role_names if n)}")
            for v in obj.values():
                _scan_roles(v, where)
        elif isinstance(obj, list):
            for v in obj:
                _scan_roles(v, where)

    # Only check when the doc actually defines roles — a workflow-only fragment
    # (validated in isolation) has no roles[] to resolve against. The full
    # merged design always carries roles, so the real cross-part case is caught.
    if role_names:
        for wf in doc.get("workflows") or []:
            if isinstance(wf, dict):
                _scan_roles(wf, f"workflows[{wf.get('name')!r}]")

    return errors


def load_design(path: Path, schema: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Load + validate a design document. Raises DesignError on problems."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise DesignError(f"cannot read design {path}: {e}") from e
    errors = validate_design(doc, schema)
    if errors:
        joined = "\n  - ".join(errors)
        raise DesignError(f"design {Path(path).name} failed validation:\n  - {joined}")
    return doc


# Top-level array sections that concatenate when merging multi-part designs.
# (``app`` is the single object section; everything else is a list.)
_MERGE_ARRAY_KEYS = (
    "worksheets", "views", "custom_actions", "custom_pages",
    "chatbots", "workflows", "roles", "optionsets",
)


def merge_designs(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Deep-merge several PARTIAL design docs into one whole.

    For the split-generation workflow: a foundation part (app + optionsets +
    worksheets) plus independent parts (views, roles, workflows+custom_actions,
    pages…) authored separately — often in parallel — and combined here before
    a single ``build``. Cross-part references stay by logical name, so a
    workflow in one part can reference a worksheet in another.

    Rules:
      - ``app``: exactly one part defines it; a second app block with a
        different name is an error (stray/duplicate foundation).
      - array sections: concatenated in part order.
      - duplicate logical names within any section (across parts) raise —
        parts are meant to own disjoint sections.
    """
    merged: dict[str, Any] = {}
    app: Any = None
    for i, part in enumerate(parts):
        if not isinstance(part, dict):
            raise DesignError(f"design part #{i + 1} is not a JSON object")
        for k, v in part.items():
            if k == "app":
                if app is None:
                    app = v
                    merged["app"] = v
                elif (isinstance(v, dict) and isinstance(app, dict)
                      and v.get("name") and v.get("name") != app.get("name")):
                    raise DesignError(
                        f"conflicting 'app' blocks across parts: "
                        f"{app.get('name')!r} vs {v.get('name')!r} — only one "
                        f"part may define 'app'")
            elif k in _MERGE_ARRAY_KEYS:
                if not isinstance(v, list):
                    raise DesignError(f"'{k}' must be an array")
                merged.setdefault(k, []).extend(v)
            else:
                # Unknown top-level key — keep it; the schema validation that
                # runs on the merged doc will reject it if truly invalid.
                merged[k] = v
    if "app" not in merged:
        raise DesignError("no design part defines 'app' (need the foundation part)")
    # Reject duplicate logical names within each merged section.
    for k in _MERGE_ARRAY_KEYS:
        seen: set = set()
        for item in merged.get(k, []):
            name = item.get("name") if isinstance(item, dict) else None
            if name is None:
                continue
            if name in seen:
                raise DesignError(
                    f"duplicate {k} entry named {name!r} across design parts — "
                    f"each part must own distinct {k}")
            seen.add(name)
    return merged


def load_designs(paths: list[Path],
                 schema: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Load one or more design files, merge, validate the WHOLE, and return it.

    A single path behaves exactly like :func:`load_design`. Multiple paths are
    merged via :func:`merge_designs` and the COMBINED document is validated —
    so cross-part logical-name references are checked against the full picture,
    not each fragment in isolation."""
    paths = [Path(p) for p in paths]
    if len(paths) == 1:
        return load_design(paths[0], schema)
    parts: list[dict[str, Any]] = []
    for p in paths:
        try:
            parts.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as e:
            raise DesignError(f"cannot read design {p}: {e}") from e
    doc = merge_designs(parts)
    errors = validate_design(doc, schema)
    if errors:
        joined = "\n  - ".join(errors)
        names = ", ".join(p.name for p in paths)
        raise DesignError(
            f"merged design ({names}) failed validation:\n  - {joined}")
    return doc
