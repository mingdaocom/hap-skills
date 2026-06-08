"""Translate a logical-name workflow node DSL into the id-based DSL that
``hap workflow node batch-add`` consumes.

The scripts design authors workflow nodes by **logical name** (the same
ID-free philosophy as the rest of the framework). This module walks that
DSL and resolves every reference against the captured :class:`Store`:

* worksheet refs (``config.worksheet``)            -> worksheetId
* field refs ``"工作表名/字段名"`` (``fieldId`` everywhere, and the field
  part of ``$alias-工作表名/字段名$`` templates) -> controlId
* option values on option fields (a field patch's ``fieldValue``)
                                                   -> the option key
* role refs in ``accounts``                        -> roleId

Node ``alias`` references (``prev``, ``node.nodeAlias``, the alias part of
``$alias-...$`` templates) are left untouched — ``batch-add`` resolves
alias->nodeId itself at create time.

The produced DSL is the exact shape ``workflow_node_dsl.build_workflow_nodes``
expects (see skills/.../workflow_rules.md).
"""
from __future__ import annotations

import re
from typing import Any

# Field-ref string convention: "工作表名/字段名". System columns and ids pass
# through verbatim.
_SYSTEM_FIELDS = {"rowid", "ownerid", "caid", "ctime", "utime", "uaid"}
_HEX24 = re.compile(r"^[0-9a-f]{24}$")
# $alias-工作表名/字段名$  (alias kept, field part resolved)
_TEMPLATE = re.compile(r"\$([^$]+?)-([^$]+?)\$")


def _collect_formula_actions(nodes: Any) -> dict[str, str]:
    """Map each rollup/compute node's alias -> its formula actionId.

    Needed so a downstream branch/filter condition that compares a rollup
    node's numeric RESULT (e.g. ``count > 0``) can emit the formula-result
    wire (filedId ``number_fx_id``, nodeType 9, appType 11, the node's actionId)
    instead of trying to resolve the author's placeholder fieldId as a control
    (which 500s). Recurses into branch paths and inner processes."""
    out: dict[str, str] = {}

    def visit(nlist: Any) -> None:
        for n in nlist or []:
            if not isinstance(n, dict):
                continue
            alias = n.get("nodeAlias")
            ntype = n.get("nodeType")
            cfg = n.get("config") or {}
            if alias and ntype == "rollup":
                # OBJECT total (105) when aggregating a node's record set;
                # WORKSHEET total (107) when aggregating a worksheet directly.
                out[alias] = "105" if (cfg.get("data_source") or cfg.get("source")) else "107"
            elif alias and ntype == "compute":
                mode = cfg.get("mode", "number")
                out[alias] = {"number": "100", "date": "101",
                              "date_diff": "104", "function": "106"}.get(mode, "100")
            for p in (cfg.get("paths") or []):
                visit(p.get("nodes"))
            visit((cfg.get("process") or {}).get("nodes"))

    visit(nodes)
    return out


