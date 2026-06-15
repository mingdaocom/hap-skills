"""Compile design-doc field specs into what the ``hap`` CLI expects.

Two output shapes:

* **Intra-sheet fields** (Text, Number, Select, SubTable, ...) compile to
  the high-level ``--fields`` entry dicts that ``hap worksheet create
  --fields`` / ``update-fields --fields`` accept (each entry is fed
  through ``worksheet_templates.build_control`` by the CLI).
* **Cross-sheet fields** (Relation, Lookup, Rollup) compile to full raw
  ``control`` dicts via ``build_control`` directly, because the second
  pass appends them to the worksheet's already-saved controls and sends
  the combined list through ``update-fields --controls`` (preserving the
  real controlIds of the intra-sheet fields).

This module is pure: it takes already-resolved ids (target worksheetId,
bridge controlId, source controlId), never the store. The executor does
the logical-name -> id resolution and hands the primitives here, which
keeps the compilation unit-testable without a live server.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from scripts._hapmeta import worksheet_templates as wt
from scripts._hapmeta.worksheet_templates import build_auto_id_rule

# relation display label -> advancedSetting.showtype (evidence: pd-openweb
# widgetConfig + sources/captured/save_controls_initial.json).
DISPLAY_TO_SHOWTYPE = {
    "dropdown": "3",
    "card": "1",
    "list": "2",
    "table": "5",
    "tab_table": "6",
}

# Rollup aggregate -> SUBTOTAL enumDefault. Verified from capture
# sources/captured/worksheet-field-rollup. Overridable via extra.enumDefault.
AGGREGATE_TO_ENUMDEFAULT = {
    "avg": 1,
    "max": 2,
    "min": 3,
    "sum": 5,
    "count": 6,
    "distinct_count": 21,
}


def field_permission_str(
    *, hidden: bool = False, readonly: bool = False, hidden_on_create: bool = False
) -> str:
    """Build the 3-char ``fieldPermission`` string.

    Each position is 隐藏 / 只读 / 新增记录时隐藏; the wire convention is
    inverted: ``0`` means the restriction is ON (true), ``1`` means OFF.
    Default (all off) is "111".
    """
    return "{}{}{}".format(
        "0" if hidden else "1",
        "0" if readonly else "1",
        "0" if hidden_on_create else "1",
    )


def field_permission_from(field: dict[str, Any]) -> Optional[str]:
    """Return the fieldPermission string for a field's hidden/readonly/
    hidden_on_create flags, or None when none are set."""
    if not any(k in field for k in ("hidden", "readonly", "hidden_on_create")):
        return None
    return field_permission_str(
        hidden=field.get("hidden", False),
        readonly=field.get("readonly", False),
        hidden_on_create=field.get("hidden_on_create", False),
    )

_CROSS_TYPES = {"Relation", "Lookup", "Rollup"}


def categorize(field: dict[str, Any]) -> str:
    """Return the build phase for a field: intra | relation | derived.

    * ``relation`` (Relation) needs the target worksheet to exist.
    * ``derived`` (Lookup/Rollup) needs a Relation/SubTable on THIS sheet
      to already exist (so it runs after relations).
    * ``intra`` (everything else) is built in the worksheet-create pass.
    """
    t = field.get("type")
    if t == "Relation":
        return "relation"
    # Lookup/Rollup bridge other sheets; Barcode references a same-sheet
    # source field whose real controlId only exists after the worksheet is
    # saved — all are built in the deferred pass.
    if t in ("Lookup", "Rollup", "Barcode", "AmountInWords"):
        return "derived"
    # A CascadingSelect bound to a source worksheet is built after that
    # worksheet (+ its self-relation) exists; a bare one (no cascade) is a
    # plain control built inline.
    if t == "CascadingSelect" and field.get("cascade"):
        return "derived"
    return "intra"


def _auto_number_increase(cfg: dict[str, Any]) -> str:
    """Build the AutoNumber ``increase`` JSON from an auto_number spec."""
    segments: list[Any] = []
    if cfg.get("prefix"):
        segments.append(cfg["prefix"])
    if cfg.get("date_format"):
        segments.append(f"date:{cfg['date_format']}")
    segments.append(("auto", cfg.get("digits", 4), cfg.get("reset", "never")))
    return build_auto_id_rule(*segments)


def intra_field_spec(
    field: dict[str, Any], *, optionset_id: Optional[str] = None
) -> dict[str, Any]:
    """Build a single ``--fields`` entry for a non-cross-sheet field.

    ``optionset_id`` (resolved collectionId) binds a select to a shared
    optionset: the control gets ``dataSource = collectionId`` and no
    inline options.
    """
    spec: dict[str, Any] = {"type": field["type"], "name": field["name"]}
    for key in ("required", "unique", "hint", "size", "is_title", "row", "col"):
        if key in field:
            spec[key] = field[key]
    if field.get("options") is not None:
        spec["options"] = field["options"]
    adv = dict(field.get("advanced_setting", {}))
    if field.get("type") == "AutoNumber" and field.get("auto_number"):
        adv["increase"] = _auto_number_increase(field["auto_number"])
    if adv:
        spec["advanced_setting"] = adv
    extra = dict(field.get("extra", {}))
    if field.get("type") == "Region" and field.get("region_level"):
        # build_control pulls regionLevel out of extra to pick 19/23/24.
        extra["regionLevel"] = field["region_level"]
    if field.get("decimals") is not None:
        # Number/Currency/Formula decimal places live on the control's `dot`.
        extra["dot"] = field["decimals"]
    if optionset_id:
        # Bind a select to a shared optionset collection (no inline options).
        extra["dataSource"] = optionset_id
        spec.pop("options", None)
    perm = field_permission_from(field)
    if perm:
        extra["fieldPermission"] = perm
    if extra:
        spec["extra"] = extra
    if field.get("type") == "SubTable" and field.get("child_fields"):
        spec["child_fields"] = [
            intra_field_spec(cf) for cf in field["child_fields"]
        ]
    return spec


def assign_explicit_cols(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For field specs that pin an explicit ``row``, fill ``col`` with the
    field's slot index within that row (0,1,... by order) so several
    half/quarter-width fields share a row without overlapping.

    Fields without ``row`` are left to the CLI's flow layout.
    """
    counts: dict[int, int] = {}
    for s in specs:
        if "row" in s and "col" not in s:
            r = s["row"]
            s["col"] = counts.get(r, 0)
            counts[r] = counts.get(r, 0) + 1
    return specs


