#!/usr/bin/env python3
"""
merge_worksheet_context.py
HAP 工作表结构分片合并与多维度强校验引擎。

功能：
  1. 读取 .build/artifacts/worksheet-{worksheetId}.json 各表分片数据；
  2. 字段类型标准化（数字枚举 → 统一英文类型）；
  3. 执行 10 项强校验规则（关系完整性、字段合法性、自洽性检查）；
  4. 生成 schema-validation.json 检验报告；
  5. 校验通过后原子输出 worksheetContext.json。

用法：
  python3 merge_worksheet_context.py <app_dir> [--shards-dir <shards_dir>]
示例：
  python3 merge_worksheet_context.py apps/个人读书与笔记
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

_PURE_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")

# HAP 数值类型到标准英文类型的映射字典
TYPE_ID_TO_NAME = {
    1: "Text",
    2: "Text",
    3: "PhoneNumber",
    4: "Email",
    5: "Number",
    6: "Number",
    8: "Currency",
    9: "SingleSelect",
    10: "MultipleSelect",
    11: "Dropdown",
    14: "Attachment",
    15: "Date",
    16: "DateTime",
    19: "Region",
    20: "Formula",
    21: "Relation",
    22: "Divider",
    24: "Location",
    25: "Formula",
    26: "Collaborator",
    27: "Department",
    28: "Rating",
    29: "Relation",
    30: "Lookup",
    31: "Formula",
    32: "Concatenate",
    33: "AutoNumber",
    34: "SubTable",
    35: "Cascader",
    36: "Checkbox",
    37: "Rollup",
    38: "DateFormula",
    41: "RichText",
    42: "Signature",
    45: "Embed",
    46: "Time",
    47: "Barcode",
    48: "OrgRole",
    50: "QueryRecord",
    53: "FormulaFunc",
    54: "CustomField",
}

SYSTEM_FIELD_IDS = {"rowid", "ownerid", "caid", "ctime", "utime", "uaid"}


def normalize_field_type(raw_type):
    """将数字或字符串字段类型标准化为统一的英文类型字符串"""
    if isinstance(raw_type, int):
        return TYPE_ID_TO_NAME.get(raw_type, f"Unknown_{raw_type}")
    if isinstance(raw_type, str):
        if raw_type.isdigit():
            return TYPE_ID_TO_NAME.get(int(raw_type), f"Unknown_{raw_type}")
        return raw_type
    return "Unknown"


def normalize_worksheet_shard(raw_data, expected_id, expected_name, name_to_id=None, fallback_opts_by_ws=None):
    """标准化单个分片数据结构（兼容 dsl 原始结构、标准分片对象或数组，并自动清洗 (isTitle) 与回填漏抄的选项 key）"""
    name_to_id = name_to_id or {}
    fallback_opts = (fallback_opts_by_ws or {}).get(expected_name, {})

    if isinstance(raw_data, dict) and isinstance(raw_data.get("data"), dict):
        raw_data = raw_data["data"]
    if isinstance(raw_data, dict) and isinstance(raw_data.get("worksheet"), dict):
        raw_data = raw_data["worksheet"]

    ws_id = (raw_data.get("worksheetId") or raw_data.get("id") or expected_id) if isinstance(raw_data, dict) else expected_id
    ws_name = (raw_data.get("worksheetName") or raw_data.get("name") or expected_name) if isinstance(raw_data, dict) else expected_name

    raw_fields = []
    if isinstance(raw_data, dict):
        if "fields" in raw_data and isinstance(raw_data["fields"], list):
            raw_fields = raw_data["fields"]
        elif "template" in raw_data and isinstance(raw_data["template"], dict):
            raw_fields = raw_data["template"].get("controls", [])
        elif "controls" in raw_data and isinstance(raw_data["controls"], list):
            raw_fields = raw_data["controls"]
    elif isinstance(raw_data, list):
        raw_fields = raw_data

    normalized_fields = []
    for f in raw_fields:
        if not isinstance(f, dict):
            continue
        raw_fid = str(f.get("controlId") or f.get("id") or f.get("fieldId") or "").strip()
        marked_title = "(isTitle)" in raw_fid
        field_id = raw_fid.replace("(isTitle)", "").strip()
        field_name = str(f.get("controlName") or f.get("name") or f.get("fieldName") or "").replace("(isTitle)", "").strip()
        raw_type = f.get("type") or f.get("fieldType") or 2
        field_type = normalize_field_type(raw_type)
        alias = f.get("alias") or ""
        marked_title = marked_title or "(isTitle)" in str(f.get("name") or f.get("controlName") or f.get("fieldName") or "")

        norm_field = {
            "id": field_id,
            "name": field_name,
            "type": field_type,
            "alias": alias,
        }
        for key in ("required", "isTitle", "isReadOnly", "isHidden", "isHiddenOnCreate",
                    "isUnique", "defaultValue", "config", "layout"):
            if key in f and f[key] is not None:
                norm_field[key] = f[key]
        if marked_title:
            norm_field["isTitle"] = True
        elif "isTitle" not in norm_field:
            if f.get("is_title") is not None:
                norm_field["isTitle"] = f["is_title"]
            elif f.get("attribute") is not None:
                norm_field["isTitle"] = f["attribute"] == 1
        if "required" not in norm_field and f.get("notNull") is not None:
            norm_field["required"] = f["notNull"]

        # 提取选项（必须完整保留 key 与 index；若分片漏抄 key 则自动从 Step 2a fieldOptionsContext 兜底回填）
        fb_map = fallback_opts.get(alias) or fallback_opts.get(field_name) or {}
        options = f.get("options")
        if options and isinstance(options, list):
            norm_options = []
            for idx, opt in enumerate(options):
                if isinstance(opt, dict):
                    val = opt.get("value") or opt.get("name") or opt.get("key") or ""
                    opt_item = {
                        **opt,
                        "value": val,
                        "isDelete": bool(opt.get("isDelete", opt.get("isDeleted", False))),
                    }
                    opt_key = opt.get("key") or fb_map.get(val)
                    if opt_key:
                        opt_item["key"] = opt_key
                    opt_item["index"] = opt["index"] if "index" in opt else idx + 1
                    norm_options.append(opt_item)
                elif isinstance(opt, str):
                    opt_item = {"value": opt, "index": idx + 1, "isDelete": False}
                    if fb_map.get(opt):
                        opt_item["key"] = fb_map[opt]
                    norm_options.append(opt_item)
            norm_field["options"] = norm_options
        elif "options" not in f and fb_map and field_type in ("SingleSelect", "MultipleSelect", "Dropdown"):
            norm_field["options"] = [
                {"key": k, "value": v, "index": i + 1, "isDelete": False}
                for i, (v, k) in enumerate(fb_map.items())
            ]

        # 提取关联元数据（支持把表名归一化为真实 worksheetId，保留 selfRelation）
        cfg = f.get("config") if isinstance(f.get("config"), dict) else {}
        data_source = f.get("dataSource") or f.get("relationWorksheetId") or cfg.get("dataSource") or ""
        if data_source in name_to_id:
            data_source = name_to_id[data_source]
        if data_source:
            norm_field["dataSource"] = data_source

        relation_field = f.get("relationField") or f.get("relationControlId") or cfg.get("relationField") or ""
        if relation_field:
            norm_field["relationField"] = relation_field

        source_field = f.get("sourceField") or f.get("sourceControlId") or cfg.get("sourceField") or ""
        if source_field:
            norm_field["sourceField"] = source_field

        # 保留辅助信息
        if "desc" in f and f["desc"]:
            norm_field["desc"] = f["desc"]
        if "remark" in f and f["remark"]:
            norm_field["remark"] = f["remark"]
        if "placeholder" in f and f["placeholder"]:
            norm_field["placeholder"] = f["placeholder"]

        normalized_fields.append(norm_field)

    ws_alias = raw_data.get("alias", "") if isinstance(raw_data, dict) else ""
    res_shard = {
        "worksheetId": ws_id,
        "worksheetName": ws_name,
        "fields": normalized_fields,
    }
    if ws_alias:
        res_shard["alias"] = ws_alias
    return res_shard


def _invalid_object_id_reason(val):
    if not isinstance(val, str):
        return None
    s = val.strip()
    if not s or s in SYSTEM_FIELD_IDS or s == "selfRelation":
        return None
    if ("<" in s and ">" in s) or "..." in s or "…" in s:
        return f"包含未替换占位符或省略号（{s}）"
    if _PURE_HEX_RE.match(s) and len(s) >= 12 and len(s) != 24:
        return f"疑似截断的 24 位 ID（当前 {len(s)} 位：{s}）"
    return None


def validate_schema(worksheets, id_to_name, name_to_id, plan_data):
    """
    执行强校验规则（含 24 位 ID 截断/占位符检测）
    返回: (passed: bool, errors: list, warnings: list)
    """
    errors = []
    warnings = []

    # 建立全局表与字段索引
    ws_map = {}
    for ws in worksheets:
        ws_id = ws["worksheetId"]
        ws_name = ws["worksheetName"]
        ws_id_err = _invalid_object_id_reason(ws_id)
        if ws_id_err:
            errors.append({
                "worksheet": ws_name,
                "field": "",
                "code": "INVALID_OBJECT_ID",
                "message": f"工作表【{ws_name}】的 worksheetId 异常：{ws_id_err}"
            })
        fields_by_id = {}
        fields_by_alias = {}
        title_fields = []

        for f in ws.get("fields", []):
            fid = f.get("id")
            falias = f.get("alias")
            ftype = f.get("type")

            fid_err = _invalid_object_id_reason(fid)
            if fid_err:
                errors.append({
                    "worksheet": ws_name,
                    "field": f.get("name"),
                    "code": "INVALID_OBJECT_ID",
                    "message": f"工作表【{ws_name}】字段【{f.get('name')}】的字段 ID 异常：{fid_err}"
                })

            # 1. 字段 ID 重复检查
            if fid:
                if fid in fields_by_id:
                    errors.append({
                        "worksheet": ws_name,
                        "field": f.get("name"),
                        "code": "DUPLICATE_FIELD_ID",
                        "message": f"工作表【{ws_name}】中存在重复的字段 ID: {fid}"
                    })
                fields_by_id[fid] = f

            if falias:
                if falias in fields_by_alias:
                    errors.append({
                        "worksheet": ws_name,
                        "field": f.get("name"),
                        "code": "DUPLICATE_FIELD_ALIAS",
                        "message": f"工作表【{ws_name}】中存在重复的字段别名: {falias}"
                    })
                fields_by_alias[falias] = f

            # 2. 标题字段记录
            if f.get("isTitle"):
                title_fields.append(f)

            # 3. 非法类型检查
            if ftype.startswith("Unknown"):
                warnings.append({
                    "worksheet": ws_name,
                    "field": f.get("name"),
                    "code": "UNKNOWN_FIELD_TYPE",
                    "message": f"工作表【{ws_name}】字段【{f.get('name')}】类型未识别: {ftype}"
                })

            # 4. 选项重复性与有效性检查
            if ftype in ("SingleSelect", "MultipleSelect", "Dropdown") and "options" in f:
                seen_vals = set()
                for opt in f["options"]:
                    val = opt["value"]
                    if not val:
                        errors.append({
                            "worksheet": ws_name,
                            "field": f.get("name"),
                            "code": "EMPTY_OPTION_VALUE",
                            "message": f"工作表【{ws_name}】字段【{f.get('name')}】存在空的选项值"
                        })
                    elif val in seen_vals:
                        warnings.append({
                            "worksheet": ws_name,
                            "field": f.get("name"),
                            "code": "DUPLICATE_OPTION_VALUE",
                            "message": f"工作表【{ws_name}】字段【{f.get('name')}】存在重复的选项值: {val}"
                        })
                    seen_vals.add(val)

        # 5. 标题字段有且仅有一个检查
        if len(title_fields) == 0:
            warnings.append({
                "worksheet": ws_name,
                "code": "NO_TITLE_FIELD",
                "message": f"工作表【{ws_name}】未检测到显式的标题字段(isTitle)"
            })
        elif len(title_fields) > 1:
            warnings.append({
                "worksheet": ws_name,
                "code": "MULTIPLE_TITLE_FIELDS",
                "message": f"工作表【{ws_name}】存在多个标题字段: {[tf.get('name') for tf in title_fields]}"
            })

        ws_fields = ws.get("fields", [])
        if not ws_fields:
            errors.append({
                "worksheet": ws_name,
                "code": "EMPTY_WORKSHEET_FIELDS",
                "message": f"工作表【{ws_name}】分片未包含任何有效字段"
            })
        fields_by_name = {f.get("name"): f for f in ws_fields if f.get("name")}
        ws_map[ws_id] = {
            "name": ws_name,
            "fields_by_id": fields_by_id,
            "fields_by_alias": fields_by_alias,
            "fields_by_name": fields_by_name,
            "fields": ws_fields,
        }

    # 跨表关联与 Lookup/Rollup 数据源校验（放行 selfRelation，分片衍生元数据缺项记为告警不误杀已建成工作表）
    for ws in worksheets:
        ws_id = ws["worksheetId"]
        ws_name = ws["worksheetName"]
        local_fields_by_id = ws_map[ws_id]["fields_by_id"]
        local_fields_by_alias = ws_map[ws_id]["fields_by_alias"]
        local_fields_by_name = ws_map[ws_id]["fields_by_name"]

        def get_local_field(key):
            return local_fields_by_id.get(key) or local_fields_by_alias.get(key) or local_fields_by_name.get(key)

        for f in ws.get("fields", []):
            ftype = f.get("type")
            fname = f.get("name")

            # 6. Relation dataSource 校验（selfRelation 为合法本表自关联）
            if ftype in ("Relation", "SubTable"):
                ds = f.get("dataSource")
                if ds and ds != "selfRelation" and ds not in ws_map and ds not in name_to_id:
                    warnings.append({
                        "worksheet": ws_name,
                        "field": fname,
                        "code": "RELATION_DATASOURCE_UNVERIFIED",
                        "message": f"工作表【{ws_name}】关联字段【{fname}】数据源未在本应用分片内命中 (dataSource={ds})"
                    })

            # 7. Lookup / Rollup 校验（分片从 md 转写可能省略 relationField，记告警不阻断阶段推进）
            if ftype in ("Lookup", "Rollup"):
                rf_key = f.get("relationField")
                sf_key = f.get("sourceField")
                if not rf_key:
                    warnings.append({
                        "worksheet": ws_name,
                        "field": fname,
                        "code": "DERIVED_RELATION_META_OMITTED",
                        "message": f"工作表【{ws_name}】衍生字段【{fname}】分片未附带 relationField 元数据"
                    })
                    continue

                rf = get_local_field(rf_key)
                if not rf:
                    warnings.append({
                        "worksheet": ws_name,
                        "field": fname,
                        "code": "LOOKUP_RELATION_NOT_FOUND",
                        "message": f"工作表【{ws_name}】衍生字段【{fname}】关联字段未在分片内对齐 (relationField={rf_key})"
                    })
                else:
                    target_ws_id = rf.get("dataSource")
                    if target_ws_id == "selfRelation":
                        target_ws_id = ws_id
                    elif target_ws_id in name_to_id:
                        target_ws_id = name_to_id[target_ws_id]
                    if not target_ws_id or target_ws_id not in ws_map:
                        warnings.append({
                            "worksheet": ws_name,
                            "field": fname,
                            "code": "LOOKUP_TARGET_WORKSHEET_NOT_FOUND",
                            "message": f"工作表【{ws_name}】衍生字段【{fname}】目标表未在分片内对齐 (targetWs={target_ws_id})"
                        })
                    elif sf_key:
                        target_ws = ws_map[target_ws_id]
                        tf = (
                            target_ws["fields_by_id"].get(sf_key)
                            or target_ws["fields_by_alias"].get(sf_key)
                            or target_ws["fields_by_name"].get(sf_key)
                        )
                        if not tf:
                            warnings.append({
                                "worksheet": ws_name,
                                "field": fname,
                                "code": "LOOKUP_SOURCE_FIELD_NOT_FOUND",
                                "message": f"工作表【{ws_name}】的【{fname}】在目标表【{target_ws['name']}】中未直接匹配到源字段 (sourceField={sf_key})"
                            })

    passed = len(errors) == 0
    return passed, errors, warnings


def merge_and_validate_worksheet_context(app_dir_arg, shards_dir_arg=None, verbose: bool = False):
    """合并单表结构分片并执行 10 项强校验；返回 (passed: bool, error_message: str)。"""
    app_dir = Path(app_dir_arg).resolve()
    if not app_dir.exists():
        msg = f"❌ 错误: 应用目录不存在: {app_dir}"
        if verbose:
            print(msg, file=sys.stderr)
        return False, msg

    context_path = app_dir / "hap-context.json"
    plan_path = app_dir / "hap-plan.json"

    # 分片文件统一位于 .build/artifacts 目录
    if shards_dir_arg:
        shards_dir = Path(shards_dir_arg).resolve()
    else:
        shards_dir = app_dir / ".build" / "artifacts"

    if not context_path.exists():
        msg = f"❌ 错误: hap-context.json 不存在: {context_path}"
        if verbose:
            print(msg, file=sys.stderr)
        return False, msg

    with open(context_path, "r", encoding="utf-8") as f:
        context_data = json.load(f)

    plan_data = {}
    if plan_path.exists():
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)

    worksheet_id_by_name = context_data.get("worksheetIdByName", {})
    if not worksheet_id_by_name:
        msg = "❌ 错误: hap-context.json 中未找到任何 worksheetIdByName 映射"
        if verbose:
            print(msg, file=sys.stderr)
        return False, msg

    id_to_name = {v: k for k, v in worksheet_id_by_name.items()}
    name_to_id = dict(worksheet_id_by_name)

    # 构建 Step 2a 缓存的选项 key 兜底索引：{ws_name: {field_alias_or_name: {opt_value: opt_key}}}（兼容 list 与 dict 结构）
    fallback_opts_by_ws = {}
    raw_fopts = context_data.get("fieldOptionsContext") or []
    if isinstance(raw_fopts, dict):
        for comp_key, opt_list in raw_fopts.items():
            if "." in str(comp_key) and isinstance(opt_list, list):
                w_n, f_n = str(comp_key).split(".", 1)
                val_to_key = {o["value"]: o["key"] for o in opt_list if isinstance(o, dict) and o.get("value") and o.get("key")}
                if val_to_key:
                    fallback_opts_by_ws.setdefault(w_n, {})[f_n] = val_to_key
    elif isinstance(raw_fopts, list):
        for w_opt in raw_fopts:
            if not isinstance(w_opt, dict) or not w_opt.get("name"):
                continue
            f_map = {}
            for fld_opt in w_opt.get("fields", []) or []:
                if not isinstance(fld_opt, dict):
                    continue
                val_to_key = {
                    o["value"]: o["key"]
                    for o in (fld_opt.get("options") or [])
                    if isinstance(o, dict) and o.get("value") and o.get("key")
                }
                if val_to_key:
                    if fld_opt.get("alias"):
                        f_map[fld_opt["alias"]] = val_to_key
                    if fld_opt.get("name"):
                        f_map[fld_opt["name"]] = val_to_key
            if f_map:
                fallback_opts_by_ws[w_opt["name"]] = f_map

    if verbose:
        print(f"🔍 启动分片收集，预期工作表数量: {len(worksheet_id_by_name)}")
        print(f"📂 分片存储目录: {shards_dir}")

    # 1. 检查并读取所有分片
    normalized_shards = []
    missing_shards = []

    # 按照 plan 中的表顺序或 context 字典顺序合并
    ordered_ws_names = []
    if "worksheets" in plan_data and isinstance(plan_data["worksheets"], list):
        ordered_ws_names = [ws.get("name") for ws in plan_data["worksheets"] if ws.get("name") in worksheet_id_by_name]
    for name in worksheet_id_by_name:
        if name not in ordered_ws_names:
            ordered_ws_names.append(name)

    for ws_name in ordered_ws_names:
        ws_id = worksheet_id_by_name[ws_name]
        shard_file = shards_dir / f"worksheet-{ws_id}.json"

        if not shard_file.exists():
            missing_shards.append({"worksheetName": ws_name, "worksheetId": ws_id, "expectedFile": str(shard_file)})
            continue

        raw_shard = None
        last_err = None
        for attempt in range(4):
            try:
                with open(shard_file, "r", encoding="utf-8") as f:
                    raw_shard = json.load(f)
                if raw_shard is not None:
                    break
            except (json.JSONDecodeError, OSError) as e:
                last_err = e
                import time
                time.sleep(0.3)

        if raw_shard is not None:
            norm_shard = normalize_worksheet_shard(raw_shard, ws_id, ws_name, name_to_id, fallback_opts_by_ws)
            normalized_shards.append(norm_shard)
        else:
            if verbose:
                print(f"❌ 读取分片文件失败 [{shard_file}]: {last_err}", file=sys.stderr)
            missing_shards.append({"worksheetName": ws_name, "worksheetId": ws_id, "error": str(last_err)})

    # 2. 执行 10 项强校验
    passed, errors, warnings = validate_schema(normalized_shards, id_to_name, name_to_id, plan_data)

    if missing_shards:
        passed = False
        for ms in missing_shards:
            errors.append({
                "worksheet": ms.get("worksheetName"),
                "code": "MISSING_SHARD_FILE",
                "message": f"缺失工作表分片文件: {ms}"
            })

    # 3. 输出 schema-validation.json
    validation_report = {
        "passed": passed,
        "expectedWorksheetCount": len(worksheet_id_by_name),
        "actualWorksheetCount": len(normalized_shards),
        "errorsCount": len(errors),
        "warningsCount": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }

    validation_path = app_dir / "schema-validation.json"
    with open(validation_path, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, ensure_ascii=False, indent=2)

    if verbose:
        print("\n" + "=" * 50)
        print("📋 HAP 工作表结构校验与合并报告")
        print("=" * 50)
        print(f"• 预期工作表数: {len(worksheet_id_by_name)}")
        print(f"• 实际采集分片: {len(normalized_shards)}")
        print(f"• 校验状态: {'✅ 通过 (PASSED)' if passed else '❌ 拦截未通过 (FAILED)'}")
        print(f"• 阻断错误 (Errors): {len(errors)}")
        print(f"• 优化告警 (Warnings): {len(warnings)}")

        if errors:
            print("\n⛔ 阻断错误详情 (Errors):")
            for err in errors:
                print(f"  - [{err.get('code')}] 表【{err.get('worksheet')}】: {err.get('message')}")

        if warnings:
            print("\n⚠️ 优化告警详情 (Warnings):")
            for warn in warnings:
                print(f"  - [{warn.get('code')}] 表【{warn.get('worksheet')}】: {warn.get('message')}")

        print("=" * 50)

    # 4. 若通过，原子写入 worksheetContext.json
    if passed:
        target_context_path = app_dir / "worksheetContext.json"
        temp_context_path = app_dir / "worksheetContext.json.tmp"

        with open(temp_context_path, "w", encoding="utf-8") as f:
            json.dump(normalized_shards, f, ensure_ascii=False, indent=2)

        # 原子替换
        temp_context_path.replace(target_context_path)
        if verbose:
            print(f"✨ 成功原子生成全量结构上下文: {target_context_path}")
            print(f"📄 检验报告已保存至: {validation_path}\n")
        return True, ""

    err_lines = [
        f"[{err.get('code')}] 表【{err.get('worksheet')}】: {err.get('message')}"
        for err in errors[:10]
    ]
    err_summary = "; ".join(err_lines) if err_lines else f"校验未通过，详见 {validation_path}"
    if verbose:
        print(f"\n❌ 校验未通过，已生成体检报告至 {validation_path}，禁止推进状态！\n", file=sys.stderr)
    return False, err_summary


def main():
    parser = argparse.ArgumentParser(description="HAP 工作表结构分片合并与多维度强校验引擎")
    parser.add_argument("app_dir", help="应用所在目录（如 apps/个人读书与笔记）")
    parser.add_argument("--shards-dir", help="分片文件所在目录，默认为 <app_dir>/.build/artifacts")
    args = parser.parse_args()

    passed, _ = merge_and_validate_worksheet_context(args.app_dir, args.shards_dir, verbose=True)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