class _Resolver:
    def __init__(self, store) -> None:
        self.store = store
        # alias -> formula actionId, for branch/filter conditions that compare a
        # rollup/compute node's numeric result. Populated by translate_nodes.
        self.formula_actions: dict[str, str] = {}

    def _subtable_control(self, parent: str, subfield: str) -> dict[str, Any]:
        """The SubTable/Relation control on ``parent`` named ``subfield``."""
        pwsid = self.store.resolve("worksheet", parent)
        return self.store.get_control(pwsid, subfield) or {}

    def subtable_child_wsid(self, parent: str, subfield: str) -> str:
        """parent worksheet name + subtable field name -> child worksheetId."""
        return self._subtable_control(parent, subfield).get("dataSource") or ""

    def _subtable_field_id(self, parent: str, subfield: str, field: str) -> str:
        """Resolve a column on a subtable to its controlId. The child columns
        are NOT served by ``worksheet fields`` (a subtable has no standalone
        form); they live inline on the parent control as ``relationControls``."""
        if field in _SYSTEM_FIELDS:
            return field
        ctrl = self._subtable_control(parent, subfield)
        for rc in ctrl.get("relationControls") or []:
            if rc.get("controlName") == field or rc.get("controlId") == field:
                return rc.get("controlId") or field
        return field

    def control(self, ref: str) -> str:
        """Resolve a ``"工作表名/字段名"`` field ref to a controlId. Passes
        system columns / already-resolved 24-hex ids through unchanged.
        A 3-part ``"父表/子表字段/子字段"`` ref resolves a subtable column."""
        if not isinstance(ref, str) or ref in _SYSTEM_FIELDS or _HEX24.match(ref):
            return ref
        if "/" not in ref:
            return ref  # unknown bare token — leave for the caller/server
        parts = ref.split("/")
        if len(parts) == 3:  # 父表/子表字段/子字段 -> subtable column
            return self._subtable_field_id(parts[0], parts[1], parts[2])
        ws_name, field = ref.split("/", 1)
        if field in _SYSTEM_FIELDS:
            return field  # "出库单/rowid" -> "rowid" (system column)
        wsid = self.store.resolve("worksheet", ws_name)
        return self.store.resolve_control(wsid, field)

    def control_dict(self, ref: str):
        """Return the full control dict for a ``"工作表名/字段名"`` ref (for
        option-key lookup), or None if not resolvable that way."""
        if not isinstance(ref, str) or "/" not in ref:
            return None
        ws_name, field = ref.split("/", 1)
        try:
            wsid = self.store.resolve("worksheet", ws_name)
            return self.store.get_control(wsid, field)
        except Exception:
            return None

    def worksheet(self, name: str) -> str:
        # "父表名/子表字段名" -> 子表(SubTable/Relation child) 的 worksheetId
        # (its dataSource). Used by get_relation_records over a subtable.
        if "/" in name:
            parent, field = name.split("/", 1)
            wsid = self.store.resolve("worksheet", parent)
            ctrl = self.store.get_control(wsid, field)
            return ctrl.get("dataSource") or wsid
        return self.store.resolve("worksheet", name)

    def role(self, name: str) -> str:
        return self.store.resolve("role", name)

    def template(self, text: str) -> str:
        """Resolve the field part of every ``$alias-工作表名/字段名$`` token,
        keeping the alias for batch-add.

        Special case — a rollup/compute node's RESULT: write ``$别名-结果$``
        (the field part can be 结果/result or the aggregation alias); when the
        alias is a formula node it resolves to the fixed result column
        ``number_fx_id`` (the wire mention ``$<nodeId>-number_fx_id$``)."""
        def _sub(m: "re.Match[str]") -> str:
            alias, field = m.group(1), m.group(2)
            if alias in self.formula_actions:
                return f"${alias}-number_fx_id$"
            return f"${alias}-{self.control(field)}$"
        return _TEMPLATE.sub(_sub, text)


def _option_key(control: dict[str, Any], value: Any) -> Any:
    """Map an option field's display value to its stored key; pass through
    if already a key or not an option field."""
    opts = control.get("options") or []
    if not opts:
        return value
    by_value = {o.get("value"): o.get("key") for o in opts}
    valid_keys = {o.get("key") for o in opts}
    if isinstance(value, list):
        return [by_value.get(v, v) if v not in valid_keys else v for v in value]
    return by_value.get(value, value) if value not in valid_keys else value


def _option_object(control: dict[str, Any], value: Any):
    """For an option field, map a display value (or key) to the FULL option
    object {key,value,isDeleted,score,index} the branch/filter wire wants in
    conditionValues. Non-option fields / unknown values pass through."""
    opts = control.get("options") or []
    if not opts:
        return value

    def _one(v):
        for o in opts:
            if o.get("value") == v or o.get("key") == v:
                return {"key": o.get("key"), "value": o.get("value"),
                        "isDeleted": o.get("isDeleted", False),
                        "score": o.get("score", 0), "index": o.get("index", 0)}
        return v
    return [_one(v) for v in value] if isinstance(value, list) else _one(value)


