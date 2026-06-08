"""Worksheet field templates and value formatters.

Builds canonical control JSON dicts that match what HAP's
`Worksheet/SaveWorksheetControls` endpoint expects, and formats
record cell values to match what `Worksheet/AddWorksheetRow` and
the V3 `batch_create_records` endpoints expect.

Two sources of truth:
  * pd-openweb `src/pages/widgetConfig/config/widget.js` DEFAULT_DATA
    — per-type default `advancedSetting`/`size`/`enumDefault` etc.
  * Live capture of a SaveWorksheetControls request observed in the
    HAP UI on 2026-05-19 (see sources/captured/INVESTIGATION_NOTES.md).

Server tolerates partial control objects: any key absent is filled
from defaults. We send the minimum necessary so payloads stay
readable.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Iterable, Optional

# ── Field type enum (mirror of pd-openweb WIDGETS_TO_API_TYPE_ENUM) ──────

TYPE = {
    "TEXT": 2,
    "MOBILE_PHONE": 3,
    "TELEPHONE": 4,
    "EMAIL": 5,
    "NUMBER": 6,
    "CRED": 7,
    "MONEY": 8,
    "FLAT_MENU": 9,
    "MULTI_SELECT": 10,
    "DROP_DOWN": 11,
    "ATTACHMENT": 14,
    "DATE": 15,
    "DATE_TIME": 16,
    "AREA_PROVINCE": 19,
    "RELATION": 21,
    "SPLIT_LINE": 22,
    "AREA_CITY": 23,
    "AREA_COUNTY": 24,
    "MONEY_CN": 25,
    "USER_PICKER": 26,
    "DEPARTMENT": 27,
    "SCORE": 28,
    "RELATE_SHEET": 29,
    "SHEET_FIELD": 30,
    "FORMULA_NUMBER": 31,
    "CONCATENATE": 32,
    "AUTO_ID": 33,
    "SUB_LIST": 34,
    "CASCADER": 35,
    "SWITCH": 36,
    "SUBTOTAL": 37,
    "FORMULA_DATE": 38,
    "LOCATION": 40,
    "RICH_TEXT": 41,
    "SIGNATURE": 42,
    "OCR": 43,
    "EMBED": 45,
    "TIME": 46,
    "BAR_CODE": 47,
    "ORG_ROLE": 48,
    "SEARCH_BTN": 49,
    "SEARCH": 50,
    "RELATION_SEARCH": 51,
    "SECTION": 52,
    "FORMULA_FUNC": 53,
    "CUSTOM": 54,
}

# Reverse lookup: int -> "TEXT"
TYPE_NAME = {v: k for k, v in TYPE.items()}


# ── Per-type default templates (port of pd-openweb DEFAULT_DATA) ─────────

# Each entry contributes the minimum keys to satisfy the server when a
# control is created for the first time. Caller-supplied dicts override
# these keys via dict.update().

_DEFAULTS: dict[str, dict[str, Any]] = {
    "TEXT": {"size": 12},
    "MOBILE_PHONE": {
        "size": 6, "hint": "请填写手机号码",
        "advancedSetting": {
            "defaultarea": '{"name":"China (中国)","iso2":"cn","dialCode":"86"}',
        },
    },
    "TELEPHONE": {"size": 6, "hint": "请填写座机号码"},
    "EMAIL": {"size": 6, "hint": "请填写邮箱地址"},
    "NUMBER": {
        "size": 6, "dot": 0, "hint": "请填写数值",
        "advancedSetting": {"showtype": "0", "roundtype": "2", "thousandth": "0"},
    },
    "MONEY": {
        "size": 6, "dot": 2, "enumDefault": 0, "enumDefault2": 2,
        "hint": "请填写金额",
        "advancedSetting": {
            "currency": '{"currencycode":"CNY","symbol":"¥"}',
            "roundtype": "2", "showformat": "1",
        },
    },
    "FLAT_MENU": {"size": 12, "enumDefault2": 0},
    "MULTI_SELECT": {
        "size": 12, "enumDefault2": 0,
        "advancedSetting": {
            "direction": "2", "checktype": "0", "showselectall": "1",
        },
    },
    "DROP_DOWN": {
        "size": 6, "enumDefault2": 0, "hint": "请选择",
        "advancedSetting": {"showtype": "0"},
    },
    "ATTACHMENT": {
        "size": 12, "enumDefault": 3, "hint": "添加附件",
        "advancedSetting": {
            "showtype": "1", "covertype": "0", "alldownload": "1",
            "webcompress": "1", "allowupload": "1", "allowdelete": "1",
            "allowdownload": "1", "allowappupload": "1",
        },
    },
    "DATE": {
        "size": 6, "hint": "请选择日期",
        "advancedSetting": {"showtype": "3", "allowtime": ""},
    },
    "DATE_TIME": {
        "size": 6, "hint": "请选择日期",
        "advancedSetting": {"showtype": "1"},
    },
    "AREA_PROVINCE": {"size": 6, "enumDefault": 0},
    "AREA_CITY": {"size": 6, "advancedSetting": {"chooserange": "CN"}},
    "AREA_COUNTY": {
        "size": 6, "enumDefault": 0, "enumDefault2": 3,
        "advancedSetting": {"chooserange": "CN"},
    },
    "USER_PICKER": {
        "size": 6, "enumDefault": 0, "enumDefault2": 0, "userPermission": 1,
        "noticeItem": 0, "hint": "请选择成员",
        "advancedSetting": {"checkusertype": "1", "usertype": "1"},
    },
    "DEPARTMENT": {
        "size": 6, "enumDefault": 0, "enumDefault2": 0, "userPermission": 1,
        "advancedSetting": {"showdelete": "1", "departrangetype": "0"},
    },
    "ORG_ROLE": {
        "size": 6, "enumDefault": 0, "enumDefault2": 0, "userPermission": 1,
    },
    "SCORE": {"size": 6, "enumDefault": 1, "advancedSetting": {"itemnum": "5", "itemtype": "1"}},
    "RELATE_SHEET": {
        "size": 12, "strDefault": "000", "enumDefault": 1, "enumDefault2": 0,
        "advancedSetting": {
            "allowlink": "1", "searchrange": "1",
            "scanlink": "1", "scancontrol": "1", "showtype": "3",
        },
    },
    "SHEET_FIELD": {
        "size": 6, "enumDefault": 1, "strDefault": "10",
        "advancedSetting": {"sorttype": "en"},
    },
    "CONCATENATE": {
        "size": 12,
        "advancedSetting": {"analysislink": "1", "sorttype": "en"},
    },
    "AUTO_ID": {
        "size": 6, "enumDefault": 0,
        "advancedSetting": {
            "increase": '[{"type":1,"repeatType":0,"start":1,"length":0,"format":""}]',
            "sorttype": "en", "usetimezone": "0",
        },
    },
    "SUB_LIST": {
        "size": 12, "enumDefault": 2, "strDefault": "000",
        "advancedSetting": {
            "allowadd": "1", "allowcancel": "1", "allowedit": "1",
            "allowsingle": "1", "allowexport": "1", "rowheight": "0",
            "enablelimit": "0", "min": "0", "max": "200", "showtype": "1",
            "blankrow": "1", "rownum": "15", "allowlink": "1",
            "allowcopy": "1", "allowimport": "1", "allowbatch": "1",
            "searchrange": "1",
        },
    },
    "SWITCH": {
        "size": 6,
        "advancedSetting": {
            "defsource": '[{"cid":"","rcid":"","staticValue":"0"}]',
            "showtype": "0",
        },
    },
    "SUBTOTAL": {
        "size": 6, "enumDefault": 6, "enumDefault2": 6,
        "advancedSetting": {"roundtype": "2"},
    },
    "FORMULA_NUMBER": {"size": 6, "dot": 2, "advancedSetting": {"roundtype": "2"}},
    "FORMULA_DATE": {"size": 6},
    "FORMULA_FUNC": {"size": 6},
    "LOCATION": {"size": 6},
    "RICH_TEXT": {"size": 12, "advancedSetting": {"defaulttype": "2"}},
    "SIGNATURE": {"size": 6},
    "CASCADER": {"size": 12, "enumDefault": 1},
    "BAR_CODE": {"size": 12, "enumDefault": 1, "advancedSetting": {"width": 160}},
    "TIME": {"size": 6, "unit": "1"},
    "SPLIT_LINE": {
        "size": 12, "enumDefault": 0, "enumDefault2": 1,
        "advancedSetting": {"theme": "#1677ff", "color": "var(--color-text-title)"},
    },
    # Note: HAP's "分段" UI block is type 22 (SPLIT_LINE). type 52
    # (SECTION) is the multi-tab container ("标签页"). Don't confuse.
    "SECTION": {"size": 12},
    "MONEY_CN": {"size": 6},
    "CRED": {"size": 6, "enumDefault": 1, "hint": "请填写身份证"},
}


# ── Public: build a single control dict ─────────────────────────────────


_VALID_SIZES = (3, 6, 12)


def snap_size(size: Any) -> int:
    """Snap an arbitrary column width to the nearest VALID grid width.

    HAP only supports 3 / 6 / 12 (quarter / half / full row). Models keep
    emitting 4, 8, 9, etc.; rather than reject them (churn) or let them break
    the layout, snap to the nearest valid width — ties go to the wider one
    (e.g. 4->3, 5->6, 8->6, 9->12). Non-ints fall back to a full row.
    """
    try:
        n = int(size)
    except (TypeError, ValueError):
        return 12
    if n in _VALID_SIZES:
        return n
    # nearest by absolute distance; on a tie prefer the larger width
    return min(_VALID_SIZES, key=lambda v: (abs(v - n), -v))


def build_control(
    field_type: str | int,
    name: str,
    *,
    row: int = 0,
    col: int = 0,
    size: int | None = None,
    required: bool = False,
    unique: bool = False,
    hint: str | None = None,
    options: list[str] | list[dict[str, Any]] | None = None,
    data_source: str | None = None,
    show_controls: list[str] | None = None,
    relation_controls: list[dict[str, Any]] | None = None,
    child_fields: list[dict[str, Any]] | None = None,
    multi: bool | None = None,
    source_control_id: str | None = None,
    is_title: bool = False,
    extra: dict[str, Any] | None = None,
    advanced_setting: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single control dict ready for SaveWorksheetControls.

    Args:
        field_type: Either the canonical name ("TEXT", "RELATE_SHEET", ...)
            or the integer type id (2, 29, ...). See TYPE.
        name: User-facing column header (controlName).
        row, col: 0-based grid position. `col` is the column within the
            row (0 or 1 for half-width fields, 0 only for full-width).
        size: Column span (12-grid). 6 = half-width, 12 = full-width.
            Defaults to the type's natural width.
        required: Mark as required.
        unique: Forbid duplicate values.
        hint: Placeholder text. None falls back to the type's default hint.
        options: For FLAT_MENU / MULTI_SELECT / DROP_DOWN. Strings expand
            into option dicts with auto-assigned color and key; pass
            full dicts to control checked/color/key explicitly.
        data_source: Type-specific bridge target:
            * RELATE_SHEET: target worksheetId
            * SUB_LIST (mount-existing — rare): target worksheetId
            * SUB_LIST (inline new child — default): omit
            * SHEET_FIELD: the same-sheet RELATE_SHEET's controlId
              (the helper wraps it in "$...$")
            * SUBTOTAL: the same-sheet SUB_LIST/multi-RELATE controlId
              that bridges to the source worksheet (helper wraps
              in "$...$")
            * FORMULA_NUMBER / FORMULA_DATE: literal expression string
              like "$<id>$ * $<id>$" — pass as-is via `extra`
        show_controls: For RELATE_SHEET / SUB_LIST — list of related
            field controlIds to surface in the picker / inline list.
        relation_controls: For SUB_LIST mount-existing mode — the full
            list of target worksheet's existing control dicts (from
            get_worksheet_controls). Triggers the bind handshake.
        child_fields: For SUB_LIST inline-new-child mode (preferred):
            list of *field specs* (same shape as the top-level
            `--fields` items: {type, name, [hint, options,
            data_source, source_control_id, advanced_setting, extra]}).
            The helper recursively builds each child control with a
            client UUID and packs them as `relationControls`. HAP
            creates a new child worksheet on first save.
        multi: For RELATE_SHEET, True = multi-record (enumDefault=2,
            inline-card list rendering) vs False = single (enumDefault=1,
            dropdown). Defaults to False. For SUB_LIST, ignored (always
            multi by definition).
        source_control_id: For SHEET_FIELD: controlId of the column on
            the target worksheet whose value to mirror. For SUBTOTAL:
            controlId of the column on the bridge's target worksheet
            to aggregate. The frontend persists these as the control's
            `sourceControlId`.
        is_title: Mark this as the worksheet's title field (only one
            allowed per sheet; backend uses `attribute: 1`).
        extra: Free-form overrides merged on top, for niche cases that
            the helper doesn't model.
        advanced_setting: Dict merged on top of the type default's
            `advancedSetting`. Use string values (HAP stringifies most
            settings even when they look numeric).
    """
    if isinstance(field_type, int):
        type_id = field_type
        type_name = TYPE_NAME.get(field_type, "")
    else:
        # Accept either:
        #   • the existing SCREAMING_SNAKE_CASE template names ("TEXT")
        #   • the hap-app-builder PascalCase CODE names ("Text") — the
        #     vocabulary the new skill emits.
        # CODE takes precedence: if the input matches a builder CODE we
        # translate via control_type_codes; otherwise we fall back to
        # the legacy uppercase template form.
        from scripts._hapmeta import control_type_codes as _codes
        if field_type in _codes.CODE_TO_TEMPLATE_NAME:
            # ``extra`` may carry regionLevel for the only one-to-many
            # CODE ("Region"). Pull it out without disturbing other extras.
            region_level: Optional[str] = None
            if extra and "regionLevel" in extra:
                extra = dict(extra)
                region_level = extra.pop("regionLevel")
            type_name = _codes.code_to_template_name(field_type, region_level)
        else:
            type_name = field_type.upper()
        if type_name not in TYPE:
            raise ValueError(f"Unknown field type: {field_type}")
        type_id = TYPE[type_name]

    defaults = _DEFAULTS.get(type_name, {})
    ctrl: dict[str, Any] = {
        "controlId": _new_control_id(),
        "controlName": name,
        "type": type_id,
        "row": row,
        "col": col,
        "required": required,
        "unique": unique,
    }
    # merge non-advancedSetting defaults
    for k, v in defaults.items():
        if k == "advancedSetting":
            continue
        ctrl.setdefault(k, v)
    # advancedSetting merge
    adv = dict(defaults.get("advancedSetting", {}))
    if advanced_setting:
        adv.update(advanced_setting)
    if adv:
        ctrl["advancedSetting"] = adv
    if hint is not None:
        ctrl["hint"] = hint
    if is_title:
        ctrl["attribute"] = 1
    # TEXT: 1=multiline, 2=single-line. Default to single-line unless caller overrode.
    if type_name == "TEXT" and "enumDefault" not in ctrl:
        ctrl["enumDefault"] = 2

    if size is not None:
        ctrl["size"] = snap_size(size)

    # options (FLAT_MENU / MULTI_SELECT / DROP_DOWN)
    if options is not None and type_name in ("FLAT_MENU", "MULTI_SELECT", "DROP_DOWN"):
        ctrl["options"] = _normalize_options(options)

    # RELATE_SHEET — single or multi
    if type_name == "RELATE_SHEET":
        if data_source is None:
            raise ValueError("RELATE_SHEET requires data_source (target worksheetId)")
        ctrl["dataSource"] = data_source
        if multi:
            ctrl["enumDefault"] = 2
            # Multi-RELATE renders as an inline list-of-cards by
            # default (UI uses showtype 6). Caller can override via
            # advanced_setting={"showtype": "..."}.
            ctrl["advancedSetting"].setdefault("showtype", "6")
        if show_controls:
            ctrl["showControls"] = show_controls

    # SUB_LIST — three modes:
    #   1. INLINE NEW CHILD (default, recommended). Pass `child_fields`
    #      — a list of field specs. The helper recursively builds each
    #      and packs them as `relationControls`. `dataSource` is a
    #      fresh client UUID that HAP turns into the new child
    #      worksheet's id on first save. Strong parent/child semantic:
    #      child rows are deleted when the parent row is deleted.
    #   2. INLINE FROM RAW CONTROL DICTS. Pass `relation_controls` (no
    #      `data_source`). Same semantic as (1) but caller supplies
    #      already-built control dicts. Useful when porting from an
    #      existing schema.
    #   3. MOUNT EXISTING worksheet (advanced). Pass `data_source` =
    #      existing worksheetId AND `relation_controls` = the target
    #      worksheet's controls (from get_worksheet_controls). Then
    #      call bind_sub_list_to_back_relate() AFTER the parent is
    #      saved to wire up the auto-display. Prefer modes (1)/(2)
    #      when you don't need standalone access to the child rows.
    if type_name == "SUB_LIST":
        if child_fields and relation_controls:
            raise ValueError(
                "SUB_LIST: pass either child_fields (high-level specs) "
                "or relation_controls (raw dicts), not both."
            )
        # Always multi
        ctrl["enumDefault"] = 2
        # SUB_LIST is always full-width by HAP convention
        ctrl.setdefault("size", 12)
        ctrl["size"] = 12

        # Build inline child controls if child_fields supplied
        if child_fields:
            built = []
            for i, spec in enumerate(child_fields):
                spec = dict(spec)
                child_type = spec.pop("type")
                child_name = spec.pop("name")
                built.append(build_control(
                    child_type, child_name, row=i, col=0, **spec,
                ))
            relation_controls = built

        if data_source:
            # mount-existing (mode 3)
            ctrl["dataSource"] = data_source
        else:
            # inline new child (mode 1/2) — fresh UUID placeholder
            ctrl["dataSource"] = str(uuid.uuid4())

        if relation_controls:
            ctrl["relationControls"] = relation_controls
            visible_ids = (show_controls or
                           [c["controlId"] for c in relation_controls
                            if c.get("type") not in (22, 52)])
            ctrl["showControls"] = visible_ids
            ctrl["advancedSetting"]["controlssorts"] = json.dumps(
                visible_ids, ensure_ascii=False,
            )
        elif show_controls:
            ctrl["showControls"] = show_controls

        # The UI omits these on SUB_LIST. Sending them flips HAP into
        # a different storage mode that breaks parent/child semantics.
        for k in ("attribute", "enumDefault2", "sourceControlId"):
            ctrl.pop(k, None)

    # SHEET_FIELD (他表字段) — bridge through a same-sheet RELATE_SHEET
    if type_name == "SHEET_FIELD":
        if data_source is None or source_control_id is None:
            raise ValueError(
                "SHEET_FIELD requires data_source (controlId of the "
                "same-sheet RELATE_SHEET bridge) AND source_control_id "
                "(controlId of the target column on the related worksheet)."
            )
        # Wrap in $...$ unless caller already did so
        ctrl["dataSource"] = data_source if data_source.startswith("$") else f"${data_source}$"
        ctrl["sourceControlId"] = source_control_id

    # SUBTOTAL — bridge field id goes into dataSource as well
    if type_name == "SUBTOTAL":
        if data_source is None or source_control_id is None:
            raise ValueError(
                "SUBTOTAL requires data_source (controlId of the bridge "
                "SUB_LIST or multi-RELATE_SHEET on this sheet) AND "
                "source_control_id (controlId of the column on the "
                "bridge's target worksheet to aggregate)."
            )
        ctrl["dataSource"] = data_source if data_source.startswith("$") else f"${data_source}$"
        ctrl["sourceControlId"] = source_control_id

    if extra:
        ctrl.update(extra)
    return ctrl


