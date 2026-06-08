"""Offline self-tests for the harness internals (no live server).

    python -m scripts.selftest

Covers the store format, schema validation, field compilation, and the
compiler's phase ordering — the pure-Python layers the live smoke
depends on. Exits non-zero on the first failed assertion.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


def _vd(design):
    """``schema.validate_design`` with the now-required ``icon`` auto-filled
    on app / worksheets / custom_pages.

    ``icon`` is mandatory in the schema, but for most fixtures the icon is
    pure boilerplate unrelated to what the test exercises (cascade selects,
    topo order, workflow refs, …). This helper deep-copies the fixture and
    sets a default icon only where absent — so fixtures stay focused, while
    the canonical "a complete valid design validates clean *with* real icons"
    coverage lives in ``test_schema`` (which validates the shipped
    ``examples/minimal.design.json`` directly, not through this helper).
    """
    import copy
    from scripts import schema
    d = copy.deepcopy(design)
    d.setdefault("app", {}).setdefault("icon", "1_2_order")
    for w in d.get("worksheets", []) or []:
        if isinstance(w, dict):
            w.setdefault("icon", "1_2_order")
    for pg in d.get("custom_pages", []) or []:
        if isinstance(pg, dict):
            pg.setdefault("icon", "1_2_order")
    return schema.validate_design(d)


def test_store() -> None:
    from scripts.store import Store
    from scripts.errors import ResolveError

    d = Path(tempfile.mkdtemp()) / "appX"
    s = Store(d)
    s.put_app("appX", "Demo", "org1",
              [{"id": "sec1", "name": "客户管理"}, {"id": "sec2", "name": "订单管理"}])
    assert s.resolve_section("客户管理") == "sec1"
    s.put_entity("worksheet", "ws1", "客户表", {"name": "客户表"})
    assert s.resolve("worksheet", "客户表") == "ws1"
    m = s.put_controls("ws1", [
        {"controlId": "c1", "controlName": "客户名称", "type": 2},
        {"controlId": "c2", "controlName": "联系电话", "type": 3},
        {"controlId": "c9", "controlName": "分隔", "type": 22},
    ])
    assert m == {"客户名称": "c1", "联系电话": "c2"}
    assert s.resolve_control("ws1", "联系电话") == "c2"
    assert s.get_control("ws1", "客户名称")["controlId"] == "c1"
    s.put_view("ws1", "v1", "全部", {})
    assert s.resolve_view("ws1", "全部") == "v1"
    try:
        s.resolve("worksheet", "缺")
        raise AssertionError("expected ResolveError")
    except ResolveError:
        pass


def test_schema() -> None:
    from scripts import schema

    good = json.loads(
        (Path(__file__).parent.parent / "examples" / "minimal.design.json").read_text("utf-8")
    )
    # Validate the shipped example directly (NOT via _vd): the example must
    # carry real icons and pass clean on its own.
    assert schema.validate_design(good) == [], schema.validate_design(good)

    bad = {
        "app": {"name": "x", "bogus": 1},
        "worksheets": [{"name": "t", "fields": [
            {"type": "Nope", "name": "a"},
            {"type": "Region", "name": "地区"},
            {"type": "Relation", "name": "r",
             "relation": {"worksheet": "t", "multi": False, "display": "tab_table"}},
        ]}],
        "roles": [{"name": "r1"}],
    }
    errs = _vd(bad)
    joined = "\n".join(errs)
    assert "unexpected property 'bogus'" in joined
    assert "not in enum" in joined
    assert "region_level" in joined
    assert "permission_scope" in joined
    assert "display 'tab_table' invalid for single" in joined


def test_fields() -> None:
    from scripts import fields as F

    assert F.categorize({"type": "Text"}) == "intra"
    assert F.categorize({"type": "Relation"}) == "relation"
    assert F.categorize({"type": "Lookup"}) == "derived"

    spec = F.intra_field_spec({"type": "Region", "name": "地区", "region_level": "city"})
    assert spec["extra"]["regionLevel"] == "city"

    rc = F.relation_control("所属客户", target_worksheet_id="ws_c",
                            multi=False, display="dropdown", show_control_ids=["c1"])
    assert rc["type"] == 29 and rc["dataSource"] == "ws_c"
    assert rc["advancedSetting"]["showtype"] == "3" and rc["enumDefault"] == 1

    lc = F.lookup_control("电话", via_control_id="rel1", source_control_id="c2")
    assert lc["type"] == 30 and lc["dataSource"] == "$rel1$" and lc["sourceControlId"] == "c2"


def test_compiler() -> None:
    from scripts import compiler

    design = json.loads(
        (Path(__file__).parent.parent / "examples" / "minimal.design.json").read_text("utf-8")
    )
    steps = compiler.compile_design(design)
    kinds = [s.kind for s in steps]
    # app first; worksheets before relations before derived; optionsets up front.
    assert kinds[0] == "app"
    assert kinds.index("worksheet") < kinds.index("relation") < kinds.index("derived")
    assert "role" in kinds and "optionset" in kinds
    # roles must precede workflows — approve / approval-block nodes (now all in
    # the Workflows phase) reference app roles by name, which must already exist.
    if "workflow" in kinds:
        assert kinds.index("role") < kinds.index("workflow"), "roles must build before workflows"
    # custom actions must precede workflows — a button-triggered workflow rides
    # the shadow process derived by its trigger_workflow custom action, and a
    # page may embed a button referencing a custom action.
    if "custom_action" in kinds and "workflow" in kinds:
        assert kinds.index("custom_action") < kinds.index("workflow"), \
            "custom actions must build before workflows"


def test_compiler_reverse_relation_ordering() -> None:
    """Two-way reverse relations split by bridge usage (BUILD-09):
    a reverse NOT used as a derived field's `via` is built AFTER the
    Derived phase, so its show_fields can reference rollup/lookup columns;
    a reverse that IS a derived `via` bridge stays BEFORE Derived."""
    from scripts import compiler

    design = {
        "app": {"name": "X"},
        "worksheets": [
            {"name": "订单", "fields": [
                {"type": "Text", "name": "单号", "is_title": True},
                {"type": "Number", "name": "金额"},
                # forward relation to 客户, two-way reverse "客户订单" on 客户.
                {"type": "Relation", "name": "客户",
                 "relation": {"worksheet": "客户", "multi": False,
                              "two_way": {"name": "客户订单", "display": "tab_table",
                                          "show_fields": ["单号", "金额"]}}},
            ]},
            {"name": "客户", "fields": [
                {"type": "Text", "name": "名称", "is_title": True},
                # rollup bridges through the reverse relation "客户订单".
                {"type": "Rollup", "name": "订单总额",
                 "rollup": {"via": "客户订单", "field": "金额", "aggregate": "sum"}},
            ]},
        ],
    }
    steps = compiler.compile_design(design)
    kinds = [s.kind for s in steps]
    ids = [s.id for s in steps]
    assert "relation_reverse" in kinds, kinds
    # forward relation always in the Relations pass, before derived
    assert kinds.index("relation") < kinds.index("derived")
    # "客户订单" is a rollup via-bridge -> its reverse must precede Derived
    rev_idx = ids.index("relation_reverse:订单.客户")
    assert rev_idx < kinds.index("derived"), \
        "bridge reverse relation must build before derived fields"

    # a reverse NOT used as a bridge moves AFTER derived
    design2 = {
        "app": {"name": "Y"},
        "worksheets": [
            {"name": "费用", "fields": [
                {"type": "Text", "name": "费用号", "is_title": True},
                {"type": "Rollup", "name": "明细合计",
                 "rollup": {"via": "明细", "field": "金额", "aggregate": "sum"}},
                {"type": "SubTable", "name": "明细", "child_fields": [
                    {"type": "Number", "name": "金额"}]},
                {"type": "Relation", "name": "项目",
                 "relation": {"worksheet": "项目", "multi": False,
                              "two_way": {"name": "费用清单", "display": "tab_table",
                                          "show_fields": ["费用号", "明细合计"]}}},
            ]},
            {"name": "项目", "fields": [
                {"type": "Text", "name": "项目名", "is_title": True}]},
        ],
    }
    steps2 = compiler.compile_design(design2)
    kinds2 = [s.kind for s in steps2]
    ids2 = [s.id for s in steps2]
    # 费用清单 is not any derived field's via -> reverse after Derived
    rev2 = ids2.index("relation_reverse:费用.项目")
    assert rev2 > max(i for i, k in enumerate(kinds2) if k == "derived"), \
        "non-bridge reverse relation must build after derived fields"


def test_amount_in_words() -> None:
    """AmountInWords (金额大写, type 25) binds a source numeric field via
    dataSource='$<source控件id>$' + advancedSetting.currencytype (ISSUE-11);
    it is a derived field built after its source, and ordered after a source
    that is itself a Rollup."""
    from scripts import fields as F
    from scripts import compiler

    assert F.categorize({"type": "AmountInWords"}) == "derived"
    c = F.amount_in_words_control("大写", source_control_id="cid1")
    assert c["type"] == 25, c
    assert c["dataSource"] == "$cid1$", c
    assert c["advancedSetting"]["currencytype"] == "0", c

    design = {"app": {"name": "X"}, "worksheets": [{"name": "单", "fields": [
        {"type": "Text", "name": "号", "is_title": True},
        {"type": "AmountInWords", "name": "大写", "source": "合计"},
        {"type": "Rollup", "name": "合计",
         "rollup": {"via": "明细", "field": "额", "aggregate": "sum"}},
        {"type": "SubTable", "name": "明细",
         "child_fields": [{"type": "Number", "name": "额"}]},
    ]}]}
    steps = compiler.compile_design(design)
    did = [s.id for s in steps if s.kind == "derived"]
    assert did.index("derived:单.合计") < did.index("derived:单.大写"), did
    from scripts import schema
    assert _vd(design) == [], _vd(design)


def test_cascade_select() -> None:
    """CascadingSelect binds a self-referencing source worksheet via a
    `cascade` config (ISSUE-11): builder emits type 29 + dataSource=source ws
    + sourceEntityName + sourceControl companion; validator requires the
    source to be self-referencing and the field to carry `cascade`."""
    from scripts import fields as F
    from scripts import schema

    assert F.categorize({"type": "CascadingSelect", "cascade": {"source": "类别"}}) == "derived"
    c = F.cascade_control("级联", source_worksheet_id="wsCat",
                          source_entity_name="类别", show_control_ids=["c1"])
    assert c["type"] == 29, c
    assert c["dataSource"] == "wsCat", c
    assert c["sourceEntityName"] == "类别" and c["sourceControlType"] == 2, c
    assert isinstance(c.get("sourceControl"), dict), c
    assert c["showControls"] == ["c1"], c

    # bare CascadingSelect (no cascade) -> schema requires cascade
    bad = {"app": {"name": "X"}, "worksheets": [{"name": "主", "fields": [
        {"type": "Text", "name": "标题", "is_title": True},
        {"type": "CascadingSelect", "name": "级联"}]}]}
    assert any("cascade" in e for e in _vd(bad)), _vd(bad)

    # cascade.source must be self-referencing
    nonself = {"app": {"name": "X"}, "worksheets": [
        {"name": "类别", "fields": [{"type": "Text", "name": "名称", "is_title": True}]},
        {"name": "主", "fields": [
            {"type": "Text", "name": "标题", "is_title": True},
            {"type": "CascadingSelect", "name": "级联",
             "cascade": {"source": "类别", "show_fields": ["名称"]}}]}]}
    assert any("self-referencing" in e for e in _vd(nonself)), \
        _vd(nonself)

    # valid: source has a self-relation
    good = {"app": {"name": "X"}, "worksheets": [
        {"name": "类别", "fields": [
            {"type": "Text", "name": "名称", "is_title": True},
            {"type": "Relation", "name": "上级类别",
             "relation": {"worksheet": "类别", "multi": False}}]},
        {"name": "主", "fields": [
            {"type": "Text", "name": "标题", "is_title": True},
            {"type": "CascadingSelect", "name": "级联",
             "cascade": {"source": "类别", "show_fields": ["名称"]}}]}]}
    assert _vd(good) == [], _vd(good)


def test_size_snap() -> None:
    """Only 3/6/12 are real column widths; any other size the model emits is
    snapped to the nearest valid one so layout never breaks (ISSUE-14)."""
    from scripts._hapmeta import worksheet_templates as wt
    from scripts import fields as F
    # build_control snaps the wire size
    assert wt.build_control("TEXT", "a", size=4)["size"] == 3
    assert wt.build_control("TEXT", "b", size=8)["size"] == 6
    assert wt.build_control("TEXT", "c", size=9)["size"] == 12
    assert wt.build_control("TEXT", "d", size=6)["size"] == 6   # valid passes
    # apply_attrs (cross-sheet relations/rollups) snaps too
    ctrl = {"type": 29}
    F.apply_attrs(ctrl, {"size": 8})
    assert ctrl["size"] == 6, ctrl
    # schema accepts a non-enum size now (snapped at build time)
    from scripts import schema
    design = {"app": {"name": "X"}, "worksheets": [{"name": "t", "fields": [
        {"type": "Text", "name": "n", "is_title": True, "size": 4}]}]}
    assert _vd(design) == [], _vd(design)


def test_compiler_derived_topo_order() -> None:
    """Derived fields build in dependency order (BUILD-12): a Rollup that
    aggregates another Rollup (Rollup-of-Rollup, across worksheets) is
    emitted AFTER the rollup it depends on — even when document order lists
    the dependent first."""
    from scripts import compiler

    design = {
        "app": {"name": "X"},
        "worksheets": [
            {"name": "教练", "fields": [
                {"type": "Text", "name": "姓名", "is_title": True},
                # accumulates 私教订单.课时数 (a rollup) via reverse "教练订单"
                {"type": "Rollup", "name": "累计课时",
                 "rollup": {"via": "教练订单", "field": "课时数", "aggregate": "sum"}},
            ]},
            {"name": "私教订单", "fields": [
                {"type": "Text", "name": "单号", "is_title": True},
                {"type": "Rollup", "name": "课时数",
                 "rollup": {"via": "明细", "field": "课时", "aggregate": "sum"}},
                {"type": "SubTable", "name": "明细", "child_fields": [
                    {"type": "Number", "name": "课时"}]},
                {"type": "Relation", "name": "服务教练",
                 "relation": {"worksheet": "教练", "multi": False,
                              "two_way": {"name": "教练订单"}}},
            ]},
        ],
    }
    steps = compiler.compile_design(design)
    did = [s.id for s in steps if s.kind == "derived"]
    # document order lists 教练.累计课时 first, but it depends on 私教订单.课时数
    assert did.index("derived:私教订单.课时数") < did.index("derived:教练.累计课时"), did


def test_seed() -> None:
    from scripts.store import Store
    from scripts.seed.template import build_fill_template
    from scripts.seed.executor import seed_app

    d = Path(tempfile.mkdtemp()) / "appSeed"
    s = Store(d)
    s.put_app("appSeed", "Seed", "org1", [{"id": "sec1", "name": "数据"}])
    s.put_entity("worksheet", "wsM", "物料", {"name": "物料"})
    s.put_entity("worksheet", "wsK", "库存", {"name": "库存"})
    # 物料: Text(title) + Dropdown(options) + AutoNumber/Rollup/Barcode (skipped).
    s.put_controls("wsM", [
        {"controlId": "m_code", "controlName": "编码", "type": 33, "attribute": 1},
        {"controlId": "m_name", "controlName": "名称", "type": 2},
        {"controlId": "m_unit", "controlName": "单位", "type": 11,
         "options": [{"key": "k1", "value": "个"}, {"key": "k2", "value": "箱"},
                     {"key": "k3", "value": "废", "isDeleted": True}]},
        {"controlId": "m_roll", "controlName": "库存量", "type": 37},
        {"controlId": "m_bar", "controlName": "条码", "type": 47},
    ])
    # 库存: Number + forward Relation(->物料) + reverse Relation (the
    # server-generated half of a two-way pair, dropped) + SubTable(明细)
    # whose child Relation(->物料) expands to childFields.
    #
    # The two halves mirror a real capture: BOTH are bidirectional, but the
    # forward's sourceControlId resolves to its partner (k_rev) while the
    # reverse's is a dangling placeholder. enumDefault is the cardinality
    # (forward single=1 here), NOT the direction — so it can't discriminate.
    s.put_controls("wsK", [
        {"controlId": "k_qty", "controlName": "数量", "type": 6},
        {"controlId": "k_rel", "controlName": "物料", "type": 29,
         "dataSource": "wsM", "enumDefault": 1,
         "advancedSetting": {"bidirectional": "1"}, "sourceControlId": "k_rev"},
        {"controlId": "k_rev", "controlName": "相关库存", "type": 29,
         "dataSource": "wsM", "enumDefault": 2,
         "advancedSetting": {"bidirectional": "1"},
         "sourceControlId": "dangling_placeholder"},
        {"controlId": "k_sub", "controlName": "明细", "type": 34,
         "relationControls": [
             {"controlId": "c_m", "controlName": "物料", "type": 29, "dataSource": "wsM"},
             {"controlId": "c_n", "controlName": "数量", "type": 6},
             {"controlId": "c_auto", "controlName": "序号", "type": 33},
         ]},
    ])

    tmpl = {t["worksheetName"]: t for t in build_fill_template(s)}
    m_fields = {f["name"]: f for f in tmpl["物料"]["fillableFields"]}
    assert set(m_fields) == {"名称", "单位"}, set(m_fields)
    assert m_fields["名称"].get("isTitle") is True        # Text fallback title
    assert m_fields["单位"]["validOptions"] == ["个", "箱"]  # deleted option dropped
    k_fields = {f["name"]: f for f in tmpl["库存"]["fillableFields"]}
    assert set(k_fields) == {"数量", "物料", "明细"}, set(k_fields)  # reverse relation dropped
    assert k_fields["物料"]["dataSource"] == "物料"
    assert k_fields["物料"]["multi"] is False  # forward single relation surfaces cardinality
    assert tmpl["库存"]["relationDeps"] == ["物料"]
    # SubTable child expansion: AutoNumber(序号) dropped, Relation child kept.
    child_names = {f["name"] for f in k_fields["明细"]["childFields"]}
    assert child_names == {"物料", "数量"}, child_names

    # Executor: topo order (物料 before 库存) + @ref + @me resolution.
    calls = []
    seq = iter(range(1, 100))

    class _R:
        def __init__(self, data):
            self.data = data

    def fake_run(argv):
        ri = argv.index("--rows")
        wsid = argv[ri - 1]
        payload = json.loads(argv[ri + 1])
        ids = [f"row{next(seq)}" for _ in payload]
        calls.append((wsid, payload, ids))
        return _R({"rowIds": ids})

    data = {
        "库存": [{"数量": 10, "物料": "@M1"}],
        "物料": [{"_ref": "M1", "名称": "螺丝", "单位": "个"}],
    }
    res = seed_app(s, data, hap_run=fake_run, me_id="ACC")
    assert calls[0][0] == "wsM", "物料 must seed before 库存"
    assert calls[1][1][0]["物料"] == "row1", calls[1][1][0]
    assert res["total"] == 2


def test_seed_self_relation_tree() -> None:
    """A self-relation (tree) table seeds at ARBITRARY depth: each node is
    created only after its parent, with the @ref resolved to the parent's
    real rowId. (The old two-phase logic capped trees at 2 levels.)"""
    from scripts.store import Store
    from scripts.seed.executor import seed_app

    d = Path(tempfile.mkdtemp()) / "appTree"
    s = Store(d)
    s.put_app("appTree", "Tree", "org1", [{"id": "sec1", "name": "S"}])
    s.put_entity("worksheet", "wsD", "部门", {"name": "部门"})
    # 名称(Text title) + 上级(Relation -> 部门 itself = self relation).
    s.put_controls("wsD", [
        {"controlId": "d_name", "controlName": "名称", "type": 2, "attribute": 1},
        {"controlId": "d_parent", "controlName": "上级", "type": 29,
         "dataSource": "wsD", "enumDefault": 1},
    ])

    calls = []
    seq = iter(range(1, 100))

    class _R:
        def __init__(self, data):
            self.data = data

    def fake_run(argv):
        ri = argv.index("--rows")
        wsid = argv[ri - 1]
        payload = json.loads(argv[ri + 1])
        ids = [f"row{next(seq)}" for _ in payload]
        calls.append((wsid, payload, ids))
        return _R({"rowIds": ids})

    # 4-level chain (deliberately out of order to prove layering, not input order).
    data = {"部门": [
        {"_ref": "L3", "名称": "三级", "上级": "@L2"},
        {"_ref": "L1", "名称": "一级(根)"},
        {"_ref": "L4", "名称": "四级", "上级": "@L3"},
        {"_ref": "L2", "名称": "二级", "上级": "@L1"},
    ]}
    res = seed_app(s, data, hap_run=fake_run, me_id="ACC")
    assert res["total"] == 4, res

    # Map each created row's name -> its assigned rowId, and name -> parent cell.
    name_to_id, name_to_parent = {}, {}
    for _wsid, payload, ids in calls:
        for row, rid in zip(payload, ids):
            name_to_id[row["名称"]] = rid
            name_to_parent[row["名称"]] = row.get("上级")
    # Root has no parent; each deeper level's 上级 == its parent's real rowId.
    assert name_to_parent["一级(根)"] in (None, "", [])
    assert name_to_parent["二级"] == name_to_id["一级(根)"], name_to_parent
    assert name_to_parent["三级"] == name_to_id["二级"], name_to_parent
    assert name_to_parent["四级"] == name_to_id["三级"], name_to_parent
    # Layered creation: root created before L2 before L3 before L4.
    order = [r["名称"] for _w, payload, _i in calls for r in payload]
    assert order.index("一级(根)") < order.index("二级") < order.index("三级") < order.index("四级"), order


def test_workflow_dsl() -> None:
    from scripts.store import Store
    from scripts import workflow_dsl as W

    d = Path(tempfile.mkdtemp()) / "appWf"
    s = Store(d)
    s.put_app("appWf", "Wf", "org1", [{"id": "sec1", "name": "S"}])
    s.put_entity("worksheet", "WS", "出库单", {"name": "出库单"})
    s.put_entity("role", "R1", "仓库主管", {"name": "仓库主管"})
    s.put_controls("WS", [
        {"controlId": "c_status", "controlName": "单据状态", "type": 11,
         "options": [{"key": "k_ing", "value": "审批中"}]},
        {"controlId": "c_prio", "controlName": "优先级", "type": 11,
         "options": [{"key": "k_urgent", "value": "加急"}]},
        {"controlId": "c_qty", "controlName": "出库总数量", "type": 6},
    ])
    nodes = [
        {"nodeAlias": "set_ing", "nodeType": "update_record",
         "config": {"fields": [{"fieldId": "出库单/单据状态", "type": 11, "fieldValue": "审批中"}]}},
        {"nodeAlias": "route", "nodeType": "branch", "config": {"paths": [
            {"alias": "u", "condition": {"logic": "and", "items": [
                {"left": {"kind": "field", "node": {"nodeAlias": "trigger"}, "fieldId": "出库单/优先级"},
                 "op": "eq", "right": {"kind": "literal", "value": "加急"}}]},
             "nodes": [{"nodeAlias": "cc1", "nodeType": "cc",
                        "config": {"accounts": [{"kind": "role", "role": "仓库主管"}],
                                   "content": "$trigger-出库单/出库总数量$"}}]}]}},
    ]
    out = W.translate_nodes(s, nodes)
    patch = out[0]["config"]["fields"][0]
    assert patch["fieldId"] == "c_status" and patch["fieldValue"] == "k_ing", patch
    item = out[1]["config"]["paths"][0]["condition"]["items"][0]
    assert item["left"]["fieldId"] == "c_prio", item
    # condition option literal -> FULL option object (branch wire needs it)
    assert item["right"]["value"] == {"key": "k_urgent", "value": "加急",
                                      "isDeleted": False, "score": 0, "index": 0}, item
    cc = out[1]["config"]["paths"][0]["nodes"][0]["config"]
    assert cc["accounts"][0]["roleId"] == "R1", cc
    assert cc["content"] == "$trigger-c_qty$", cc  # alias kept, field resolved


def test_workflow_schema() -> None:
    from scripts import schema
    base = {"app": {"name": "x"},
            "workflows": [{"name": "wf", "trigger": {"type": "record_update", "worksheet": "出库单"}, "nodes": []}]}

    def _with(nodes):
        d = json.loads(json.dumps(base))
        d["workflows"][0]["nodes"] = nodes
        return d

    # Positive: data + branch + sub_process(get_single, nested condition) validates.
    good = _with([
        {"nodeAlias": "u", "nodeType": "update_record",
         "config": {"target": {"kind": "record", "node": {"nodeAlias": "trigger"}},
                    "fields": [{"fieldId": "出库单/单据状态", "value": "审批中"}]}},
        {"nodeAlias": "b", "nodeType": "branch", "config": {"paths": [
            {"alias": "p", "condition": {"items": [
                {"left": {"kind": "field", "node": {"nodeAlias": "trigger"}, "fieldId": "出库单/优先级"},
                 "op": "eq", "right": {"kind": "literal", "value": "加急"}}]},
             "nodes": [{"nodeAlias": "c", "nodeType": "cc",
                        "config": {"accounts": [{"kind": "role", "role": "仓库主管"}], "content": "hi"}}]}]}},
        {"nodeAlias": "sp", "nodeType": "sub_process", "config": {"process": {"nodes": [
            {"nodeAlias": "g", "nodeType": "get_single",
             "config": {"worksheet": "库存", "filter": {"items": [
                 {"left": {"kind": "field", "node": {"nodeAlias": "g"}, "fieldId": "库存/物料"},
                  "op": "eq", "right": {"kind": "field", "node": {"nodeAlias": "sub_trigger"}, "fieldId": "出库明细/物料"}}]}}}]}}},
    ])
    assert _vd(good) == [], _vd(good)
    # Negatives: branch without paths / bad op / role account missing role.
    assert _vd(_with([{"nodeAlias": "b", "nodeType": "branch", "config": {}}]))
    assert _vd(_with([{"nodeAlias": "b", "nodeType": "branch", "config": {"paths": [
        {"nodes": [], "condition": {"items": [
            {"left": {"kind": "field", "node": {"nodeAlias": "t"}, "fieldId": "a/b"}, "op": "ge"}]}}]}}]))
    assert _vd(_with([{"nodeAlias": "c", "nodeType": "cc",
                                          "config": {"accounts": [{"kind": "role"}]}}]))


def test_filter_field_map() -> None:
    """One page-filter item maps to differently-named columns per worksheet
    via field_map (e.g. a single date picker driving 入库单/入库日期 and
    出库单/出库日期), producing one filter with per-chart controlIds."""
    from scripts import charts as CH

    chart_map = {
        "入库总数": {"objectId": "o1", "worksheetId": "wsIn", "worksheet": "入库单"},
        "出库总数": {"objectId": "o2", "worksheetId": "wsOut", "worksheet": "出库单"},
        "物料数": {"objectId": "o3", "worksheetId": "wsMat", "worksheet": "物料"},
    }
    ctrls = {("wsIn", "入库日期"): {"controlId": "cIn", "type": 15},
             ("wsOut", "出库日期"): {"controlId": "cOut", "type": 15}}

    def resolve(wsid, field):
        c = ctrls.get((wsid, field))
        if not c:
            raise KeyError(field)
        return c

    comp = CH.filter_component(
        filter_bar={"name": "日期", "filters": [
            {"name": "单据日期",
             "field_map": {"入库单": "入库日期", "出库单": "出库日期"}}]},
        name="日期", layout={"x": 0, "y": 0, "w": 48, "h": 3},
        chart_map=chart_map, resolve_control=resolve)
    flt = comp["filtersGroup"]["filters"][0]
    ocs = {o["name"]: o["controlId"] for o in flt["objectControls"]}
    # binds inbound->入库日期 + outbound->出库日期; 物料 (no mapping) is skipped.
    assert ocs == {"入库总数": "cIn", "出库总数": "cOut"}, ocs
    assert flt["dataType"] == 15 and flt["filterType"] == 17, flt  # date_is
    assert flt["name"] == "单据日期"


def test_ranking_sort_and_limit() -> None:
    """A ranking (TopChart) must sort by its metric value descending and
    honour `limit` as a TopN cap — mirrors pd-openweb Statistics/common.js
    (sorts=[{yaxis0:2}], style.topStyle='crown', displaySetup.showXAxisCount).
    A non-ranking chart with `limit` only sets showXAxisCount, never sorts."""
    from scripts import charts as CH
    from scripts import schema

    ctrls = {"门店": {"controlId": "cDim", "type": 2},
             "订单金额": {"controlId": "cAmt", "type": 6}}

    def resolve(field):
        if field == "count":
            return {"controlId": "record_count", "type": 10000000}
        return ctrls[field]

    rank = CH.chart_spec(
        {"report_type": "ranking", "dimensions": [{"field": "门店"}],
         "metrics": [{"field": "订单金额", "aggregate": "sum"}], "limit": 10},
        view_id="v1", resolve=resolve)
    assert rank["sorts"] == [{"cAmt": 2}], rank["sorts"]            # value desc
    assert rank["displaySetup"]["showXAxisCount"] == 10, rank["displaySetup"]
    assert rank["style"].get("topStyle") == "crown", rank["style"]

    # explicit ascending override
    rank_asc = CH.chart_spec(
        {"report_type": "ranking", "dimensions": [{"field": "门店"}],
         "metrics": [{"field": "订单金额", "aggregate": "sum"}], "sort": "asc"},
        view_id="v1", resolve=resolve)
    assert rank_asc["sorts"] == [{"cAmt": 1}], rank_asc["sorts"]

    # a bar chart with limit gets the cap but no auto value-sort
    bar = CH.chart_spec(
        {"report_type": "bar", "dimensions": [{"field": "门店"}],
         "metrics": [{"field": "订单金额", "aggregate": "sum"}], "limit": 5},
        view_id="v1", resolve=resolve)
    assert bar["displaySetup"]["showXAxisCount"] == 5
    assert bar["sorts"] == []

    # schema accepts the `limit` key on a chart component
    design = {
        "app": {"name": "X"},
        "worksheets": [{"name": "店", "fields": [
            {"type": "Text", "name": "名", "is_title": True},
            {"type": "Number", "name": "额"}]}],
        "custom_pages": [{"name": "p", "components": [{
            "type": "chart", "name": "排行", "chart": {
                "worksheet": "店", "report_type": "ranking",
                "dimensions": [{"field": "名"}],
                "metrics": [{"field": "额", "aggregate": "sum"}],
                "limit": 10, "sort": "desc"}}]}],
    }
    assert _vd(design) == [], _vd(design)


def test_view_role_field_references() -> None:
    """Field-level reference + type completeness (ISSUE-07/08/13): view
    field slots (group_by/dates/hierarchy_field/...) and role field/view
    refs must resolve; date slots must be Date/DateTime; a self-hierarchy
    field must be a self-relation."""
    from scripts import schema
    import copy
    base = {"app": {"name": "X"}, "worksheets": [
        {"name": "任务", "fields": [
            {"type": "Text", "name": "标题", "is_title": True},
            {"type": "Date", "name": "开始日"},
            {"type": "SingleSelect", "name": "状态", "options": ["A", "B"]},
            {"type": "Relation", "name": "上级",
             "relation": {"worksheet": "任务", "multi": False}},
        ]},
    ]}

    def errs(views=None, roles=None):
        d = copy.deepcopy(base)
        if views is not None:
            d["views"] = views
        if roles is not None:
            d["roles"] = roles
        return _vd(d)

    # group_by names a missing field
    e = errs(views=[{"worksheet": "任务", "name": "v", "view_type": "kanban",
                     "group_by": "不存在"}])
    assert any("不存在" in x for x in e), e
    # calendar date slot pointing at a non-date field
    e = errs(views=[{"worksheet": "任务", "name": "c", "view_type": "calendar",
                     "dates": [{"start": "标题"}]}])
    assert any("标题" in x for x in e), e
    # hierarchy_field that is not a self-relation
    e = errs(views=[{"worksheet": "任务", "name": "h", "view_type": "hierarchy",
                     "hierarchy_field": "状态", "hierarchy_type": "self"}])
    assert any("状态" in x for x in e), e
    # role field ref that doesn't exist
    e = errs(roles=[{"name": "r", "permission_scope": "0",
                     "worksheet_permissions": [
                         {"worksheet": "任务", "fields": [{"field": "没有此字段"}]}]}])
    assert any("没有此字段" in x for x in e), e
    # all-valid design passes clean
    ok = errs(
        views=[{"worksheet": "任务", "name": "日历", "view_type": "calendar",
                "dates": [{"start": "开始日"}]},
               {"worksheet": "任务", "name": "层级", "view_type": "hierarchy",
                "hierarchy_field": "上级", "hierarchy_type": "self"},
               {"worksheet": "任务", "name": "看板", "view_type": "kanban",
                "group_by": "状态",
                "card": {"title": "标题", "display_fields": ["状态"]}}],
        roles=[{"name": "r", "permission_scope": "0",
                "worksheet_permissions": [
                    {"worksheet": "任务", "fields": [{"field": "状态"}],
                     "views": [{"view": "看板"}]}]}])
    assert ok == [], ok


def test_view_actions_reference() -> None:
    """A view.actions entry must name a custom_action defined on that view's
    worksheet. This catches a naming drift between the (parallel-authored)
    views part and custom_actions part at merge/validate time, BEFORE build.
    Lenient: a views-only fragment (no custom_actions at all) is NOT flagged.
    """
    base = {"app": {"name": "X"}, "worksheets": [
        {"name": "图书", "fields": [
            {"type": "Text", "name": "书名", "is_title": True}]}]}

    # views-only fragment: no custom_actions defined -> NOT flagged (isolation)
    frag = dict(base, views=[{"worksheet": "图书", "name": "全部",
                              "view_type": "table", "actions": ["归还"]}])
    assert not any("actions" in e and "归还" in e for e in _vd(frag)), \
        "views-only fragment must not false-flag a missing action"

    # merged: worksheet HAS actions but the view references a wrong name -> flag
    bad = dict(base,
               custom_actions=[{"worksheet": "图书", "name": "归还书籍",
                                "type": "update_record",
                                "update_fields": ["书名"]}],
               views=[{"worksheet": "图书", "name": "全部", "view_type": "table",
                       "actions": ["归还"]}])  # typo: 归还 vs 归还书籍
    e = _vd(bad)
    assert any("actions" in x and "归还" in x for x in e), e

    # merged + matching name -> clean
    good = dict(base,
                custom_actions=[{"worksheet": "图书", "name": "归还",
                                 "type": "update_record",
                                 "update_fields": ["书名"]}],
                views=[{"worksheet": "图书", "name": "全部", "view_type": "table",
                        "actions": ["归还"]}])
    assert _vd(good) == [], _vd(good)


def test_embedded_view_reference() -> None:
    """A custom-page embedded view must name a view defined for that
    worksheet (BUILD-10). Referencing the default '全部' when the worksheet
    only has custom views (so '全部' was never created) is rejected at
    validate time instead of failing at build."""
    from scripts import schema

    design = {
        "app": {"name": "X"},
        "worksheets": [{"name": "任务", "fields": [
            {"type": "Text", "name": "标题", "is_title": True}]}],
        "views": [{"worksheet": "任务", "name": "任务列表", "view_type": "table"}],
        "custom_pages": [{"name": "p", "components": [
            {"type": "view", "name": "嵌入",
             "view": {"worksheet": "任务", "view": "全部"}}]}],
    }
    errs = _vd(design)
    assert any("全部" in e and "view" in e.lower() for e in errs), errs

    # naming a view that IS defined for the worksheet passes
    design["custom_pages"][0]["components"][0]["view"]["view"] = "任务列表"
    assert _vd(design) == [], _vd(design)


def test_merge_designs() -> None:
    """Split-generation: independently-authored parts merge into one whole.
    `app` is single-owner; array sections concatenate; cross-part duplicate
    names and conflicting app blocks are rejected."""
    from scripts import schema
    from scripts.errors import DesignError

    foundation = {"app": {"name": "X"},
                  "worksheets": [{"name": "客户",
                                  "fields": [{"type": "Text", "name": "名称",
                                              "is_title": True}]}]}
    part_roles = {"roles": [{"name": "管理员", "permission_scope": "0"}]}
    part_wf = {"workflows": [{"name": "wf",
                              "trigger": {"type": "record_create", "worksheet": "客户"},
                              "nodes": []}]}
    merged = schema.merge_designs([foundation, part_roles, part_wf])
    assert merged["app"]["name"] == "X"
    assert [w["name"] for w in merged["worksheets"]] == ["客户"]
    assert [r["name"] for r in merged["roles"]] == ["管理员"]
    assert [w["name"] for w in merged["workflows"]] == ["wf"]
    # The merged whole validates (cross-part: wf references foundation's 客户).
    assert _vd(merged) == [], _vd(merged)

    # Conflicting app blocks across parts -> error.
    try:
        schema.merge_designs([{"app": {"name": "A"}}, {"app": {"name": "B"}}])
        assert False, "expected conflicting-app error"
    except DesignError:
        pass
    # Duplicate logical name across parts -> error.
    try:
        schema.merge_designs([{"app": {"name": "A"}, "roles": [{"name": "R"}]},
                              {"roles": [{"name": "R"}]}])
        assert False, "expected duplicate-name error"
    except DesignError:
        pass
    # No app part at all -> error.
    try:
        schema.merge_designs([{"roles": [{"name": "R"}]}])
        assert False, "expected missing-app error"
    except DesignError:
        pass


def test_filter_extensions() -> None:
    """build_filter_conditions: ``in``/``notin``/``is`` aliases, single-dict
    tolerance, and condition groups (isGroup + groupFilters)."""
    from scripts import fields as F

    opt = {"controlId": "c1", "type": 9,
           "options": [{"value": "待整改", "key": "k1"},
                       {"value": "整改中", "key": "k2"}]}
    resolve = lambda name: opt
    # in -> filterType 2 + option keys in values
    out = F.build_filter_conditions(
        [{"field": "状态", "op": "in", "value": ["待整改", "整改中"]}], resolve)
    assert out[0]["filterType"] == 2 and out[0]["values"] == ["k1", "k2"], out
    # notin -> filterType 6
    out = F.build_filter_conditions(
        [{"field": "状态", "op": "notin", "values": ["待整改"]}], resolve)
    assert out[0]["filterType"] == 6 and out[0]["values"] == ["k1"], out
    # is -> eq
    out = F.build_filter_conditions(
        [{"field": "状态", "op": "is", "value": "待整改"}], resolve)
    assert out[0]["filterType"] == 2, out
    # a single condition object (not wrapped in a list) is tolerated
    out = F.build_filter_conditions(
        {"field": "状态", "op": "eq", "value": "待整改"}, resolve)
    assert len(out) == 1 and out[0]["isGroup"] is False, out
    # condition group -> isGroup:true + groupFilters[]
    out = F.build_filter_conditions([{
        "join": "or", "group_join": "and",
        "conditions": [{"field": "状态", "op": "eq", "value": "待整改"},
                       {"field": "状态", "op": "eq", "value": "整改中"}]}], resolve)
    assert out[0]["isGroup"] is True and out[0]["spliceType"] == 2, out
    assert len(out[0]["groupFilters"]) == 2, out


def test_schema_extensions() -> None:
    """Schema/validator extensions: rollup node friendly DSL, system value in
    a condition, chart filters alias, and reference-integrity checks."""
    from scripts import schema

    base_app = {"app": {"name": "压测", "sections": ["S"]},
                "worksheets": [{"name": "W", "section": "S", "fields": [
                    {"type": "Text", "name": "标题", "is_title": True},
                    {"type": "Date", "name": "到期日"}]}]}
    sched = {"type": "scheduled",
             "schedule": {"repeat": "day", "start_time": "2026-01-01 09:00"}}

    # rollup node: lowercase ``aggregate`` + ``data_source`` accepted.
    wf = {**base_app, "workflows": [{"name": "wf1", "trigger": sched, "nodes": [
        {"nodeAlias": "g", "nodeType": "get_multiple", "config": {"worksheet": "W"}},
        {"nodeAlias": "r", "nodeType": "rollup", "config": {
            "mode": "worksheet",
            "data_source": {"kind": "record", "node": {"nodeAlias": "g"}},
            "aggregations": [{"alias": "cnt", "aggregate": "count"}]}}]}]}
    assert not _vd(wf), _vd(wf)

    # system value as a condition right.
    wf2 = {**base_app, "workflows": [{"name": "wf2", "trigger": sched, "nodes": [
        {"nodeAlias": "g", "nodeType": "get_multiple", "config": {
            "worksheet": "W",
            "filter": {"items": [{"left": {"kind": "field",
                                            "node": {"nodeAlias": "g"},
                                            "fieldId": "W/到期日"},
                                  "op": "lt",
                                  "right": {"kind": "system", "field": "now"}}]}}}]}]}
    assert not _vd(wf2), _vd(wf2)

    # chart filters alias accepting a single condition object.
    cp = {**base_app, "custom_pages": [{"name": "看板", "section": "S",
        "components": [{"type": "chart", "name": "c", "chart": {
            "worksheet": "W", "report_type": "number",
            "filters": {"field": "标题", "op": "eq", "value": "x"}}}]}]}
    assert not _vd(cp), _vd(cp)

    # reference check: a page section not in app.sections is flagged.
    bad = {**base_app, "custom_pages": [{"name": "P", "section": "不存在"}]}
    errs = _vd(bad)
    assert any("section '不存在'" in e for e in errs), errs
    # reference check: a relation pointing at a missing worksheet is flagged.
    bad2 = {"app": {"name": "压测", "sections": ["S"]},
            "worksheets": [{"name": "W", "section": "S", "fields": [
                {"type": "Text", "name": "标题", "is_title": True},
                {"type": "Relation", "name": "关联",
                 "relation": {"worksheet": "没有这表"}}]}]}
    errs = _vd(bad2)
    assert any("没有这表" in e for e in errs), errs

    # reference check: a workflow approver role not defined in roles[] is flagged
    # (only when roles[] is present — a workflow-only fragment is not checked).
    bad3 = {**base_app,
            "roles": [{"name": "审批人", "permission_scope": "0"}],
            "workflows": [{"name": "wf3", "trigger": {"type": "button"}, "nodes": [
                {"nodeAlias": "ap", "nodeType": "approval_block", "config": {
                    "process": {"nodes": [
                        {"nodeAlias": "a", "nodeType": "approve", "config": {
                            "accounts": [{"kind": "role", "role": "运营总监"}]}}]}}}]}]}
    errs = _vd(bad3)
    assert any("运营总监" in e for e in errs), errs


def test_workflow_formula_refs() -> None:
    """A rollup/compute node's result is referenced by ``number_fx_id``:
    branch conditions and notice templates that target a formula alias resolve
    to it (instead of the author's placeholder field). Ground truth: saveNode
    captures (rollup-from-node / rollup-from-worksheet; notice $-number_fx_id$)."""
    from scripts import workflow_dsl as WD

    # _collect_formula_actions: data_source -> 105 (object), else worksheet 107.
    nodes = [
        {"nodeAlias": "g", "nodeType": "get_multiple", "config": {"worksheet": "W"}},
        {"nodeAlias": "c", "nodeType": "rollup",
         "config": {"data_source": {"kind": "record", "node": {"nodeAlias": "g"}}}},
        {"nodeAlias": "d", "nodeType": "rollup", "config": {"worksheet": "W"}},
    ]
    fa = WD._collect_formula_actions(nodes)
    assert fa == {"c": "105", "d": "107"}, fa

    # template(): a $alias-结果$ token on a formula alias -> $alias-number_fx_id$.
    r = WD._Resolver(store=None)
    r.formula_actions = {"cnt": "105"}
    assert r.template("有 $cnt-结果$ 条") == "有 $cnt-number_fx_id$ 条", r.template("$cnt-结果$")
    assert r.template("$cnt-加油条数$") == "$cnt-number_fx_id$"

    # _condition_item(): a branch comparing a formula alias result -> number_fx_id
    # wire hints (filedTypeId 6, node nodeType 9 / appType 11 / actionId).
    cond = WD._condition_item(
        {"left": {"kind": "field", "node": {"nodeAlias": "cnt"}, "fieldId": "count"},
         "op": "gt", "right": {"kind": "literal", "value": "0"}}, r)
    assert cond["left"]["fieldId"] == "number_fx_id", cond["left"]
    assert cond["left"]["_filedTypeId"] == 6
    assert cond["left"]["node"]["_nodeType"] == 9
    assert cond["left"]["node"]["_appType"] == 11
    assert cond["left"]["node"]["_actionId"] == "105"


def test_report_three_state() -> None:
    """The run report distinguishes ✅ ok / ⚠️ created-but-unfinished /
    ❌ not-created / ⏭️ skipped, and emits a 'failures to repair' section that
    carries the real id of partially-built entities (so a failed workflow can
    be fixed in place instead of rebuilt)."""
    from scripts.executor import (
        RunSummary, StepRecord, STATUS_OK, STATUS_ERR, STATUS_SKIP,
    )
    from scripts.recording.report import render_markdown, _mark

    ok = StepRecord(step_id="w1", kind="worksheet", name="客户",
                    phase="Worksheets", status=STATUS_OK, created_id="ws_1")
    # workflow created but publish failed → ⚠️ partial, id retained
    partial = StepRecord(step_id="f1", kind="workflow", name="提交审批",
                         phase="Workflows", status=STATUS_ERR,
                         created_id="proc_99", error="publish failed")
    # view never created → ❌
    notmade = StepRecord(step_id="v1", kind="view", name="看板",
                         phase="Views", status=STATUS_ERR, error="bad config")
    skipped = StepRecord(step_id="s1", kind="role", name="主管",
                         phase="Roles", status=STATUS_SKIP,
                         error="skipped: depends on failed worksheet")

    assert _mark(ok) == "✅"
    assert _mark(partial) == "⚠️", "ERR with a created_id is repairable in place"
    assert _mark(notmade) == "❌"
    assert _mark(skipped) == "⏭️"

    summ = RunSummary(run_id="r1", app_id="app_1", app_name="Demo",
                      ok=1, err=2, skip=1,
                      records=[ok, partial, notmade, skipped])
    md = render_markdown(summ, ts="t", design="d")
    assert "## 需修复项 (failures to repair)" in md
    # the partial workflow's real id must appear so repair can target it
    assert "proc_99" in md
    # the ok worksheet must NOT show up under failures (scope to the failures
    # section only — the resource-map appendix below legitimately lists it).
    fail_section = md.split("## 需修复项")[1].split("## Resource map")[0]
    assert "提交审批" in fail_section and "看板" in fail_section
    assert "客户" not in fail_section

    # a clean run says so explicitly
    clean = RunSummary(run_id="r2", app_id="a", ok=1, records=[ok])
    assert "无失败项 ✅" in render_markdown(clean, ts="t", design="d")


def test_partial_step_failure_carries_id() -> None:
    """A PartialStepFailure exposes the created id, and the executor copies it
    onto the failed step record (status err, id retained)."""
    from scripts.errors import PartialStepFailure
    from scripts.executor import Executor, STATUS_ERR
    from scripts.steps import Step, handler, _REGISTRY

    e = PartialStepFailure("boom", created_id="proc_42")
    assert e.created_id == "proc_42"

    # Register a throwaway handler that fails partially, run one step, assert
    # the record kept the id. (Restore the registry afterwards.)
    kind = "_selftest_partial"
    saved = _REGISTRY.get(kind)

    @handler(kind)
    def _boom(ctx, step):  # noqa: ANN001
        raise PartialStepFailure("created but unfinished", created_id="proc_42")

    try:
        ex = Executor({"app": {"name": "X"}}, run_id="r", org_id="o",
                      account_id="a", ts="t")
        summary = ex.run([Step(id="x", kind=kind, name="n", phase="P", spec={})])
    finally:
        if saved is not None:
            _REGISTRY[kind] = saved
        else:
            _REGISTRY.pop(kind, None)

    rec = summary.records[0]
    assert rec.status == STATUS_ERR
    assert rec.created_id == "proc_42", "partial id must survive onto the record"


def main() -> int:
    tests = [test_store, test_schema, test_fields, test_compiler,
             test_compiler_reverse_relation_ordering,
             test_compiler_derived_topo_order, test_size_snap,
             test_amount_in_words, test_cascade_select, test_seed,
             test_seed_self_relation_tree,
             test_workflow_dsl, test_workflow_schema, test_filter_field_map,
             test_ranking_sort_and_limit, test_embedded_view_reference,
             test_view_role_field_references, test_view_actions_reference,
             test_merge_designs, test_filter_extensions, test_schema_extensions,
             test_workflow_formula_refs,
             test_report_three_state, test_partial_step_failure_carries_id]
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"✗ {t.__name__}: {e}", file=sys.stderr)
            return 1
        print(f"✓ {t.__name__}")
    print(f"\nall {len(tests)} self-tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