# Approval-outcome keys (审批结果) for an approval_block result branch.
_APPROVAL_RESULTS = {
    "PASS": "通过", "通过": "通过",
    "OVERRULE": "否决", "否决": "否决",
    "REVOKE": "撤回", "撤回": "撤回",
    "SUSPEND": "中止", "中止": "中止", "已取消": "中止",
}


def _approval_result_object(value: Any):
    """Map an approval outcome (key or label) to the fixed conditionValues
    option object the result-branch wire wants."""
    def _one(v):
        label = _APPROVAL_RESULTS.get(v)
        if label is None:
            return v
        key = next(k for k, lab in _APPROVAL_RESULTS.items()
                   if lab == label and k.isupper())
        return {"key": key, "value": label, "isDeleted": False,
                "score": None, "index": None}
    return [_one(v) for v in value] if isinstance(value, list) else _one(value)


def _is_field_ref(v: Any) -> bool:
    return isinstance(v, str) and "/" in v and not v.startswith("$")


def _condition_item(d: dict[str, Any], r: _Resolver) -> dict[str, Any]:
    """Translate a ``{left, op, right}`` condition item. ``left.fieldId``
    decides whether ``right``'s literal value is an option display value.
    For a branch/filter condition the wire needs the **full option object**
    in conditionValues (not just the key) — translate_condition forwards a
    dict value verbatim. It also enriches the left field with the control's
    type/name so the wire item carries filedTypeId/filedValue."""
    out = {k: _walk(v, r) for k, v in d.items()}
    left = d.get("left") or {}
    left_ref = left.get("fieldId") if isinstance(left, dict) else None
    # Approval-result branch: an approval_block exposes a virtual "result"
    # column (审批结果, filedTypeId 11). Its conditionValues are the fixed
    # approval-outcome option objects, not worksheet options.
    if left_ref == "result":
        new_left = dict(out.get("left") or {})
        new_left["_filedTypeId"] = 11
        new_left["_filedValue"] = "审批结果"
        new_left["_enumDefault"] = 0
        # The source-node metadata the wire expects (审批结果 lives on the
        # approval_block: nodeType 26, appType 10) rides on left.node.
        node_meta = dict(new_left.get("node") or {})
        node_meta["_nodeType"] = 26
        node_meta["_appType"] = 10
        node_meta["_nodeName"] = "审批"
        new_left["node"] = node_meta
        out["left"] = new_left
        right = d.get("right")
        if isinstance(right, dict):
            new_right = dict(out.get("right") or {})
            for vk in ("value", "values"):
                if vk in right:
                    new_right[vk] = _approval_result_object(right[vk])
            out["right"] = new_right
        return out
    # Formula/rollup result branch: comparing a rollup/compute node's numeric
    # RESULT (e.g. count > 0). The wire references the fixed result column
    # ``number_fx_id`` (filedTypeId 6) on the formula node (nodeType 9, appType
    # 11, the node's actionId) — NOT the author's placeholder fieldId.
    left_node_alias = (left.get("node") or {}).get("nodeAlias") if isinstance(left, dict) else None
    if left_node_alias and left_node_alias in r.formula_actions:
        new_left = dict(out.get("left") or {})
        new_left["fieldId"] = "number_fx_id"
        new_left["_filedTypeId"] = 6
        new_left["_filedValue"] = "结果"
        new_left["_enumDefault"] = 0
        node_meta = dict(new_left.get("node") or {})
        node_meta["_nodeType"] = 9
        node_meta["_appType"] = 11
        node_meta["_actionId"] = r.formula_actions[left_node_alias]
        new_left["node"] = node_meta
        out["left"] = new_left
        return out
    ctrl = r.control_dict(left_ref) if _is_field_ref(left_ref) else None
    # System columns (e.g. rowid) aren't controls — give the wire the text
    # metadata it needs so a "记录ID == X" filter doesn't 500.
    if ctrl is None and isinstance(left_ref, str) and left_ref.rsplit("/", 1)[-1] in _SYSTEM_FIELDS:
        new_left = dict(out.get("left") or {})
        new_left["_filedTypeId"] = 2
        new_left["_filedValue"] = left_ref.rsplit("/", 1)[-1]
        new_left["_enumDefault"] = 0
        out["left"] = new_left
    if ctrl is not None:
        # Carry field metadata so hap-cli translate_condition can emit the
        # rich operateCondition (filedTypeId/filedValue/enumDefault).
        new_left = dict(out.get("left") or {})
        new_left["_filedTypeId"] = ctrl.get("type")
        new_left["_filedValue"] = ctrl.get("controlName")
        new_left["_enumDefault"] = ctrl.get("enumDefault", 0)
        out["left"] = new_left
        right = d.get("right")
        if isinstance(right, dict):
            new_right = dict(out.get("right") or {})
            for vk in ("value", "values"):
                if vk in right:
                    new_right[vk] = _option_object(ctrl, right[vk])
            out["right"] = new_right
    return out