def _normalize_options(
    opts: list[str] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Coerce a list of strings (or partial dicts) into HAP option dicts.

    First item is marked as the default selection (checked=True) unless
    any caller-supplied dict already sets it.
    """
    colors = [
        "#C9E6FC", "#C3F2F2", "#C2F1D2", "#FFE7B1", "#FBD2BF",
        "#FDD2DC", "#E6CFF1", "#D2D2D2",
    ]
    out: list[dict[str, Any]] = []
    any_default = any(isinstance(o, dict) and o.get("checked") for o in opts)
    for i, o in enumerate(opts):
        if isinstance(o, dict):
            entry = {
                "key": o.get("key") or str(uuid.uuid4()),
                "value": o["value"],
                "isDeleted": o.get("isDeleted", False),
                "index": o.get("index", i + 1),
                "checked": o.get("checked", False),
                "color": o.get("color", colors[i % len(colors)]),
            }
        else:
            entry = {
                "key": str(uuid.uuid4()),
                "value": str(o),
                "isDeleted": False,
                "index": i + 1,
                "checked": (not any_default and i == 0),
                "color": colors[i % len(colors)],
            }
        out.append(entry)
    return out


def build_auto_id_rule(*segments: Any) -> str:
    """Build the JSON-string for `AUTO_ID.advancedSetting.increase`.

    Each segment is one of:
      * ``str``        — literal prefix/separator (e.g. ``"ORD-"``)
      * ``"date:FORMAT"`` — a date segment, where FORMAT is one of
        ``YYYY``, ``YYYYMM``, ``YYYYMMDD``, ``YYYYMMDDHH``, etc.
      * ``int`` or ``("auto", length, repeat)`` — auto-incrementing
        number, optionally with daily/monthly reset.

    Examples::

        # ORD-20260519-0001 (resets daily, 4-digit pad)
        build_auto_id_rule("ORD-", "date:YYYYMMDD", ("auto", 4, "daily"))

        # C-00001 (never resets, 5-digit pad)
        build_auto_id_rule("C-", ("auto", 5, "never"))

    The encoding matches what HAP's frontend emits in the
    multi-segment "自动编号规则" config dialog.
    """
    out: list[dict[str, Any]] = []
    repeat_map = {"never": 0, "daily": 1, "monthly": 2, "yearly": 3}
    for seg in segments:
        if isinstance(seg, str):
            if seg.startswith("date:"):
                out.append({"type": 4, "format": seg[5:]})
            else:
                out.append({"type": 2, "controlId": seg})
        elif isinstance(seg, int):
            out.append({"type": 1, "repeatType": 0, "start": 1,
                        "length": seg, "format": "auto",
                        "key": uuid.uuid4().hex})
        elif isinstance(seg, tuple) and seg and seg[0] == "auto":
            length = seg[1] if len(seg) > 1 else 4
            repeat = seg[2] if len(seg) > 2 else "never"
            out.append({"type": 1, "repeatType": repeat_map.get(repeat, 0),
                        "start": 1, "length": length, "format": "auto",
                        "key": uuid.uuid4().hex})
        else:
            raise ValueError(f"Unknown auto-id segment: {seg!r}")
    return json.dumps(out, ensure_ascii=False)


def _new_control_id() -> str:
    """Generate a client-side controlId. Server replaces with a real
    24-hex id on first save but accepts ours during creation."""
    return uuid.uuid4().hex


# ── Public: format a record cell value ──────────────────────────────────


def format_cell(field_type: str | int, value: Any) -> str:
    """Coerce `value` into the string form V3 batch_create_records /
    create_record / update_record expect.

    V3 takes simpler shapes than legacy AddWorksheetRow:

        TEXT / NUMBER / MONEY / DATE / EMAIL / MOBILE_PHONE
            -> str(value)
        DROP_DOWN / FLAT_MENU
            -> the option label (server resolves to the option key).
               Pass a string. If you must pass a list, the first item
               is used.
        MULTI_SELECT
            -> comma-separated labels (server resolves each).
               Accepts str or iterable.
        USER_PICKER  -> plain accountId (single) or comma-separated (multi)
        DEPARTMENT   -> plain departmentId (single) or comma-separated
        ORG_ROLE     -> plain organizeId (single) or comma-separated
        RELATE_SHEET -> plain rowId (single) or comma-separated (multi)
        LOCATION     -> JSON-string of {x, y, address, title}
        ATTACHMENT   -> JSON-string of [{name, url}]; pass list[dict].
        SWITCH       -> "1" / "0" (bool accepted)
        SUB_LIST     -> JSON-string of an array of row dicts. Each row
                        dict maps child fieldName/alias/controlId to
                        already-formatted value strings. See V3 docs.

    Empty value -> empty string (V3 treats as "leave unset").

    For the legacy receiveControls shape (RELATE_SHEET as
    `[{sid: rowId}]`, USER_PICKER as `[{accountId}]`, etc.) keep using
    `record.create_record` / `record.update_record`, which target the
    legacy endpoint.
    """
    if isinstance(field_type, int):
        name = TYPE_NAME.get(field_type, "")
    else:
        name = field_type.upper()

    if value is None or value == "":
        return ""

    if name in ("DROP_DOWN", "FLAT_MENU"):
        if isinstance(value, (list, tuple)):
            value = value[0] if value else ""
        return str(value)

    if name == "MULTI_SELECT":
        if isinstance(value, (list, tuple)):
            return ",".join(str(v) for v in value)
        return str(value)

    if name in ("USER_PICKER", "DEPARTMENT", "ORG_ROLE", "RELATE_SHEET"):
        if isinstance(value, (list, tuple)):
            return ",".join(str(v) for v in value)
        return str(value)

    if name == "SUB_LIST":
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    if name == "LOCATION":
        return json.dumps(value, ensure_ascii=False)

    if name == "ATTACHMENT":
        if isinstance(value, str):
            return value
        return json.dumps(list(value), ensure_ascii=False)

    if name == "SWITCH":
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)

    return str(value)


def format_sub_list_rows(
    rows: Iterable[dict[str, str]],
) -> str:
    """Build the JSON-string value for a SUB_LIST cell.

    Each row is a dict mapping child controlId -> string value. A
    `tempRowId` field is auto-assigned per row (HAP requires it to
    identify newly inserted child rows).

    Example:
        format_sub_list_rows([
            {"<product_field_id>": "[{...sid...}]",
             "<qty_field_id>": "2",
             "<price_field_id>": "99.00"},
        ])
    """
    out = []
    for row in rows:
        cells = [{"controlId": "tempRowId",
                  "value": f"temp-{uuid.uuid4()}"}]
        for cid, val in row.items():
            cells.append({"controlId": cid, "value": val})
        out.append(cells)
    return json.dumps(out, ensure_ascii=False)
