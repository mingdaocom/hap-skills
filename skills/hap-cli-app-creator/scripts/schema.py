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
    errors.extend(_button_trigger_host_checks(doc))
    return errors


def _button_trigger_host_checks(doc: Any) -> list[str]:
    """A button-triggered workflow's ``trigger`` record IS a record of the
    worksheet its custom action sits on (the *host* worksheet). Every reference
    bound to the reserved ``trigger`` alias therefore addresses a host-worksheet
    field.

    If such a reference carries a ``"<worksheet>/<field>"`` prefix that names a
    DIFFERENT real worksheet, the design is treating the button record as if it
    were that other table's record. The build wires the node against the host
    worksheet but with foreign column ids, so the server rejects publish with
    ``warningType 200`` ("N 个节点未设置有效的操作或操作内容异常") and the whole
    workflow stays unpublished. Schema validation passes (the fields are real,
    just on the wrong table) so this only surfaces mid-build — catch it here.

    To read/update a different worksheet's record from a button flow, add a
    ``create_record`` / ``get_single`` node and bind to THAT node's alias
    instead of ``trigger``.

    Conservative: only flagged when the offending worksheet is a known
    worksheet in the (merged) doc — a workflow-only fragment never false-flags.
    """
    errors: list[str] = []
    if not isinstance(doc, dict):
        return errors
    workflows = doc.get("workflows") or []
    wf_by_name = {w.get("name"): w for w in workflows if isinstance(w, dict)}
    ws_names = {w.get("name") for w in (doc.get("worksheets") or [])
                if isinstance(w, dict)}
    if not ws_names:
        return errors
    # host worksheet per button workflow, via its trigger_workflow custom action.
    host_of: dict[str, str] = {}
    for ca in doc.get("custom_actions") or []:
        if (isinstance(ca, dict) and ca.get("type") == "trigger_workflow"
                and ca.get("workflow") in wf_by_name and ca.get("worksheet")):
            host_of[ca["workflow"]] = ca["worksheet"]

    _trig_tpl_re = re.compile(r'\$trigger-([^/$]+/[^$]+?)\$')

    def _flag(ref: Any, host: str, where: str) -> None:
        if not isinstance(ref, str) or "/" not in ref:
            return
        wsn = ref.partition("/")[0]
        if wsn in ws_names and wsn != host:
            errors.append(
                f"{where}: trigger-bound reference {ref!r} addresses worksheet "
                f"{wsn!r}, but this button workflow's trigger record is a "
                f"{host!r} record (the worksheet its custom action sits on) — "
                f"not a {wsn!r} record. To touch a {wsn!r} record, add a "
                f"create_record/get_single node and bind to that node's alias "
                f"instead of 'trigger'.")

    def _scan(obj: Any, host: str, where: str) -> None:
        if isinstance(obj, dict):
            # update/query target == trigger: its fields[] address the host ws.
            tgt = obj.get("target")
            if (isinstance(tgt, dict) and isinstance(tgt.get("node"), dict)
                    and tgt["node"].get("nodeAlias") == "trigger"):
                for fld in obj.get("fields") or []:
                    if isinstance(fld, dict):
                        _flag(fld.get("fieldId"), host, f"{where}.fields")
            # a field ref read FROM the trigger record: {node:{nodeAlias:trigger},fieldId}
            node = obj.get("node")
            if (isinstance(node, dict) and node.get("nodeAlias") == "trigger"
                    and isinstance(obj.get("fieldId"), str)):
                _flag(obj["fieldId"], host, where)
            for v in obj.values():
                if isinstance(v, str):
                    for m in _trig_tpl_re.findall(v):
                        _flag(m, host, where)
                else:
                    _scan(v, host, where)
        elif isinstance(obj, list):
            for v in obj:
                _scan(v, host, where)

    for name, wf in wf_by_name.items():
        if (wf.get("trigger") or {}).get("type") != "button":
            continue
        host = host_of.get(name)
        if not host:  # no custom action -> _semantic_checks already flags it
            continue
        _scan(wf.get("nodes"), host, f"workflows[{name!r}]")
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