def _walk(value: Any, r: _Resolver) -> Any:
    """Recursively translate a DSL fragment. Rules are key-aware so that
    field patches resolve option values, conditions resolve both sides,
    and templates resolve their field parts."""
    if isinstance(value, dict):
        if "left" in value and "op" in value:  # a condition item
            return _condition_item(value, r)
        out: dict[str, Any] = {}
        # Detect a field patch ({fieldId, ... value}) to convert option values.
        patch_ctrl = None
        if "fieldId" in value and _is_field_ref(value.get("fieldId")):
            patch_ctrl = r.control_dict(value["fieldId"])
        for k, v in value.items():
            if k == "fieldId" and isinstance(v, str):
                out[k] = r.control(v)
            elif k == "field" and isinstance(v, str) and "/" in v:
                # A "工作表/字段" ref on a compute/rollup config → controlId.
                out[k] = r.control(v)
            elif k == "worksheet" and isinstance(v, str):
                out[k] = r.worksheet(v)
            elif k in ("fieldValue", "value") and patch_ctrl is not None:
                # A field-write value can be a `$alias-工作表名/字段名$` template
                # pulling from another node (e.g. create_record copying the
                # trigger/get_single record's column). Resolve its field part
                # to a controlId — otherwise the server can't bind it (publish
                # warningType 200). Plain values get option-name -> key mapping.
                if isinstance(v, str) and _TEMPLATE.search(v):
                    out[k] = r.template(v)
                else:
                    out[k] = _option_key(patch_ctrl, v)
            elif k == "valueRef" and isinstance(v, dict):
                # A dynamic field value pulled from another node's column.
                # Resolve the inner fieldId/node, then attach nodeAppId (the
                # source column's worksheet) so a421/update_record can bind it.
                rv = _walk(v, r)
                fref = v.get("fieldId")
                if isinstance(fref, str) and "/" in fref and not _HEX24.match(fref):
                    parts = fref.split("/")
                    try:
                        if len(parts) == 3:
                            rv.setdefault("nodeAppId", r.subtable_child_wsid(parts[0], parts[1]))
                        elif len(parts) == 2 and parts[1] not in _SYSTEM_FIELDS:
                            rv.setdefault("nodeAppId", r.store.resolve("worksheet", parts[0]))
                    except Exception:
                        pass
                out[k] = rv
            elif k in ("accounts", "ccAccounts") and isinstance(v, list):
                out[k] = [_translate_account(a, r) for a in v]
            elif k == "aggregations" and isinstance(v, list):
                # rollup/compute aggregation items: accept friendly lowercase
                # ``aggregate`` (sum/count/...) or ``func`` (any case) and
                # normalise to the wire's uppercase ``func``.
                out[k] = [_normalize_aggregation(a, r) for a in v]
            elif k in ("formula", "content", "body", "subject", "title") and isinstance(v, str):
                out[k] = r.template(v)
            else:
                out[k] = _walk(v, r)
        return out
    if isinstance(value, list):
        return [_walk(v, r) for v in value]
    return value


