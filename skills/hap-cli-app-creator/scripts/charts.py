"""Build dashboard chart (report) specs + page component layouts.

A dashboard custom page is a two-level composite:
  1. each chart is created via ``worksheet chart create`` (saveReportConfig)
     which returns a ``reportId``;
  2. the page layout is saved via ``custom-page save`` with a ``components``
     array whose chart components carry that ``reportId`` in ``value``.

The chart wire payload is large and the server rejects partial specs, so
these builders fill the full default structure observed in
sources/captured/custom-page-dashboard and only vary the parts the design
controls (reportType, dimension, metrics, filter, view).
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Optional

# Friendly chart type -> reportType integer (pd-openweb
# src/pages/Statistics/Charts/common.js reportTypes; verified live).
REPORT_TYPE = {
    "number": 10, "bar": 1, "line": 2, "pie": 3, "pivot": 8,
    # dimension+metric shaped, share the generic xaxes/yaxisList spec:
    "funnel": 6, "radar": 5, "bidirectional_bar": 11, "ranking": 16,
    "scatter": 12, "wordcloud": 13, "world_map": 17,
    # carry extra type-specific blocks (rightY / config / country):
    "dual_axes": 7, "gauge": 14, "progress": 15, "region_map": 9,
}

# Region-map granularity -> particleSizeType (1=province, 2=city, 3=county).
_MAP_LEVEL = {"province": 1, "city": 2, "county": 3}

# Aggregate -> chart normType (verified: sum=1, count=5; others best-effort).
NORM_TYPE = {"sum": 1, "count": 5, "avg": 2, "max": 3, "min": 4}

# date grain -> particleSizeType (quarter=4 verified; rest by convention).
DATE_GRAIN = {"day": 1, "week": 2, "month": 3, "quarter": 4, "year": 5}

# Component type integers (pd-openweb customPage/util.js). Only the six with
# builders are listed; carousel/tabs/card/image exist upstream but have no
# builder here and are not in the design schema.
COMP_TYPE = {
    "chart": 1, "rich_text": 2, "embed_url": 3, "button": 4, "view": 5,
    "filter": 6,
}

_DISPLAY_SETUP = {
    "isPerPile": False, "isPile": False, "isAccumulate": False,
    "accumulatePerPile": None, "isToday": False, "isLifecycle": False,
    "lifecycleValue": 0, "contrastType": 0, "fontStyle": 1, "showTotal": False,
    "showTitle": True, "showLegend": True, "legendType": 1, "showDimension": True,
    "showNumber": True, "showPercent": False, "showXAxisCount": 0,
    "showChartType": 1, "showPileTotal": True, "hideOverlapText": False,
    "showRowList": True, "showControlIds": [], "auxiliaryLines": [],
    "showOptionIds": [], "contrast": False, "colorRules": [],
    "percent": {"enable": False, "type": 2, "dot": "2", "dotFormat": "1", "roundType": 2},
    "mergeCell": True, "previewUrl": None, "imageUrl": None,
    "xdisplay": {"showDial": True, "showTitle": False, "title": "", "minValue": None, "maxValue": None},
    "xaxisEmpty": False,
    "ydisplay": {"showDial": True, "showTitle": False, "title": "", "minValue": None, "maxValue": None, "lineStyle": 1, "showNumber": None},
}

_FILTER = {
    "filterRangeId": "ctime", "filterRangeName": "创建时间", "rangeType": 0,
    "rangeValue": None, "today": False, "ignoreToday": False,
    "dynamicFilter": {"startType": 1, "startCount": 1, "startUnit": 1,
                      "endType": 1, "endCount": 1, "endUnit": 1},
}

_SUMMARY = {"controlId": "", "type": 1, "name": "总计", "number": True,
            "percent": False, "sum": 0, "contrastSum": 0, "contrastMapSum": 0, "rename": ""}

_EMPTY_XAXES = {
    "controlId": "", "sortType": 0, "particleSizeType": 0, "rename": "",
    "emptyType": 0, "fields": None, "subTotal": False, "subTotalName": None,
    "showFormat": "4", "displayMode": "text", "controlName": "", "controlType": 0,
    "dataSource": "", "options": [], "advancedSetting": None, "relationControl": None,
    "cid": "", "cname": "", "xaxisEmptyType": 0, "xaxisEmpty": False, "c_Id": "",
}


def _yaxis(metric: dict[str, Any], resolve: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Build one yaxisList value entry. ``metric`` is {field, aggregate}.
    field == 'count' -> the special record-count pseudo column."""
    agg = metric.get("aggregate", "sum")
    if metric["field"] == "count":
        cid, cname, ctype = "record_count", "记录数量", 10000000
        norm = NORM_TYPE.get(agg, 5)
    else:
        c = resolve(metric["field"])
        cid = c.get("controlId") or c.get("id")
        cname = c.get("controlName") or metric["field"]
        ctype = c.get("type", 6)
        norm = NORM_TYPE.get(agg, 1)
    return {
        "controlId": cid, "controlName": cname, "controlType": ctype,
        "magnitude": 0, "roundType": 2, "dotFormat": "1", "suffix": "", "ydot": 2,
        "fixType": 0, "showNumber": True, "hide": False,
        "percent": {"enable": False, "type": 2, "dot": "2", "dotFormat": "1", "roundType": 2},
        "normType": norm, "emptyShowType": 0, "dot": 0, "rename": "", "advancedSetting": {},
    }