def relation_control(
    name: str,
    *,
    target_worksheet_id: str,
    multi: bool = False,
    display: Optional[str] = None,
    show_control_ids: Optional[list[str]] = None,
    required: bool = False,
    bidirectional: bool = False,
) -> dict[str, Any]:
    """Build a raw RELATE_SHEET control dict for the cross-sheet pass.

    When ``bidirectional`` is set, the server reserves a placeholder
    controlId in this control's ``sourceControlId`` — that placeholder is
    later used as the reverse field's controlId (see
    :func:`reverse_relation_control`).
    """
    adv: dict[str, Any] = {}
    if display:
        adv["showtype"] = DISPLAY_TO_SHOWTYPE[display]
    if bidirectional:
        adv["bidirectional"] = "1"
    return wt.build_control(
        "Relation",
        name,
        data_source=target_worksheet_id,
        multi=multi,
        show_controls=show_control_ids or None,
        advanced_setting=adv or None,
        required=required,
    )


def reverse_relation_control(
    name: str,
    *,
    source_worksheet_id: str,
    forward_control_id: str,
    placeholder_id: str,
    multi: bool = True,
    display: Optional[str] = None,
    show_control_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Build the reverse side of a two-way relation, to be saved on the
    TARGET worksheet.

    HAP pairs the two controls by ids: the reverse control's ``controlId``
    must be the placeholder the forward control reserved in its
    ``sourceControlId``, and the reverse's ``sourceControlId`` points back
    to the forward control's id. (Mechanism verified live — same pattern
    as the SUB_LIST back-relate.)
    """
    ctrl = wt.build_control(
        "Relation",
        name,
        data_source=source_worksheet_id,
        multi=multi,
        show_controls=show_control_ids or None,
        advanced_setting={
            "showtype": DISPLAY_TO_SHOWTYPE[display] if display else ("6" if multi else "3"),
            "bidirectional": "1",
        },
    )
    ctrl["controlId"] = placeholder_id
    ctrl["sourceControlId"] = forward_control_id
    ctrl["sourceControlType"] = 2
    # Auto-created reverse relations default to "hidden on create" so the
    # add-record form isn't cluttered by a back-reference list.
    ctrl["fieldPermission"] = field_permission_str(hidden_on_create=True)
    return ctrl


def bidirectional_relation_control(
    name: str,
    *,
    target_worksheet_id: str,
    host_worksheet_id: str,
    forward_id: str,
    reverse_id: str,
    reverse_name: str,
    multi: bool = False,
    display: Optional[str] = None,
    show_control_ids: Optional[list[str]] = None,
    reverse_display: Optional[str] = None,
    reverse_show_control_ids: Optional[list[str]] = None,
    required: bool = False,
) -> dict[str, Any]:
    """Build a FORWARD relate control that carries its REVERSE half as an
    embedded ``sourceControl`` object.

    Sent in a SINGLE SaveWorksheetControls call on the host worksheet, the
    server creates BOTH halves correctly paired —
    ``forward.sourceControlId == reverse.controlId`` AND
    ``reverse.sourceControlId == forward.controlId`` — and re-mints the
    client placeholder ids to real 24-hex ObjectIds. This mirrors the
    pd-openweb widget-config protocol (verified live).

    Creating the reverse this way, rather than as a separate
    AddWorksheetControls call, is what keeps its back-link from being
    overwritten with a dangling placeholder — the bug that left a
    multi/tab_table reverse blank in the grid until a manual form re-save.

    ``forward_id`` / ``reverse_id`` MUST be dashed uuid4 placeholders: the
    server only re-mints (and pairs) ids it recognises as new, which it
    detects by the ``-`` separators. The reverse half always lists every
    record pointing back, so it is always multi.
    """
    fwd = relation_control(
        name,
        target_worksheet_id=target_worksheet_id,
        multi=multi,
        display=display,
        show_control_ids=show_control_ids,
        required=required,
        bidirectional=True,
    )
    rev = reverse_relation_control(
        reverse_name,
        source_worksheet_id=host_worksheet_id,
        forward_control_id=forward_id,
        placeholder_id=reverse_id,
        multi=True,
        display=reverse_display,
        show_control_ids=reverse_show_control_ids,
    )
    fwd["controlId"] = forward_id
    fwd["sourceControlId"] = reverse_id
    fwd["sourceControlType"] = 2
    fwd["sourceControl"] = rev
    return fwd


def apply_attrs(ctrl: dict[str, Any], field: dict[str, Any]) -> dict[str, Any]:
    """Stamp a cross-sheet control with the field's optional ``size`` (12
    grid), explicit form position, and hidden/readonly/hidden_on_create
    permission. Mutates ctrl.

    Size lets the design pack relations/rollups (e.g. two size-6 rollups
    share a row). An explicit ``row`` (carried via the private ``__row__``
    marker) lets the design place a cross-sheet field anywhere in the form
    instead of always at the bottom — ``_append_controls_pass`` honours it.
    Omitted, the control keeps its type-default width and auto-packs.
    """
    if field.get("size"):
        ctrl["size"] = wt.snap_size(field["size"])
    if "row" in field:
        ctrl["__row__"] = field["row"]
        if "col" in field:
            ctrl["__col__"] = field["col"]
    perm = field_permission_from(field)
    if perm:
        ctrl["fieldPermission"] = perm
    return ctrl


# Back-compat alias.
apply_permission = apply_attrs


# Friendly filter operator -> HAP filterType code (authoritative spec
# FilterTypeEnum). Text/number ops here; option/ref/date specialisations
# are applied in build_filter_conditions by field type.
FILTER_OP_TO_TYPE = {
    "contains": 1, "eq": 2, "startswith": 3, "endswith": 4, "notcontains": 5,
    "ne": 6, "isempty": 7, "isnotempty": 8, "between": 11, "notbetween": 12,
    "gt": 13, "ge": 14, "lt": 15, "le": 16,
    "date_is": 17, "date_is_not": 18, "date_between": 31, "date_not_between": 32,
    "date_gt": 33, "date_ge": 34, "date_lt": 35, "date_le": 36,
    # Friendly aliases: ``is`` == eq; ``in``/``notin`` == 是其中之一/不在其中
    # (values array, same filterType as eq/ne — the HAP UI 用 filterType 2/6 +
    # values 表达「在其中之一」).
    "is": 2, "in": 2, "notin": 6,
}

# Operator aliases normalised before compilation.
_OP_ALIAS = {"is": "eq", "in": "eq", "notin": "ne"}
# Ops that always carry a multi-value ``values`` array (是其中之一/不在其中).
_VALUES_OPS = {"in", "notin"}

# DateRangeEnum (for date_is / date_is_not).
DATE_RANGE = {
    "today": 1, "yesterday": 2, "tomorrow": 3, "this_week": 4, "last_week": 5,
    "next_week": 6, "this_month": 7, "last_month": 8, "next_month": 9,
    "this_quarter": 12, "last_quarter": 13, "next_quarter": 14,
    "this_year": 15, "last_year": 16, "next_year": 17, "custom": 18,
    "last_7_days": 21, "last_14_days": 22, "last_30_days": 23,
    "next_7_days": 31, "next_14_days": 32, "next_33_days": 33,
}

# Control type ids by filter family.
_OPTION_TYPES = {9, 10, 11}            # SingleSelect / MultiSelect / Dropdown
_REF_TYPES = {26, 27, 48, 29, 19, 23, 24, 35}  # member/dept/orgrole/relation/region/cascader
_DATE_TYPES = {15, 16}                 # Date / DateTime
_NO_VALUE_OPS = {"isempty", "isnotempty"}
_RANGE_OPS = {"between", "notbetween", "date_between", "date_not_between"}


def _option_key(control: dict[str, Any], text: str) -> str:
    """Resolve an option's display value -> its stored key on this control.
    Passes ``text`` through if it already looks like a key (no match)."""
    for o in control.get("options", []) or []:
        if o.get("value") == text:
            return o.get("key", text)
    return text


def build_filter_conditions(
    conditions: list[dict[str, Any]],
    resolve,
) -> list[dict[str, Any]]:
    """Build a HAP worksheet filter array from friendly conditions.

    ``resolve(field_name)`` returns the field's full control dict (so we
    can read its type + options). Per the HAP filter spec:
      * Option fields (single/multi/dropdown): the condition value is the
        option's display name; we resolve it to the option KEY and put it
        in ``values`` (array).
      * Reference fields (member/dept/org-role/relation/region): the value
        is a record/member id, put in ``values``; op eq/ne -> RCEq(24)/RCNe(25).
      * Date fields with ``date_range``: filterType DateEnum(17)/NotDateEnum(18)
        + ``dateRange`` (and minValue/maxValue when range=custom).
      * Range ops (between/date_between): minValue/maxValue.
      * Otherwise: single ``value``.
    """
    # Tolerate a single condition/group object passed instead of an array.
    if isinstance(conditions, dict):
        conditions = [conditions]
    out: list[dict[str, Any]] = []
    for c in conditions:
        # ---- condition GROUP (filterGroup: {conditions:[...], join, group_join}) ----
        # Maps to HAP's isGroup:true + groupFilters[] (see SaveWorksheetFilter).
        if isinstance(c, dict) and "conditions" in c and "field" not in c:
            group_join = c.get("group_join", "and")
            inner = build_filter_conditions(
                [{**ic, "join": ic.get("join", group_join)} for ic in c["conditions"]],
                resolve,
            )
            out.append({
                "dataType": 1,
                "spliceType": 2 if c.get("join", "and") == "or" else 1,
                "filterType": 0,
                "dateRange": 0,
                "dateRangeType": 0,
                "isAsc": False,
                "isGroup": True,
                "groupFilters": inner,
            })
            continue

        ctrl = resolve(c["field"])
        cid = ctrl.get("controlId") or ctrl.get("id")
        dtype = c.get("data_type", ctrl.get("type"))
        # Normalise friendly operator aliases (is->eq, in->eq, notin->ne) but
        # remember whether the original op was a multi-value (是其中之一) one.
        raw_op = c["op"]
        multi_value = raw_op in _VALUES_OPS
        op = _OP_ALIAS.get(raw_op, raw_op)
        cond: dict[str, Any] = {
            "controlId": cid,
            "dataType": dtype,
            "spliceType": 2 if c.get("join", "and") == "or" else 1,
            "conditionGroupType": 2,
            "isGroup": False,
        }
        # raw values list from value/values
        raw_vals = c.get("values")
        if raw_vals is None and c.get("value") is not None:
            raw_vals = c["value"] if isinstance(c["value"], list) else [c["value"]]
        raw_vals = raw_vals or []

        if dtype in _OPTION_TYPES and op in ("eq", "ne"):
            ft = 2 if op == "eq" else 6
            cond["values"] = [_option_key(ctrl, str(v)) for v in raw_vals]
        elif dtype in _REF_TYPES and op in ("eq", "ne"):
            ft = 24 if op == "eq" else 25
            cond["values"] = [str(v) for v in raw_vals]
        elif dtype in _DATE_TYPES and c.get("date_range"):
            ft = 17 if op in ("eq", "date_is") else 18
            cond["dateRange"] = DATE_RANGE[c["date_range"]]
            if c["date_range"] == "custom":
                cond["minValue"] = str(c.get("min", ""))
                cond["maxValue"] = str(c.get("max", ""))
        elif op in _RANGE_OPS:
            ft = FILTER_OP_TO_TYPE[op]
            cond["minValue"] = str(c.get("min", ""))
            cond["maxValue"] = str(c.get("max", ""))
        elif multi_value:
            # in/notin on a plain (non-option/ref) field: filterType 2/6 + values.
            ft = 2 if op == "eq" else 6
            cond["values"] = [str(v) for v in raw_vals]
        else:
            ft = FILTER_OP_TO_TYPE[op]
            if op not in _NO_VALUE_OPS:
                cond["value"] = "" if c.get("value") is None else str(c["value"])
        cond["filterType"] = ft
        cond["type"] = ft
        out.append(cond)
    return out


def lookup_control(
    name: str,
    *,
    via_control_id: str,
    source_control_id: str,
    required: bool = False,
) -> dict[str, Any]:
    """Build a raw SHEET_FIELD (他表字段) control dict."""
    return wt.build_control(
        "Lookup",
        name,
        data_source=via_control_id,
        source_control_id=source_control_id,
        required=required,
    )


def barcode_control(
    name: str,
    *,
    source_control_id: str,
    row: Optional[int] = None,
) -> dict[str, Any]:
    """Build a raw BAR_CODE control that encodes a same-sheet source field.

    A barcode can't stand alone — ``enumDefault=1`` + ``dataSource`` =
    the source field's controlId tells HAP which field's value to encode.
    """
    extra: dict[str, Any] = {"enumDefault": 1, "dataSource": source_control_id}
    if row is not None:
        extra["row"] = row
        extra["col"] = 0
    return wt.build_control("Barcode", name, extra=extra)


def cascade_control(
    name: str,
    *,
    source_worksheet_id: str,
    source_entity_name: str,
    show_control_ids: list[str],
    required: bool = False,
) -> dict[str, Any]:
    """Build a CASCADER (级联选择, type 29) bound to a self-referencing source
    worksheet (a parent-child hierarchy table). Wire shape verified from a
    live SaveWorksheetControls capture:
      * dataSource = the source worksheet id
      * sourceEntityName = source worksheet name
      * showControls = which source columns to surface in the picker
      * sourceControl = a companion text control template (server pairs it)
      * sourceControlType = 2, enumDefault = 1, strDefault = "000".
    """
    # In HAP a 级联选择 is wire-wise a RELATE_SHEET (type 29) to the source
    # self-referencing worksheet, rendered as a cascade (advancedSetting
    # showtype=3) with a companion text control (sourceControl) that stores
    # the chosen path. NOT the legacy CASCADER (35).
    source_control = {
        "controlId": "", "controlName": "", "type": 2, "attribute": 0,
        "default": "2", "enumDefault": 2, "enumDefault2": 0,
        "advancedSetting": {"sorttype": "en", "analysislink": "1"},
        "dataSource": "", "sourceControlId": "", "sourceControlType": 0,
        "showControls": [], "options": [], "required": False, "size": 0,
    }
    ctrl = wt.build_control(
        "Relation",
        name,
        data_source=source_worksheet_id,
        multi=False,
        show_controls=show_control_ids or None,
        required=required,
        advanced_setting={
            "allowlink": "1", "searchrange": "1", "scanlink": "1",
            "scancontrol": "1", "showtype": "3", "sorttype": "zh",
            "allowdelete": "1", "allowexport": "1", "allowedit": "1",
            "showquick": "1",
        },
        extra={
            "enumDefault": 1,
            "sourceEntityName": source_entity_name,
            "sourceControlType": 2,
            "strDefault": "000",
            "sourceControl": source_control,
        },
    )
    return ctrl


def amount_in_words_control(
    name: str,
    *,
    source_control_id: str,
) -> dict[str, Any]:
    """Build a MONEY_CN (金额大写, type 25) control bound to a source field.

    Like Barcode it can't stand alone — ``dataSource`` is the source numeric
    field's controlId wrapped in ``$...$`` (verified from a live
    SaveWorksheetControls capture), and ``advancedSetting.currencytype`` picks
    the wording style (0 = 人民币元角分)."""
    return wt.build_control(
        "AmountInWords",
        name,
        extra={"dataSource": f"${source_control_id}$"},
        advanced_setting={"currencytype": "0"},
    )


def rollup_control(
    name: str,
    *,
    via_control_id: str,
    source_control_id: str,
    aggregate: str = "sum",
    required: bool = False,
    filters: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Build a raw SUBTOTAL (汇总) control dict.

    ``aggregate`` -> enumDefault verified from capture. ``filters`` is an
    already-built HAP filter array stored at advancedSetting.filters.
    """
    extra: dict[str, Any] = {"enumDefault": AGGREGATE_TO_ENUMDEFAULT.get(aggregate, 5)}
    adv: dict[str, Any] = {}
    if filters:
        adv["filters"] = json.dumps(filters, ensure_ascii=False)
    ctrl = wt.build_control(
        "Rollup",
        name,
        data_source=via_control_id,
        source_control_id=source_control_id,
        required=required,
        advanced_setting=adv or None,
        extra=extra,
    )
    return ctrl