def _normalize_aggregation(agg: Any, r: _Resolver) -> Any:
    """Normalise a rollup/compute aggregation item to the wire shape.

    Accepts the friendly DSL (``aggregate`` lowercase, as taught for the
    field-level Rollup) or ``func`` in any case, and emits the wire's
    uppercase ``func``. ``fieldId`` (if a "工作表名/字段名" ref) is resolved by
    the generic walk. Missing aggregate defaults to COUNT.
    """
    if not isinstance(agg, dict):
        return _walk(agg, r)
    out = _walk({k: v for k, v in agg.items() if k != "aggregate"}, r)
    func = out.pop("func", None) or agg.get("aggregate") or "count"
    out["func"] = str(func).upper()
    return out


def _translate_account(acct: Any, r: _Resolver) -> Any:
    """Resolve a recipient/approver account to wire-ready logical form.

    - ``kind:role`` → attach roleId + appId (role-name → id).
    - ``kind:field`` (a member/dept/email field on a record) → resolve the
      ``"工作表名/字段名"`` ref to its controlId AND capture the control
      ``controlType`` (26 member / 27 dept / 5 email-text …). The hap-cli
      layer then builds the proper field-recipient wire (entityId=source node,
      roleId=controlId, controlType=…). Without controlType the server can't
      bind the recipient and publish fails warningType 105.
    - other kinds (triggerUser / owner / supervisor / user / email) pass through.
    """
    if isinstance(acct, dict) and acct.get("kind") == "role" and acct.get("role"):
        out = dict(acct)
        out["roleId"] = r.role(acct["role"])
        out["roleName"] = acct["role"]
        # The application id — an approve node's app-role recipient is keyed
        # off it (entityId). cc/notice ignore it.
        out["appId"] = r.store.app_id
        out.pop("role", None)
        return out
    if isinstance(acct, dict) and acct.get("kind") == "field" and acct.get("fieldId"):
        out = dict(acct)
        ref = acct["fieldId"]
        cd = r.control_dict(ref)
        out["fieldId"] = r.control(ref)          # "工作表名/字段名" -> controlId
        if cd and cd.get("type") is not None:
            out["controlType"] = cd.get("type")
        return out
    return _walk(acct, r) if isinstance(acct, (dict, list)) else acct


# Control types that don't belong in a cc/notice card's formProperties.
_NON_CARD_TYPES = {22, 52, 10000001, 10000002, 10000003, 10000004, 10000005}


# Read-only control types — can't be filled in (Lookup/AutoNumber/Formula/
# Rollup/…). In a fill-in form they stay view-only (property 1).
_READONLY_TYPES = {30, 31, 32, 33, 37, 38, 47, 53}