def _xaxes(dimension: dict[str, Any], resolve: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Build the xaxes (dimension) block from a {field, date_grain} dim."""
    c = resolve(dimension["field"])
    cid = c.get("controlId") or c.get("id")
    grain = DATE_GRAIN.get(dimension.get("date_grain", ""), 0)
    x = dict(_EMPTY_XAXES)
    x.update({
        "controlId": cid, "controlName": c.get("controlName") or dimension["field"],
        "controlType": c.get("type", 0), "particleSizeType": grain,
        "dataSource": c.get("dataSource", "") or "", "advancedSetting": {"max": ""},
        "cid": cid, "cname": c.get("controlName") or dimension["field"], "c_Id": cid,
    })
    return x


def _pivot_dim(dimension: dict[str, Any],
               resolve: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Build one pivot row/column entry (pivotTable.lines / .columns item).

    Shaped after sources/captured/custom-page-dashboard/...saveReportConfig
    (reportType 8): like an xaxis item but with fields=[], showtype showtype,
    subTotal/displayMode fields the pivot grid needs."""
    c = resolve(dimension["field"])
    cid = c.get("controlId") or c.get("id")
    cname = c.get("controlName") or dimension["field"]
    grain = DATE_GRAIN.get(dimension.get("date_grain", ""), 0)
    return {
        "controlId": cid, "sortType": 0, "particleSizeType": grain, "rename": "",
        "emptyType": 0, "fields": [], "subTotal": False, "subTotalName": None,
        "showFormat": "4", "displayMode": "text", "controlName": cname,
        "controlType": c.get("type", 0), "dataSource": c.get("dataSource", "") or "",
        "options": None, "advancedSetting": {"showtype": "0"}, "relationControl": None,
        "cid": cid, "cname": cname, "xaxisEmptyType": 0, "xaxisEmpty": False, "c_Id": cid,
    }


def _pivot_summary(location: int,
                   metrics: list[dict[str, Any]],
                   resolve: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Build a pivotTable columnSummary (location 4) / lineSummary (location 2)
    total block, listing each value field in controlList."""
    control_list = []
    for m in metrics:
        if m["field"] == "count":
            cid = "record_count"
        else:
            c = resolve(m["field"])
            cid = c.get("controlId") or c.get("id")
        control_list.append({
            "controlId": cid, "type": 1, "name": "", "number": True,
            "percent": False, "sum": 0, "contrastSum": 0, "contrastMapSum": 0,
        })
    return {
        "controlId": "", "type": 1, "name": "", "number": True, "percent": False,
        "sum": 0, "contrastSum": 0, "contrastMapSum": 0, "rename": "",
        "location": location, "controlList": control_list,
    }


def _pivot_table(chart: dict[str, Any],
                 resolve: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Build the pivotTable block from a friendly pivot config
    (rows -> lines, columns -> columns, metrics -> summaries + yaxisList)."""
    rows = chart.get("rows") or []
    columns = chart.get("columns") or []
    metrics = chart.get("metrics") or [{"field": "count", "aggregate": "count"}]
    return {
        "showColumnCount": 0, "showColumnTotal": True,
        "showLineCount": 0, "showLineTotal": True,
        "columns": [_pivot_dim(d, resolve) for d in columns],
        "columnSummary": _pivot_summary(4, metrics, resolve),
        "lines": [_pivot_dim(d, resolve) for d in rows],
        "lineSummary": _pivot_summary(2, metrics, resolve),
    }


def _right_y(metrics: list[dict[str, Any]], report_type_int: int,
             resolve: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Build the dual-axes (reportType 7) ``rightY`` block: a mini chart
    config for the secondary axis. Shaped after
    sources/captured/custom_page_statistics (reportType 7)."""
    title = ""
    if metrics:
        m0 = metrics[0]
        title = ("记录数量" if m0["field"] == "count"
                 else resolve(m0["field"]).get("controlName") or m0["field"])
    return {
        "reportType": report_type_int,
        "display": {
            "isPerPile": False, "isPile": False, "isAccumulate": False,
            "accumulatePerPile": None,
            "ydisplay": {"showDial": True, "showTitle": False, "title": title,
                         "minValue": None, "maxValue": None, "lineStyle": 1,
                         "showNumber": None},
        },
        "splitId": "", "split": dict(_EMPTY_XAXES),
        "summary": {**_SUMMARY, "showTotal": False},
        "yaxisList": [_yaxis(m, resolve) for m in metrics],
    }


def _gauge_config(chart: dict[str, Any],
                  resolve: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Build the gauge/progress (reportType 14/15) ``config`` block:
    min/max bounds (optional field refs) + targetList (the goal field).
    Shaped after sources/captured/custom_page_statistics (reportType 14/15)."""
    def measure(field: Optional[str]) -> Optional[dict[str, Any]]:
        if not field:
            return None
        return _yaxis({"field": field, "aggregate": "sum"}, resolve)

    target = chart.get("target")
    return {
        "min": measure(chart.get("min_field")),
        "max": measure(chart.get("max_field")),
        "targetList": [measure(target)] if target else [],
    }


def chart_spec(
    chart: dict[str, Any],
    *,
    view_id: str,
    resolve: Callable[[str], dict[str, Any]],
    filters: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Build the full saveReportConfig spec (minus name/reportType/appId,
    which the CLI stamps) from a friendly chart config."""
    is_pivot = chart.get("report_type") == "pivot"
    dims = chart.get("dimensions") or []
    metrics = chart.get("metrics") or [{"field": "count", "aggregate": "count"}]
    display = dict(_DISPLAY_SETUP)
    if chart.get("display"):
        display.update(chart["display"])
    # TopN cap: showXAxisCount holds "x轴前 N 项" (positive = top, see
    # pd-openweb Statistics/components/.../DataFilter.js). A friendly
    # ``limit`` on the chart maps straight to it.
    if chart.get("limit") is not None:
        display["showXAxisCount"] = int(chart["limit"])
    filt = dict(_FILTER)
    if filters:
        filt["filter"] = None  # filters supplied via items below
    spec: dict[str, Any] = {
        # pivot uses pivotTable + empty xaxes/split; others use xaxes.
        "xaxes": {} if is_pivot else (_xaxes(dims[0], resolve) if dims else dict(_EMPTY_XAXES)),
        "yaxisList": [_yaxis(m, resolve) for m in metrics],
        "yreportType": None,
        "displaySetup": display,
        "filter": filt,
        "sorts": [], "formulas": [], "summary": dict(_SUMMARY), "style": {},
        "split": {}, "splitId": None, "sourceType": 1, "auth": 1, "isPublic": True,
        "views": [{"viewId": view_id, "name": "全部", "viewType": 0}],
        "desc": "",
    }
    if is_pivot:
        spec["pivotTable"] = _pivot_table(chart, resolve)

    rt = chart.get("report_type")
    if rt == "dual_axes":
        # right axis: its own chart type (bar/line) + metrics.
        right_int = REPORT_TYPE.get(chart.get("right_type", "line"), 2)
        spec["rightY"] = _right_y(chart.get("right_metrics") or [], right_int, resolve)
    elif rt in ("gauge", "progress"):
        # gauge/progress have no dimension; the value is the single metric.
        spec["xaxes"] = dict(_EMPTY_XAXES)
        spec["config"] = _gauge_config(chart, resolve)
    elif rt == "region_map":
        # the dimension is a Region field; tag the area granularity.
        level = _MAP_LEVEL.get(chart.get("map_level", "province"), 1)
        if isinstance(spec.get("xaxes"), dict) and spec["xaxes"].get("controlId"):
            spec["xaxes"]["particleSizeType"] = level
            spec["xaxes"]["advancedSetting"] = {"chooserange": "CN"}
        spec["country"] = {"particleSizeType": level, "filterCode": "",
                           "filterCodeName": "", "municipality": False}
    elif rt == "ranking":
        # TopChart (排行榜) sorts by its first metric value — descending by
        # default; pd-openweb Statistics/common.js stamps
        # sorts=[{<yaxis0.controlId>: 2}] + the crown style. Without this the
        # bars render in raw record order, which reads as "unsorted".
        yl = spec["yaxisList"]
        if yl and yl[0].get("controlId"):
            direction = 1 if chart.get("sort") == "asc" else 2  # 1=asc, 2=desc
            spec["sorts"] = [{yl[0]["controlId"]: direction}]
        spec["style"] = {"topStyle": "crown", "valueProgressVisible": True}

    if filters:
        spec["filter"]["items"] = filters  # CLI mints a stored filter id
    return spec


def chart_component(
    *, report_id: str, worksheet_id: str, name: str, report_type: int,
    layout: dict[str, int],
) -> dict[str, Any]:
    """Build a type-1 chart component for the page layout."""
    return {
        "type": 1, "value": report_id, "config": {"objectId": uuid.uuid4().hex},
        "worksheetId": worksheet_id, "name": name, "reportType": report_type,
        "web": {"title": "", "titleVisible": False, "visible": True,
                "layout": {**layout, "minW": 2, "minH": 4}},
        "mobile": {"title": "", "titleVisible": False, "visible": True, "layout": None},
    }


def view_component(*, worksheet_id: str, view_id: str, name: str,
                   layout: dict[str, int]) -> dict[str, Any]:
    """Build a type-5 embedded-view component.

    The component's display title lives in ``config.name`` (pd-openweb
    customPage editWidget/view/Setting.jsx reads/writes ``config.name``),
    so the design's component name goes there. The view already renders its
    own header, so the outer widget title bar is hidden on both web and
    mobile (``titleVisible: False``).
    """
    return {
        "type": 5, "value": worksheet_id, "viewId": view_id, "name": name,
        "config": {"objectId": uuid.uuid4().hex, "name": name},
        "web": {"title": "", "titleVisible": False, "visible": True,
                "layout": {**layout, "minW": 2, "minH": 4}},
        "mobile": {"title": "", "titleVisible": False, "visible": True, "layout": None},
    }


# Button click action -> wire integer (pd-openweb customPage btnSetting.jsx
# CLICK_ACTION). 5/6 carried but only filled via the raw `config` escape.
# open_page (3) is intentionally unsupported: a custom page cannot link to
# another custom page (the target page may not exist yet at build time and the
# feature was dropped — see BUILD-13). The wire integers keep upstream meaning.
BUTTON_ACTION = {
    "create_record": 1, "open_view": 2,
    "open_link": 4, "scan": 5, "call_process": 6,
}
# How the target opens (btnSetting.jsx OPEN_MODE; 3=dialog only for open_link).
OPEN_MODE = {"current_page": 1, "new_page": 2, "dialog": 3}
# Button group visual type (config.btnType): button=text button, graphic=icon tile.
BTN_SHAPE = {"button": 1, "graphic": 2}
# Tile layout direction when shape=graphic (config.direction).
BTN_DIRECTION = {"vertical": 1, "horizontal": 2}
_ICON_BASE = "https://fp1.mingdaoyun.cn/customIcon/"


def _button_item(
    b: dict[str, Any], idx: int, *,
    resolve_ws: Callable[[str], str],
    resolve_view: Callable[[str, str], str],
    resolve_action: Callable[[str, str], str],
) -> dict[str, Any]:
    """Build one entry of button.buttonList from a friendly button dict.

    Per-button required fields depend on ``action`` (see schema):
      create_record -> value=worksheetId (+ optional btnId from a custom action)
      open_view     -> value=worksheetId, viewId=<resolved view>
      open_link     -> value=url
      scan/call_process -> filled via raw ``config`` (escape hatch).
    """
    action = BUTTON_ACTION[b["action"]]
    default_open = 1 if action == 1 else 2  # create opens current page by default
    item: dict[str, Any] = {
        "name": b["label"],
        "color": b.get("color", "#2196f3"),
        "config": {},
        "id": uuid.uuid4().hex,
        "action": action,
        "viewId": "",
        "openMode": OPEN_MODE.get(b.get("open_mode", ""), default_open),
        "value": "",
    }
    if b.get("icon"):
        item["config"] = {"icon": b["icon"], "iconUrl": f"{_ICON_BASE}{b['icon']}.svg"}
    if action == 1:  # create_record
        item["value"] = resolve_ws(b["worksheet"])
        item["btnId"] = (
            resolve_action(b["worksheet"], b["custom_action"])
            if b.get("custom_action") else None
        )
    elif action == 2:  # open_view
        wsid = resolve_ws(b["worksheet"])
        item["value"] = wsid
        item["viewId"] = resolve_view(wsid, b["view"])
    elif action == 4:  # open_link
        item["value"] = b["url"]
    else:  # scan / call_process — caller-supplied raw value
        item["value"] = b.get("value", "")
    if b.get("config"):
        item["config"].update(b["config"])
    return item


def button_component(
    *, button: dict[str, Any], name: str, layout: dict[str, int],
    resolve_ws: Callable[[str], str],
    resolve_view: Callable[[str, str], str],
    resolve_action: Callable[[str, str], str],
) -> dict[str, Any]:
    """Build a type-4 button-group component for the page layout."""
    shape = BTN_SHAPE.get(button.get("shape", "graphic"), 2)
    count = button.get("count", 2)
    button_list = [
        _button_item(b, i, resolve_ws=resolve_ws, resolve_view=resolve_view,
                     resolve_action=resolve_action)
        for i, b in enumerate(button.get("buttons", []))
    ]
    return {
        "type": 4,
        "button": {
            "style": button.get("style", 2),
            "wdith": button.get("width", 2),  # API field is misspelled "wdith"
            "explain": button.get("explain", ""),
            "count": count,
            "mobileCount": button.get("mobile_count", count),
            "buttonList": button_list,
            "config": {
                "btnType": shape,
                "direction": BTN_DIRECTION.get(button.get("direction", "vertical"), 1),
            },
        },
        "web": {"title": "", "titleVisible": False, "visible": True,
                "layout": {**layout, "minW": 2, "minH": 4}},
        "mobile": {"title": "", "titleVisible": False, "visible": True, "layout": None},
    }


# filterType codes (FilterTypeEnum) reused by the page filter bar.
_FILTER_OP_TO_TYPE = {
    "contains": 1, "eq": 2, "ne": 6, "isempty": 7, "isnotempty": 8,
    "between": 11, "gt": 13, "ge": 14, "lt": 15, "le": 16,
    "date_is": 17, "date_is_not": 18, "date_between": 31,
}
# DateRangeEnum subset for a default-selected date filter.
_DATE_RANGE = {
    "today": 1, "yesterday": 2, "this_week": 4, "last_week": 5,
    "this_month": 7, "last_month": 8, "this_quarter": 12, "last_quarter": 13,
    "this_year": 15, "last_year": 16, "custom": 18,
    "last_7_days": 21, "last_30_days": 23,
}
_DATE_CTRL_TYPES = {15, 16, 30}  # Date / DateTime / formula-date
# Full daterange option set a date filter exposes (verbatim from capture).
_DEFAULT_DATERANGE = "[1,2,3,4,5,6,7,8,9,12,13,14,15,16,17,52,21,22,23,51,31,32,33]"


def filter_component(
    *, filter_bar: dict[str, Any], name: str, layout: dict[str, int],
    chart_map: dict[str, dict[str, str]],
    resolve_control: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Build a type-6 page-filter-bar component carrying a high-level
    ``filtersGroup`` spec. The CLI's ``custom-page save`` mints the
    filtersGroupId via Worksheet/SaveFiltersGroup before persisting.

    Each filter binds one field across one or more chart components: it
    references each target chart by that chart's ``config.objectId`` plus
    the field's controlId on that chart's worksheet (objectControls).

    ``chart_map``: chart component name -> {objectId, worksheetId}.
    ``resolve_control(worksheetId, field)`` -> the control dict (controlId+type).
    """
    filters = []
    for f in filter_bar.get("filters", []):
        # A filter item binds one logical column across its target charts.
        # ``field`` is the single column name used on every target; the
        # optional ``field_map`` (worksheet logical name -> field logical name)
        # lets ONE filter map to differently-named columns per worksheet — e.g.
        # one date picker driving 入库单 by 入库日期 AND 出库单 by 出库日期. The
        # resulting objectControls carry each chart's own controlId.
        field_map = f.get("field_map") or {}
        default_field = f.get("field")

        def _field_for(info, _fm=field_map, _df=default_field):
            return _fm.get(info.get("worksheet", "")) or _df

        label = f.get("name") or default_field or next(iter(field_map.values()), "")
        targets = f.get("targets")
        if not targets:
            # auto-bind: every chart whose worksheet has the (mapped) field.
            targets = []
            for cname, info in chart_map.items():
                fld = _field_for(info)
                if not fld:
                    continue
                try:
                    resolve_control(info["worksheetId"], fld)
                    targets.append(cname)
                except Exception:
                    continue
        if not targets:
            raise RuntimeError(
                f"page filter {label or '<unnamed>'!r} matched no chart components "
                f"(known charts: {', '.join(chart_map) or '<none>'})")
        object_controls = []
        dtype = 0
        rep_cid = ""
        for cname in targets:
            info = chart_map[cname]
            fld = _field_for(info)
            if not fld:
                raise RuntimeError(
                    f"page filter has no field for chart {cname!r} "
                    f"(worksheet {info.get('worksheet', '')!r}): add it to "
                    f"field_map or set a default field")
            ctl = resolve_control(info["worksheetId"], fld)
            cid = ctl.get("controlId") or ctl.get("id")
            dtype = ctl.get("type", 0)
            rep_cid = rep_cid or cid
            object_controls.append({
                "objectId": info["objectId"], "type": 1, "name": cname,
                "worksheetId": info["worksheetId"], "controlId": cid,
            })
        is_date = dtype in _DATE_CTRL_TYPES
        op = f.get("op") or ("date_is" if is_date else "eq")
        flt: dict[str, Any] = {
            "filterId": uuid.uuid4().hex,
            "name": label,
            "global": True,
            "dataType": dtype,
            "filterType": _FILTER_OP_TO_TYPE.get(op, 2),
            "objectControls": object_controls,
            "controlId": rep_cid,
            "values": [], "value": "", "minValue": "", "maxValue": "",
        }
        if is_date:
            flt["dateRangeType"] = 3
            flt["advancedSetting"] = {"daterange": _DEFAULT_DATERANGE}
            if f.get("date_range"):
                flt["dateRange"] = _DATE_RANGE[f["date_range"]]
        filters.append(flt)
    return {
        "type": 6, "needUpdate": True,
        "filtersGroup": {
            "name": filter_bar.get("name", ""),
            "enableBtn": filter_bar.get("enable_btn", False),
            "filters": filters,
        },
        "web": {"title": "", "titleVisible": False, "visible": True,
                "layout": {**layout, "minW": 2, "minH": 3}},
        "mobile": {"title": "", "titleVisible": False, "visible": True, "layout": None},
    }


def rich_text_component(*, html: str, name: str, layout: dict[str, int]) -> dict[str, Any]:
    """Build a type-2 rich-text component."""
    return {
        "type": 2, "value": html, "name": name,
        "web": {"title": "", "titleVisible": False, "visible": True,
                "layout": {**layout, "minW": 2, "minH": 4}},
        "mobile": {"title": "", "titleVisible": False, "visible": True, "layout": None},
    }


def embed_url_component(*, url: str, name: str, layout: dict[str, int]) -> dict[str, Any]:
    """Build a type-3 embedded-URL (iframe) component.

    Wire shape verified from pd-openweb ``src/pages/customPage/util.js``
    (``embedUrl: 3``; the widget's ``value`` is the URL string, same
    pattern as the rich-text widget — no extra required config).
    """
    return {
        "type": 3, "value": url, "name": name,
        "web": {"title": "", "titleVisible": False, "visible": True,
                "layout": {**layout, "minW": 2, "minH": 4}},
        "mobile": {"title": "", "titleVisible": False, "visible": True, "layout": None},
    }


# Default web grid widths (48-col grid) per component kind.
_DEFAULT_W = {"number": 12, "chart": 24, "view": 48, "rich_text": 48,
              "embed_url": 24, "button": 24, "filter": 24}
_DEFAULT_H = {"number": 5, "chart": 10, "view": 12, "rich_text": 5,
              "embed_url": 12, "button": 6, "filter": 3}


def auto_layout(kind: str, width: int, cursor: dict[str, int]) -> dict[str, int]:
    """Pack a component into the 48-col grid, advancing ``cursor`` (x/y/row_h)."""
    w = width
    if cursor["x"] + w > 48:
        cursor["x"] = 0
        cursor["y"] += cursor["row_h"]
        cursor["row_h"] = 0
    layout = {"x": cursor["x"], "y": cursor["y"], "w": w,
              "h": _DEFAULT_H.get(kind, 8)}
    cursor["x"] += w
    cursor["row_h"] = max(cursor["row_h"], layout["h"])
    return layout