# Node aliases the build executor binds itself (trigger record, sub-process
# iterated record, approval block inner trigger). Mirrors
# hap_cli.core.workflow_node_dsl._RESERVED_NODE_ALIASES.
_RESERVED_NODE_ALIASES = frozenset(
    {"trigger", "sub_trigger", "approval_trigger", "approval_start"})


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

    # Reserved node aliases. The executor binds "trigger" (and the inner-flow
    # names) itself; a node claiming one shadows that binding and every
    # $alias-...$ template / accounts ref / data_source pointing at it
    # resolves to the wrong node — the workflow builds but publish fails
    # (warningType 105/200). Walk nested branch paths and inner processes too.
    def _scan_aliases(nodes: Any, where: str) -> None:
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            alias = node.get("nodeAlias")
            if alias in _RESERVED_NODE_ALIASES:
                errors.append(
                    f"{where}: nodeAlias {alias!r} is reserved (it already "
                    "refers to the trigger/inner-flow record) — drop or "
                    "rename this node's alias")
            cfg = node.get("config") or {}
            if isinstance(cfg, dict):
                process = cfg.get("process")
                if isinstance(process, dict):
                    _scan_aliases(process.get("nodes"),
                                  f"{where}.process")
                for i, path in enumerate(cfg.get("paths") or []):
                    if isinstance(path, dict):
                        _scan_aliases(path.get("nodes"),
                                      f"{where}.paths[{i}]")
    for w in workflows:
        if isinstance(w, dict):
            _scan_aliases(w.get("nodes"), f"workflows[{w.get('name')!r}]")

    # At most ONE unfiltered table view per worksheet: the builder adopts the
    # platform's auto-created "全部" view for it (rename + configure in
    # place); a second one would recreate the duplicate-全部 problem.
    seen_all_view: dict[str, str] = {}
    for v in doc.get("views", []) or []:
        if not isinstance(v, dict):
            continue
        if v.get("view_type") == "table" and not v.get("filter"):
            wsn = v.get("worksheet")
            first = seen_all_view.get(wsn)
            if first:
                errors.append(
                    f"views[{v.get('name')!r}]: worksheet {wsn!r} already has "
                    f"an unfiltered table view ({first!r}); only one is "
                    "allowed — it becomes the worksheet's built-in 全部 view")
            else:
                seen_all_view[wsn] = v.get("name")
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
    # System/built-in field slugs that may appear in a "<ws>/<field>" reference
    # without being declared as a field (mirrors workflow_dsl._SYSTEM_FIELDS).
    _SYSTEM_FIELD_NAMES = {"rowid", "ownerid", "caid", "ctime", "utime", "uaid"}
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
        # Duplicate field names on one worksheet are illegal: build resolves
        # fields/derived-bridges by name, so a second field with the same name
        # shadows the first and a Rollup/workflow that meant the other one
        # silently resolves wrong, then fails mid-build (e.g. two SubTables
        # both named '费用明细' -> a rollup `via:费用明细` hits the wrong one).
        # SubTable children share the same flat name space within their child
        # list, so check those too.
        seen: set = set()
        for f in w.get("fields") or []:
            if not isinstance(f, dict) or not f.get("name"):
                continue
            # Dividers are layout-only section headers, not addressable data
            # fields — a divider is routinely given the same label as the
            # SubTable it introduces (a '订单明细' divider above the '订单明细'
            # SubTable), which is valid and builds fine. Keep them out of both
            # the uniqueness check and the field index.
            if f.get("type") == "Divider":
                continue
            nm = f["name"]
            if nm in seen:
                errors.append(
                    f"worksheets[{w.get('name')!r}]: duplicate field name "
                    f"{nm!r} — field names must be unique within a worksheet")
            seen.add(nm)
            if f.get("type") == "SubTable":
                child_seen: set = set()
                for cf in f.get("child_fields") or []:
                    if (not isinstance(cf, dict) or not cf.get("name")
                            or cf.get("type") == "Divider"):
                        continue
                    cnm = cf["name"]
                    if cnm in child_seen:
                        errors.append(
                            f"worksheets[{w.get('name')!r}].{nm}: duplicate "
                            f"child field name {cnm!r} — child field names "
                            f"must be unique within a SubTable")
                    child_seen.add(cnm)
            fi[nm] = f
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
            # Rollup/Lookup bridge integrity: ``via`` must name a Relation
            # (forward, or a synthesized two_way reverse) or a SubTable ON THIS
            # worksheet, and ``field`` must exist on the bridged target. A via
            # that names a reverse living on ANOTHER worksheet (a common
            # mistake — e.g. 销量总数 via 相关订单 where 相关订单 is 店铺's
            # reverse, not 商品SKU's) resolves to nothing and fails mid-build.
            if f.get("type") in ("Rollup", "Lookup") and wn in field_index and field_index[wn]:
                cfg = f.get("rollup") or f.get("lookup") or {}
                via = cfg.get("via")
                tgt_field = cfg.get("field")
                bridge = field_index[wn].get(via) if via else None
                if via and bridge is None:
                    errors.append(
                        f"{where}: rollup/lookup via {via!r} is not a Relation "
                        f"or SubTable on worksheet {wn!r} — a two_way reverse "
                        f"lives on the TARGET worksheet, not the source")
                elif bridge is not None and tgt_field:
                    if bridge.get("type") == "SubTable":
                        cols = {c.get("name") for c in bridge.get("child_fields") or []
                                if isinstance(c, dict)}
                        if cols and tgt_field not in cols:
                            errors.append(
                                f"{where}: rollup/lookup field {tgt_field!r} not "
                                f"found in SubTable {via!r} (has {sorted(cols)})")
                    elif bridge.get("type") == "Relation":
                        tws = (bridge.get("relation") or {}).get("worksheet")
                        if (tws in field_index and field_index[tws]
                                and tgt_field not in field_index[tws]
                                and tgt_field not in _SYSTEM_FIELD_NAMES):
                            errors.append(
                                f"{where}: rollup/lookup field {tgt_field!r} not "
                                f"found on bridged worksheet {tws!r}")
                    else:
                        errors.append(
                            f"{where}: rollup/lookup via {via!r} must be a "
                            f"Relation or SubTable (is {bridge.get('type')!r})")

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

    # Workflow field-reference integrity. A node references record fields by
    # "<worksheet>/<field>" — either as a ``fieldId`` or inside a
    # ``$trigger-<worksheet>/<field>$`` value literal (the match/value form).
    # If <worksheet> is a real worksheet but <field> doesn't exist on it (and
    # isn't a system field), the build resolves the control to nothing and the
    # workflow fails to publish — e.g. matching on $trigger-消耗记录/耗材库存
    # 编号$ when 消耗记录 has no 耗材库存编号 field (no relation was modelled).
    # Conservative: only flagged when <worksheet> is known AND carries a field
    # index, so a workflow-only fragment or a control-id ref never false-flags.
    _REF_RE = re.compile(r'\$(?:trigger-)?([^$]+?/[^$]+?)\$')

    def _chk_wf_ref(ref: Any, where: str) -> None:
        if not isinstance(ref, str) or "/" not in ref:
            return
        parts = ref.split("/")
        wsn = parts[0]
        # Conservative: only check refs whose worksheet is known and indexed,
        # so a workflow-only fragment or a control-id ref never false-flags.
        if wsn not in field_index or not field_index[wsn]:
            return
        if len(parts) == 2:
            fld = parts[1]
            if (fld and fld not in field_index[wsn]
                    and fld not in _SYSTEM_FIELD_NAMES):
                errors.append(f"{where}: field reference {ref!r} — field "
                              f"{fld!r} not found on worksheet {wsn!r}")
        elif len(parts) == 3:
            # "<worksheet>/<subtable>/<child>" — a SubTable column, resolved
            # at build time by workflow_dsl. Validate the subtable exists and
            # the child column is one of its child_fields (or a system field).
            sub_name, child = parts[1], parts[2]
            sub = field_index[wsn].get(sub_name)
            if not (isinstance(sub, dict) and sub.get("type") == "SubTable"):
                errors.append(f"{where}: field reference {ref!r} — {sub_name!r} "
                              f"is not a SubTable on worksheet {wsn!r}")
                return
            child_names = {cf.get("name") for cf in (sub.get("child_fields") or [])
                           if isinstance(cf, dict)}
            if (child and child not in child_names
                    and child not in _SYSTEM_FIELD_NAMES):
                errors.append(f"{where}: field reference {ref!r} — child field "
                              f"{child!r} not found on SubTable {sub_name!r} of "
                              f"worksheet {wsn!r}")

    def _scan_wf_refs(obj: Any, where: str) -> None:
        if isinstance(obj, dict):
            if isinstance(obj.get("fieldId"), str):
                _chk_wf_ref(obj["fieldId"], where)
            for v in obj.values():
                if isinstance(v, str):
                    for m in _REF_RE.findall(v):
                        _chk_wf_ref(m, where)
                else:
                    _scan_wf_refs(v, where)
        elif isinstance(obj, list):
            for v in obj:
                _scan_wf_refs(v, where)

    for wf in doc.get("workflows") or []:
        if isinstance(wf, dict):
            _scan_wf_refs(wf, f"workflows[{wf.get('name')!r}]")

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