def _form_properties(store, wsid: str, card: bool = True, *,
                     card_fields: "set[str] | None" = None,
                     editable: "set[str] | None" = None,
                     readonly: "set[str] | None" = None,
                     hidden: "set[str] | None" = None) -> list[dict[str, Any]]:
    """Build a ``formProperties`` field list from a worksheet's saved controls.

    ``card=True`` (cc/notice display card) adds ``showType`` and marks every
    field view-only (property 1). ``card=False`` (fill-in / approve editable
    form) omits showType and marks writable fields editable (property 2) — a
    fill node needs at least one editable field or it's flagged 200.

    Per-field role overrides (by control name):
    - ``card_fields``  → ``showCard:1`` (shown on the cc card; default all 0).
    - ``editable``     → ``property:2`` (the approver/filler may change it).
    - ``readonly``     → ``property:1`` (visible, view-only).
    - ``hidden``       → ``property:3`` (not shown at all).
    Override sets win over the card/writable default; precedence
    hidden > editable > readonly.
    """
    card_fields = card_fields or set()
    editable = editable or set()
    readonly = readonly or set()
    hidden = hidden or set()
    props = []
    for c in store.worksheet_controls(wsid):
        t = c.get("type")
        if t in _NON_CARD_TYPES:
            continue
        cid = c.get("controlId") or c.get("id")
        if not cid:
            continue
        name = c.get("controlName") or ""
        if name in hidden:
            prop = 3
        elif name in editable and t not in _READONLY_TYPES:
            prop = 2
        elif name in readonly:
            prop = 1
        else:
            prop = 1 if (card or t in _READONLY_TYPES) else 2
        item = {
            "id": cid, "type": t, "name": name,
            "property": prop, "showCard": 1 if name in card_fields else 0,
            "sectionId": "", "workflow": False, "detailTable": False,
        }
        if card:
            item["showType"] = "3"
        props.append(item)
    return props


_VIEW_CACHE: dict[str, str] = {}


def _default_view_id(wsid: str) -> str:
    """Live-read a worksheet's default (全部) view id (cached). cc/notice
    cards need a viewId or the server drops sendContent/formProperties."""
    if wsid in _VIEW_CACHE:
        return _VIEW_CACHE[wsid]
    from scripts import hap
    try:
        data = hap.run(["worksheet", "view", "list", wsid]).data
    except Exception:
        return ""
    views = data if isinstance(data, list) else (data.get("views") or data.get("data") or [])
    vid = ""
    if isinstance(views, list) and views:
        vid = next((v.get("viewId") or v.get("id") for v in views
                    if v.get("name") == "全部"), None) or \
            views[0].get("viewId") or views[0].get("id") or ""
    _VIEW_CACHE[wsid] = vid
    return vid


# The fixed 本流程参数 (process-parameter) system node id (see hap-cli
# workflow_node_dsl.PROCESS_PARAM_NODE_ID).
_PROCESS_PARAM_NODE_ID = "6038a1cbf18158039fb40e68"


def _new_control_id() -> str:
    import uuid
    return uuid.uuid4().hex[:24]


def _resolve_param_refs(value: Any, name_to_cid: dict[str, str]) -> Any:
    """Replace ``{kind:param,name}`` value-refs (inside a sub-process's inner
    nodes) with a field-ref to the fixed 本流程参数 node + the param's
    controlId, so it behaves like any other field comparison."""
    if isinstance(value, dict):
        if value.get("kind") == "param":
            cid = name_to_cid.get(value.get("name", ""))
            return {"kind": "field", "node": {"nodeId": _PROCESS_PARAM_NODE_ID},
                    "fieldId": cid} if cid else value
        return {k: _resolve_param_refs(v, name_to_cid) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_param_refs(v, name_to_cid) for v in value]
    return value


def _enrich_node(node: dict[str, Any], store) -> None:
    """Post-translate enrichment that needs the store / build-time ids.
    cc/notice nodes get ``formProperties`` + ``viewId``; sub_process nodes
    get param controlIds generated and their inner ``{kind:param}`` refs
    resolved. Recurses into branch paths and nested inner processes."""
    node_type = node.get("nodeType")
    config = node.get("config") or {}
    # get_relation_records (a401): the related rows are reached through a
    # relation/subtable control on the source record. The wire needs that
    # control's id in ``fields`` and the child worksheet as ``appId``.
    if node_type == "get_relation_records":
        rel = config.pop("relation_field", None)
        if isinstance(rel, str) and "/" in rel:
            r = _Resolver(store)
            ctrl_id = r.control(rel)
            parent, field = rel.split("/", 1)
            try:
                pwsid = store.resolve("worksheet", parent)
                child_wsid = (store.get_control(pwsid, field) or {}).get("dataSource")
            except Exception:
                child_wsid = None
            config["fields"] = [{"fieldId": ctrl_id}]
            if child_wsid:
                config["worksheet"] = child_wsid
    # cc(5) renders a record card → needs formProperties + viewId. A plain
    # notice(27) does NOT (it only carries sendContent + recipients); giving
    # it cc-only fields makes the server flag it 103.
    if node_type == "cc" and "formProperties" not in config:
        wsid = config.get("worksheet")
        if wsid:
            config["formProperties"] = _form_properties(
                store, wsid, card_fields=set(config.pop("card_fields", []) or []))
            config.setdefault("viewId", _default_view_id(wsid))
            config.pop("worksheet", None)  # worksheet was only a hint here
    elif node_type == "notice":
        config.pop("worksheet", None)  # notice needs no worksheet/card
    elif node_type == "fill_in" and "formProperties" not in config:
        # The fill-in form shows the record's editable fields (no card showType).
        wsid = config.get("worksheet")
        if wsid:
            config["formProperties"] = _form_properties(
                store, wsid, card=False,
                editable=set(config.pop("editable_fields", []) or []),
                readonly=set(config.pop("readonly_fields", []) or []),
                hidden=set(config.pop("hidden_fields", []) or []))
            config.pop("worksheet", None)
    elif node_type == "approve" and "formProperties" not in config:
        # Approve "可改字段": only build the editable-field list when the design
        # opted in (worksheet + at least one role override). Without it the
        # node keeps the server default (all fields view-only).
        wsid = config.get("worksheet")
        roles = (config.get("editable_fields") or config.get("readonly_fields")
                 or config.get("hidden_fields"))
        if wsid and roles:
            config["formProperties"] = _form_properties(
                store, wsid, card=False,
                editable=set(config.pop("editable_fields", []) or []),
                readonly=set(config.pop("readonly_fields", []) or []),
                hidden=set(config.pop("hidden_fields", []) or []))
        config.pop("worksheet", None)
        config.pop("editable_fields", None)
        config.pop("readonly_fields", None)
        config.pop("hidden_fields", None)
    if node_type == "sub_process":
        process = config.get("process") or {}
        params = process.get("parameters") or []
        name_to_cid = {}
        for p in params:
            cid = p.get("controlId") or _new_control_id()
            p["controlId"] = cid
            name_to_cid[p.get("name", "")] = cid
        if name_to_cid:
            for child in (process.get("nodes") or []):
                child["config"] = _resolve_param_refs(child.get("config") or {}, name_to_cid)
    for path in (config.get("paths") or []):
        for child in (path.get("nodes") or []):
            _enrich_node(child, store)
    inner = (config.get("process") or {}).get("nodes")
    for child in (inner or []):
        _enrich_node(child, store)


def translate_nodes(store, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate a logical-name node DSL list to the id-based DSL.

    Each node keeps ``nodeAlias`` / ``nodeType`` / ``name`` / ``prevNode``;
    its ``config`` (and branch ``paths`` / nested ``process.nodes``) are
    walked recursively, then enriched (cc formProperties). Returns a new
    list (input is not mutated)."""
    r = _Resolver(store)
    r.formula_actions = _collect_formula_actions(nodes)
    out = [_walk(n, r) for n in nodes]
    for n in out:
        _enrich_node(n, store)
    return out


def translate_filter(store, group: dict[str, Any]) -> dict[str, Any]:
    """Translate a logical-name condition group (``{items:[{left,op,right}]}``)
    into the id-resolved, ``_``-hinted form hap-cli's translate_condition_group
    consumes. Used for trigger/standalone filters that aren't node config."""
    return _walk(group, _Resolver(store))
