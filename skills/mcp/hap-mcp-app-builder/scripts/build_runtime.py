#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_runtime.py
HAP App Copilot 报告驱动型薄控制面运行时引擎 (Report-Driven Build Runtime).

对齐 MDAgentService build-app-agent 最新全链路架构：
- 阶段 1 (step1): 创建应用、导航分组与自定义页面空壳 -> app_created
- 阶段 1.5 (app_created -> step2a_done -> worksheets_created):
  Step 1b(后台使用手册) + Step 2a(基础表与字段并发，产出 relationLayout 与 fieldOptionsContext)
  -> Step 2b(按 relationLayout 预留行号回填跨表关联与衍生字段)
- 阶段 2 (worksheets_created -> fields_refreshed):
  Step 3(单表结构采集 + 自定义动作 + 视图 + 四类业务规则) + Step 4a(AI助手实体创建)
  -> 自动触发 merge_worksheet_context.py 执行 10 项强校验合并
- 阶段 3 (fields_refreshed -> config_completed):
  Step 4b(AI助手关联工作流 ai_agent 节点配置发布) + Step 5(后台示例数据) + Step 6(页面组装与 summary 校正)
  + Step 7(应用项智能排序) + Step 8(单角色精细权限并发) + Step 9a/9b(单条系统流/动作流节点蓝图并发设计)
- 阶段 4 (config_completed -> completed):
  Step 10(单条系统流创建校验发布) + Step 11(单个动作流按 worksheet::action 精确匹配 processId 注入发布)
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

SYSTEM_WORKFLOW_TOOLS = [
    "find_member",
    "find_department",
    "get_current_user",
    "get_worksheet_field",
    "get_worksheet_structure",
    "create_process",
    "get_workflow_structure",
    "get_workflow_node",
    "get_workflow_variables",
    "update_workflow_node",
    "update_workflow_variables",
    "batch_create_process_nodes",
    "batch_delete_process_nodes",
    "validate_process",
    "publish_process",
    "get_sms_signatures",
]

ACTION_WORKFLOW_TOOLS = [t for t in SYSTEM_WORKFLOW_TOOLS if t != "create_process"] + [
    "get_custom_action_list",
    "update_custom_action",
]


def load_json(filepath: str) -> Any:
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return None


def load_text(filepath: str) -> str:
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def save_json(filepath: str, data: Any):
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(name)).strip("_")


def canonical_stage(stage: str) -> str:
    groups = {
        "step1": ("", "initial"),
        "app_created": ("step2a",),
        "step2a_done": ("step2b",),
        "worksheets_created": ("phase2_single_table",),
        "fields_refreshed": ("phase3_configs", "page_shells_created", "phase3"),
        "config_completed": ("phase4_deploy",),
    }
    return next((name for name, aliases in groups.items() if stage in aliases), stage)


def get_skill_root() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, ".."))


def require_run(app_dir: str) -> Dict[str, Any]:
    """所有运行命令复用同一环境和批次，不从缺失配置猜测环境。"""
    data = load_json(os.path.join(app_dir, ".build", "run.json"))
    if not isinstance(data, dict) or any(
        not isinstance(data.get(key), str) or not data[key].strip()
        for key in ("runId", "mcpServer")
    ):
        raise ValueError("缺少有效 runId 或 mcpServer；新工程须用已选环境 init，历史工程须核对并恢复原 run.json，禁止换批次重放。")
    return data


def unique_task_paths(app_dir: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """兼容既有无冲突编号；新冲突按原始身份区分，旧歧义产物不自动迁移。"""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    registry = load_json(os.path.join(app_dir, ".build", "dispatch-registry.json")) or {}

    def has_history(task_id: str) -> bool:
        return task_id in registry or any(os.path.exists(os.path.join(app_dir, ".build", folder, task_id + ".json"))
                                         for folder in ("receipts", "task-context"))

    for task in tasks:
        groups.setdefault(task["taskId"], []).append(task)
    for old_id, group in groups.items():
        if len(group) > 1 and has_history(old_id):
            raise ValueError(f"历史任务编号冲突：{old_id}；请先核对对应对象和既有回执，禁止覆盖或重新派发。")
        identities = set()
        for task in group:
            action = task.get("planSlice", {}).get("actionWorkflow", {})
            identity = json.dumps([task["step"], task["target"].get("type"),
                                   task["target"].get("name"), action.get("worksheet"), action.get("name")],
                                  ensure_ascii=False)
            if identity in identities:
                raise ValueError(f"重复任务目标：{old_id}；请消除方案中的重复对象。")
            identities.add(identity)
            new_id = old_id + "--" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
            if len(group) > 1 or has_history(new_id):
                task["taskId"] = new_id
                for key in ("receiptPath", "taskContextPath"):
                    task[key] = os.path.join(os.path.dirname(task[key]), new_id + ".json")
    for key in ("taskId", "receiptPath", "taskContextPath"):
        values = [t[key].casefold() for t in tasks]
        if len(values) != len(set(values)):
            raise ValueError(f"任务 {key} 存在文件名冲突；未写入任务文件，请先区分目标名称。")
    return tasks


def is_task_succeeded(receipt_path: str, expected_task_id: str, current_run_id: str = "", expected_agent_id: str = "") -> bool:
    if not os.path.exists(receipt_path):
        return False
    data = load_json(receipt_path)
    if not isinstance(data, dict):
        return False
    if data.get("taskId") != expected_task_id:
        return False
    if data.get("status") != "succeeded":
        return False

    receipt_run_id = data.get("runId")
    if not isinstance(current_run_id, str) or not current_run_id.strip() or receipt_run_id != current_run_id:
        return False

    executor = data.get("executor", {})
    if not isinstance(executor, dict) or executor.get("kind") not in {"subagent", "reconciled"}:
        return False

    agent_id = executor.get("agentId")
    if not isinstance(agent_id, str) or not agent_id.strip():
        return False

    verification = data.get("verification", {})
    if not isinstance(verification, dict) or verification.get("passed") is not True:
        return False
    evidence = verification.get("evidence", [])
    if not isinstance(evidence, list) or len(evidence) == 0:
        return False

    return True


def receipt_version(receipt_path: str) -> str:
    """识别派发续作前的旧回执；同内容的新失败回执也按新结果处理。"""
    with open(receipt_path, "rb") as file_obj:
        content = file_obj.read()
        modified = os.fstat(file_obj.fileno()).st_mtime_ns
    return hashlib.sha256(content + str(modified).encode()).hexdigest()


def _group_receipt_missing_worksheets(receipt: Dict[str, Any], expected_target: Optional[Dict[str, Any]]) -> Optional[str]:
    """校验 Step 2b 分组任务成功回执是否完整覆盖本组全部目标工作表。"""
    if not isinstance(expected_target, dict) or expected_target.get("type") != "worksheet_group":
        return None
    expected_ws = [w for w in (expected_target.get("worksheets") or []) if isinstance(w, str) and w]
    if not expected_ws:
        return None
    outputs = receipt.get("outputs") if isinstance(receipt.get("outputs"), dict) else {}
    completed_raw = outputs.get("completedWorksheets")
    done_names = set()
    if isinstance(completed_raw, list):
        for item in completed_raw:
            if isinstance(item, str) and item.strip():
                done_names.add(item.strip())
            elif isinstance(item, dict):
                wn = item.get("worksheetName") or item.get("name")
                if isinstance(wn, str) and wn.strip():
                    done_names.add(wn.strip())
    elif len(expected_ws) == 1:
        single_name = outputs.get("worksheetName") or outputs.get("name")
        if isinstance(single_name, str) and single_name.strip() == expected_ws[0]:
            done_names.add(expected_ws[0])
    if not done_names:
        return "分组关联回执缺少 outputs.completedWorksheets 明细；请核实本组各表回填结果。"
    missing = [w for w in expected_ws if w not in done_names]
    if missing:
        return f"分组关联回执未覆盖本组全部目标工作表（缺失：{'、'.join(missing)}）；请补齐剩余工作表。"
    return None


def task_state(
    receipt_path: str,
    task_id: str,
    run_id: str,
    dispatch: Dict[str, Any],
    expected_target: Optional[Dict[str, Any]] = None,
):
    """回执优先于旧派发状态；不校验外部登记 agentId 字符串相等，避免宿主异步会话 ID 天然不一致导致死锁。"""
    if not os.path.exists(receipt_path):
        return dispatch.get("status", "planned"), ""
    try:
        receipt = load_json(receipt_path)
        if (not isinstance(receipt, dict) or receipt.get("runId") != run_id
                or receipt.get("taskId") != task_id):
            return "blocked", "回执归属或格式无效；核对原运行与线上结果后恢复或执行 reset-task。"
        if receipt.get("status") == "succeeded":
            if is_task_succeeded(receipt_path, task_id, run_id):
                grp_err = _group_receipt_missing_worksheets(receipt, expected_target)
                if grp_err:
                    return "blocked", grp_err
                return "succeeded", ""
            return "blocked", "成功回执缺少有效执行者或验证证据；核实结果，不重复创建。"
        # 续作已派发，保留的旧失败回执不能把新执行器再次放入待派发列表。
        if (dispatch.get("status") == "running" and dispatch.get("resumeReceiptVersion")
                == receipt_version(receipt_path)):
            return "running", ""
        executor = receipt.get("executor") or {}
        if (not isinstance(executor, dict) or executor.get("kind") not in {"subagent", "reconciled"}
                or not isinstance(executor.get("agentId"), str) or not executor.get("agentId").strip()):
            return "blocked", "回执缺少有效 subagent 执行者标识；先核对实际执行结果。"
        status = receipt.get("status")
        if isinstance(status, str) and status in {"failed", "running"}:
            return status, str(receipt.get("issues") or "")
        return "blocked", f"任务回执状态为 {status}；核实未完成部分后续作。"
    except OSError as exc:
        return "blocked", f"暂无法读取回执：{exc}"


def extract_action_workflows(plan: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """提取需要设计并部署工作流的自定义动作（按 worksheet::action 复合键去重，保留跨表同名按钮）"""
    action_wfs: List[Dict[str, Any]] = []
    seen_keys = set()
    ws_id_by_name = context.get("worksheetIdByName", {})
    proc_id_by_key = context.get("actionProcessIdByKey", {})

    def add_action_item(ws_name: str, act: Dict[str, Any]):
        act_name = act.get("name") or act.get("actionName", "")
        if not act_name:
            return
        comp_key = f"{ws_name}::{act_name}"
        act_type = str(act.get("type") or act.get("clickType", "")).lower()
        is_wf = (
            act_type in ("triggerworkflow", "workflow", "2")
            or act.get("actionType") == 2
            or act.get("runWorkflowAfterSubmit") is True
            or bool(act.get("intentHints"))
            or bool(act.get("processId"))
            or bool(act.get("workflowId"))
            or bool(proc_id_by_key.get(comp_key))
        )
        if not is_wf:
            return
        if comp_key in seen_keys:
            return
        seen_keys.add(comp_key)
        action_wfs.append({
            "key": comp_key,
            "worksheet": ws_name,
            "worksheetName": ws_name,
            "worksheetId": ws_id_by_name.get(ws_name, ""),
            "name": act_name,
            "actionName": act_name,
            "type": act.get("type", "triggerWorkflow"),
            "runWorkflowAfterSubmit": bool(act.get("runWorkflowAfterSubmit", False)),
            "targetWorksheet": act.get("targetWorksheet", ""),
            "relateFieldName": act.get("relateFieldName", ""),
            "enableCondition": act.get("enableCondition", ""),
            "description": act.get("description", ""),
            "intentHints": act.get("intentHints", []),
            "requirements": act.get("requirements", []),
            **{k: act[k] for k in ("enabled", "status") if k in act},
            "processId": act.get("processId") or act.get("workflowId") or proc_id_by_key.get(comp_key, ""),
        })

    # 1. 从 worksheets 内嵌 customActions 提取
    for ws in plan.get("worksheets", []) or []:
        if not isinstance(ws, dict):
            continue
        ws_name = ws.get("name", "")
        for act in (ws.get("customActions") or ws.get("worksheetCustomActions") or []):
            if isinstance(act, dict):
                add_action_item(ws_name, act)

    # 2. 从顶层 customActions 数组提取 (MDAgentService 标准格式)
    for item in (plan.get("customActions") or plan.get("worksheetCustomActions") or []):
        if not isinstance(item, dict):
            continue
        ws_name = item.get("worksheet", "")
        ws_reqs = item.get("requirements", [])
        for act in item.get("actions", []) or []:
            if isinstance(act, dict):
                merged = dict(act)
                if ws_reqs and not merged.get("requirements"):
                    merged["requirements"] = ws_reqs
                add_action_item(ws_name, merged)

    # 3. 兼容旧版平铺 customActionWorkflows
    for wf in (plan.get("customActionWorkflows") or context.get("customActionWorkflows") or []):
        if isinstance(wf, dict):
            ws_name = wf.get("worksheet") or wf.get("worksheetName", "")
            add_action_item(ws_name, wf)

    return action_wfs


MAX_RELATION_GROUP_SIZE = 5


def _extract_referenced_worksheets(ws: Dict[str, Any], rel_layout: List[Dict[str, Any]], known_names: set) -> set:
    refs = set()
    parent_ws = ws.get("parentWorksheet")
    if isinstance(parent_ws, str) and parent_ws in known_names:
        refs.add(parent_ws)
    for item in rel_layout or []:
        if isinstance(item, dict):
            target_ws = item.get("targetWorksheet")
            if isinstance(target_ws, str) and target_ws in known_names:
                refs.add(target_ws)
    for f in (ws.get("fields") or ws.get("customFields") or []):
        if not isinstance(f, str) or "(" not in f:
            continue
        spec = f.split("(", 1)[1].rstrip(")")
        for prefix in ("Relation:", "SubTable:"):
            if spec.startswith(prefix):
                target_name = spec[len(prefix):].split(":", 1)[0].strip()
                if target_name in known_names:
                    refs.add(target_name)
    return refs


def _sort_relation_group_items(grp: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """组内主从拓扑排序：确保子表（subTable）及被 SubTable/Lookup/Rollup 依赖的目标表排在父表/源表之前，避免父表配置 showFields 时子表跨表列尚未创建。"""
    if len(grp) <= 1:
        return grp
    names_in_grp = {item["name"] for item in grp}
    # 依赖关系：若 parent 依赖 child 先完成（如 child 是 subTable，或 parent 有 SubTable/Lookup/Rollup 指向 child），则 child -> parent
    deps_on: Dict[str, set] = {item["name"]: set() for item in grp}
    for item in grp:
        name = item["name"]
        ws = item.get("ws") or {}
        if ws.get("worksheetType") == "subTable":
            parent_ws = ws.get("parentWorksheet")
            if isinstance(parent_ws, str) and parent_ws in names_in_grp and parent_ws != name:
                deps_on[parent_ws].add(name)
        for rel in item.get("rel_layout") or []:
            if not isinstance(rel, dict):
                continue
            ftype = str(rel.get("type") or rel.get("fieldType") or "")
            target_ws = rel.get("targetWorksheet")
            if ftype in ("SubTable", "Lookup", "Rollup") and isinstance(target_ws, str) and target_ws in names_in_grp and target_ws != name:
                deps_on[name].add(target_ws)
        for f in (ws.get("fields") or ws.get("customFields") or []):
            if isinstance(f, str) and "(SubTable:" in f:
                sub_name = f.split("(SubTable:", 1)[1].rstrip(")").split(":", 1)[0].strip()
                if sub_name in names_in_grp and sub_name != name:
                    deps_on[name].add(sub_name)

    item_by_name = {item["name"]: item for item in grp}
    orig_order = [item["name"] for item in grp]
    placed: List[str] = []
    placed_set: set = set()
    # 优先级：1. subTable 优先；2. 无未就绪依赖的表按原顺序输出
    remaining = sorted(orig_order, key=lambda n: (0 if (item_by_name[n].get("ws") or {}).get("worksheetType") == "subTable" else 1, orig_order.index(n)))
    while remaining:
        progressed = False
        for n in list(remaining):
            if deps_on[n].issubset(placed_set):
                placed.append(n)
                placed_set.add(n)
                remaining.remove(n)
                progressed = True
                break
        if not progressed:
            # 存在循环引用时按剩余顺序兜底
            n = remaining.pop(0)
            placed.append(n)
            placed_set.add(n)
    return [item_by_name[n] for n in placed]


def group_relation_worksheets(
    rel_items: List[Dict[str, Any]],
    all_ws_names: List[str],
    max_group_size: int = MAX_RELATION_GROUP_SIZE,
) -> List[List[Dict[str, Any]]]:
    """按跨表关联连通性（含共同指向同一目标主表）聚拢并按上限保序分箱，消除反向关联并发锁竞争且减少 Subagent 冷启动。"""
    if not rel_items:
        return []
    if len(rel_items) <= max_group_size:
        return [_sort_relation_group_items(rel_items)]

    known = set(all_ws_names)
    n = len(rel_items)
    idx_by_name = {item["name"]: i for i, item in enumerate(rel_items)}
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    holders_by_target: Dict[str, List[int]] = {}
    for i, item in enumerate(rel_items):
        for target_name in _extract_referenced_worksheets(item["ws"], item["rel_layout"], known):
            if target_name in idx_by_name and idx_by_name[target_name] != i:
                union(i, idx_by_name[target_name])
            holders_by_target.setdefault(target_name, []).append(i)

    for holders in holders_by_target.values():
        first = holders[0]
        for other in holders[1:]:
            union(first, other)

    comp_map: Dict[int, List[Dict[str, Any]]] = {}
    comp_order: List[int] = []
    for i, item in enumerate(rel_items):
        root = find(i)
        if root not in comp_map:
            comp_map[root] = []
            comp_order.append(root)
        comp_map[root].append(item)

    atomic_chunks: List[List[Dict[str, Any]]] = []
    for root in comp_order:
        comp = comp_map[root]
        for start in range(0, len(comp), max_group_size):
            atomic_chunks.append(comp[start : start + max_group_size])

    groups: List[List[Dict[str, Any]]] = []
    for chunk in atomic_chunks:
        placed = False
        for grp in groups:
            if len(grp) + len(chunk) <= max_group_size:
                grp.extend(chunk)
                placed = True
                break
        if not placed:
            groups.append(list(chunk))
    return [_sort_relation_group_items(g) for g in groups]


def current_rule_notes(app_dir, context, run_id):
    notes = dict(context.get("businessRulesNotesByWorksheet") or {})
    folder = os.path.join(app_dir, ".build", "receipts")
    for filename in os.listdir(folder) if os.path.isdir(folder) else []:
        if not filename.startswith("step2a-") or not filename.endswith(".json"):
            continue
        receipt = load_json(os.path.join(folder, filename)) or {}
        if (receipt.get("runId") != run_id or receipt.get("taskId") != filename[:-5]
                or receipt.get("status") != "succeeded"
                or (receipt.get("verification") or {}).get("passed") is not True):
            continue
        outputs = receipt.get("outputs") or {}
        name = outputs.get("worksheetName")
        if name and outputs.get("worksheetId") and outputs["worksheetId"] == context.get("worksheetIdByName", {}).get(name):
            notes[name] = outputs.get("businessRulesNotes") or []
    return notes


def get_stage_tasks_definitions(app_dir: str, stage: str) -> List[Dict[str, Any]]:
    plan = load_json(os.path.join(app_dir, "hap-plan.json")) or {}
    context = load_json(os.path.join(app_dir, "hap-context.json")) or {}
    ws_context = load_json(os.path.join(app_dir, "worksheetContext.json")) or {}
    overview_md = load_text(os.path.join(app_dir, "overview.md"))

    app_name = plan.get("appName") or plan.get("name") or context.get("appName") or os.path.basename(app_dir)
    app_id = context.get("appId", "")
    org_id = plan.get("org_id") or plan.get("orgId") or context.get("org_id") or context.get("orgId", "")
    app_lang = plan.get("language") or context.get("language") or "zh-CN"
    app_color = plan.get("appColor", "")
    app_reqs = plan.get("requirements", [])
    nav_groups = plan.get("navGroups") or plan.get("sections") or []
    worksheets = plan.get("worksheets", [])
    custom_pages = plan.get("customPages", [])
    roles = plan.get("roles", [])
    ai_assistants = plan.get("aiAssistants") or plan.get("chatbots") or []
    workflows = plan.get("workflows", [])
    action_workflows = extract_action_workflows(plan, context)

    ws_id_by_name = context.get("worksheetIdByName", {})
    sec_id_by_name = context.get("sectionIdByName", {})
    rel_layout_by_ws = context.get("relationLayoutByWorksheet", {})
    ws_fields_preview = context.get("worksheetFieldsPreview", {})
    field_options_ctx = context.get("fieldOptionsContext", [])
    chatbot_id_by_name = context.get("chatbotIdByName", {})

    tasks: List[Dict[str, Any]] = []

    # 阶段 1: 应用外壳、分组与页面空壳
    if stage in ("step1", "initial"):
        tasks.append({
            "taskId": "step1-app-init",
            "taskName": f"[Step 1] 创建应用外壳 - {app_name}",
            "step": "1",
            "target": {"type": "app", "name": app_name},
            "stepFile": "build/steps/1_create_app.md",
            "references": ["references/hap-domain-app-spec.md", "references/hap-icon-palette.md"],
            "allowedTools": ["create_app", "create_app_sections", "create_app_items"],
            "receiptPath": ".build/receipts/step1-app-init.json",
            "taskContextPath": ".build/task-context/step1-app-init.json",
            "planSlice": {
                "appName": app_name,
                "appIcon": plan.get("appIcon"),
                "appColor": app_color,
                "navLayout": plan.get("navLayout"),
                "navColor": plan.get("navColor"),
                "enableExternalPortal": bool(plan.get("enableExternalPortal", False)),
                "requirements": app_reqs,
                "appLanguage": app_lang,
                "org_id": org_id,
                "navGroups": nav_groups,
                "customPages": custom_pages,
            },
            "contextSlice": {"org_id": org_id},
            "worksheetContextSlice": {},
            "desc": f"创建应用 [{app_name}]、导航分组与自定义页面空壳",
        })

    # 阶段 1.5 Pass 1: Step 2a 并发建表（Step 1b 应用说明已收归主调度器在阶段 1 内联完成）
    elif stage in ("app_created", "step2a"):
        for ws in worksheets:
            if not isinstance(ws, dict):
                continue
            name = ws.get("name", "")
            sec_name = ws.get("groupName") or ws.get("section") or ws.get("navGroup") or ""
            related_roles = [{"name": role.get("name"), "description": role.get("description")}
                             for role in roles if isinstance(role, dict)
                             and f"{name}(worksheet)" in (role.get("permissions") or [])]
            related_flows = [flow for flow in workflows if isinstance(flow, dict)
                             and isinstance(flow.get("trigger"), dict)
                             and flow["trigger"].get("source") == name]
            action_groups = plan.get("customActions") or plan.get("worksheetCustomActions") or []
            related_actions = [action for group in action_groups if isinstance(group, dict)
                               and group.get("worksheet") == name for action in group.get("actions") or []]
            tasks.append({
                "taskId": f"step2a-ws-{normalize_name(name)}",
                "taskName": f"[Step 2a] 创表 - {name}",
                "step": "2a",
                "target": {"type": "worksheet", "name": name},
                "stepFile": "build/steps/2a_create_worksheets.md",
                "references": ["references/hap-domain-worksheet-spec.md", "references/hap-domain-custom-field-spec.md"],
                "allowedTools": ["create_worksheet", "update_worksheet", "update_worksheet_settings"],
                "receiptPath": f".build/receipts/step2a-ws-{normalize_name(name)}.json",
                "taskContextPath": f".build/task-context/step2a-ws-{normalize_name(name)}.json",
                "planSlice": {
                    "worksheet": ws,
                    "worksheetUsage": {"roles": related_roles, "actions": related_actions, "workflows": related_flows},
                    "fields": ws.get("fields") or ws.get("customFields") or [],
                    "appLanguage": app_lang,
                },
                "contextSlice": {
                    "appId": app_id,
                    "appSectionId": sec_id_by_name.get(sec_name, ""),
                    "sectionIdByName": sec_id_by_name,
                },
                "worksheetContextSlice": {},
                "desc": f"创建工作表与基础字段排版: {name}",
            })

    # 阶段 1.5 Pass 2: Step 2b 关联与衍生字段按组回填（连通聚类 + 保序分箱，兼容历史单表回执）
    elif stage in ("step2a_done", "step2b"):
        all_ws_order = [ws.get("name", "") for ws in worksheets if isinstance(ws, dict) and ws.get("name")]
        pending_rel_items: List[Dict[str, Any]] = []
        for ws in worksheets:
            if not isinstance(ws, dict):
                continue
            name = ws.get("name", "")
            rel_layout = rel_layout_by_ws.get(name)
            fields = ws.get("fields") or ws.get("customFields") or []
            has_relations = bool(rel_layout) or any(
                isinstance(f, str) and any(kw in f for kw in ("Relation:", "SubTable:", "Rollup:", "Lookup:"))
                for f in fields
            )
            if not has_relations:
                continue
            legacy_rel_receipt = f".build/receipts/step2b-rel-{normalize_name(name)}.json"
            if os.path.exists(os.path.join(app_dir, legacy_rel_receipt)):
                tasks.append({
                    "taskId": f"step2b-rel-{normalize_name(name)}",
                    "taskName": f"[Step 2b] 关联回填 - {name}",
                    "step": "2b",
                    "target": {"type": "worksheet", "id": ws_id_by_name.get(name, ""), "name": name},
                    "stepFile": "build/steps/2b_create_relations.md",
                    "references": ["references/hap-domain-worksheet-spec.md"],
                    "allowedTools": ["update_worksheet"],
                    "receiptPath": legacy_rel_receipt,
                    "taskContextPath": f".build/task-context/step2b-rel-{normalize_name(name)}.json",
                    "planSlice": {
                        "worksheetName": name,
                        "fields": fields,
                        "relationLayout": rel_layout or [],
                        "allWorksheetOrder": all_ws_order,
                        "allRelationLayouts": rel_layout_by_ws,
                        "requirements": ws.get("requirements", []),
                        "appLanguage": app_lang,
                    },
                    "contextSlice": {
                        "appId": app_id,
                        "worksheetId": ws_id_by_name.get(name, ""),
                        "worksheetIdByName": ws_id_by_name,
                        "worksheetFieldsByName": ws_fields_preview,
                        "fieldOptionsContext": field_options_ctx,
                    },
                    "worksheetContextSlice": {},
                    "desc": f"按预留行号补充跨表关联与衍生字段: {name}",
                })
            else:
                pending_rel_items.append({
                    "name": name,
                    "ws": ws,
                    "fields": fields,
                    "rel_layout": rel_layout or [],
                })

        rel_groups = group_relation_worksheets(pending_rel_items, all_ws_order)
        for idx, grp in enumerate(rel_groups, start=1):
            group_names = [item["name"] for item in grp]
            joined_names = "、".join(group_names)
            plan_slice: Dict[str, Any] = {
                "groupIndex": idx,
                "items": [
                    {
                        "worksheetName": item["name"],
                        "worksheetId": ws_id_by_name.get(item["name"], ""),
                        "worksheet": item["ws"],
                        "fields": item["fields"],
                        "relationLayout": item["rel_layout"],
                        "requirements": item["ws"].get("requirements", []),
                    }
                    for item in grp
                ],
                "allWorksheetOrder": all_ws_order,
                "allRelationLayouts": rel_layout_by_ws,
                "appLanguage": app_lang,
            }
            ctx_slice: Dict[str, Any] = {
                "appId": app_id,
                "worksheetIds": {item["name"]: ws_id_by_name.get(item["name"], "") for item in grp},
                "worksheetIdByName": ws_id_by_name,
                "worksheetFieldsByName": ws_fields_preview,
                "fieldOptionsContext": field_options_ctx,
            }
            if len(grp) == 1:
                only = grp[0]
                plan_slice.update({
                    "worksheet": only["ws"],
                    "worksheetName": only["name"],
                    "fields": only["fields"],
                    "relationLayout": only["rel_layout"],
                    "requirements": only["ws"].get("requirements", []),
                })
                ctx_slice["worksheetId"] = ws_id_by_name.get(only["name"], "")

            tasks.append({
                "taskId": f"step2b-rel-group-{idx}",
                "taskName": f"[Step 2b] 关联回填第 {idx} 组 ({joined_names})",
                "step": "2b",
                "target": {
                    "type": "worksheet_group",
                    "name": f"group-{idx}",
                    "worksheets": group_names,
                    "worksheetIds": {n: ws_id_by_name.get(n, "") for n in group_names},
                },
                "stepFile": "build/steps/2b_create_relations.md",
                "references": ["references/hap-domain-worksheet-spec.md"],
                "allowedTools": ["update_worksheet"],
                "receiptPath": f".build/receipts/step2b-rel-group-{idx}.json",
                "taskContextPath": f".build/task-context/step2b-rel-group-{idx}.json",
                "planSlice": plan_slice,
                "contextSlice": ctx_slice,
                "worksheetContextSlice": {},
                "desc": f"按预留行号逐表顺序补充跨表关联与衍生字段（第 {idx} 组：{joined_names}）",
            })

    # 阶段 2: Step 3 单表全要素 + Step 4a AI 助手实体创建
    elif stage in ("worksheets_created", "phase2_single_table"):
        run = load_json(os.path.join(app_dir, ".build", "run.json")) or {}
        rule_notes = current_rule_notes(app_dir, context, run.get("runId"))
        top_ca = plan.get("customActions") or plan.get("worksheetCustomActions") or []
        ca_by_ws: Dict[str, List[Dict[str, Any]]] = {}
        if isinstance(top_ca, list):
            for item in top_ca:
                if isinstance(item, dict) and "worksheet" in item:
                    ca_by_ws[item["worksheet"]] = item.get("actions", [])

        for ws in worksheets:
            if not isinstance(ws, dict):
                continue
            name = ws.get("name", "")
            ws_id = ws_id_by_name.get(name, "")
            rules = ws.get("businessRules") or ws.get("businessRulesNotes") or []
            views = ws.get("views", [])
            custom_actions = ws.get("customActions") or ws.get("worksheetCustomActions") or ca_by_ws.get(name, [])
            # 子表字段可能在父表挂载之后才由另一关联组回填；交给父表任务在阶段门禁后核对。
            # 只提供定位线索，实际列必须来自在线结构，不能把尚未创建的 alias 当作事实。
            subtable_checks = []
            for item in rel_layout_by_ws.get(name, []) or []:
                if isinstance(item, dict) and item.get("fieldType") == "SubTable" and item.get("targetWorksheet"):
                    child = item["targetWorksheet"]
                    subtable_checks.append({"name": item.get("name", ""), "alias": item.get("alias", ""),
                                            "worksheetName": child, "worksheetId": ws_id_by_name.get(child, "")})
            # 旧工程没有 relationLayout 时从原计划补充定位信息，不改变原任务归属。
            if not subtable_checks:
                for field in ws.get("fields") or ws.get("customFields") or []:
                    if isinstance(field, str) and "(SubTable:" in field:
                        label, spec = field.split("(SubTable:", 1)
                        child = spec.rstrip(")").strip()
                        if child:
                            subtable_checks.append({"name": label.strip(), "alias": "", "worksheetName": child,
                                                    "worksheetId": ws_id_by_name.get(child, "")})
            tasks.append({
                "taskId": f"step3-view-act-{normalize_name(name)}",
                "taskName": f"[Step 3] 单表全要素配置 - {name}",
                "step": "3",
                "target": {"type": "worksheet", "id": ws_id, "name": name},
                "stepFile": "build/steps/3_create_actions_views_rules.md",
                "references": [
                    "references/hap-domain-view-spec.md",
                    "references/hap-domain-custom-action-spec.md",
                    "references/hap-domain-business-rule-spec.md",
                ],
                "allowedTools": [
                    "get_worksheet_structure",
                    *(["update_worksheet"] if subtable_checks else []),
                    "get_custom_action_list",
                    "create_custom_actions",
                    "create_view",
                    "get_view_structure",
                    "update_view",
                    "get_business_rule_list",
                    "create_business_rule",
                ],
                "receiptPath": f".build/receipts/step3-view-act-{normalize_name(name)}.json",
                "taskContextPath": f".build/task-context/step3-view-act-{normalize_name(name)}.json",
                "planSlice": {
                    "worksheetName": name,
                    "businessRules": rules,
                    "views": views,
                    "customActions": custom_actions,
                    "requirements": ws.get("requirements", []),
                    "appLanguage": app_lang,
                },
                "contextSlice": {
                    "appId": app_id,
                    "worksheetId": ws_id,
                    "worksheetIdByName": ws_id_by_name,
                    "artifactPath": os.path.join(app_dir, ".build", "artifacts", f"worksheet-{ws_id}.json"),
                    "subtableDisplayChecks": subtable_checks,
                    "businessRulesNotes": rule_notes.get(name, []),
                },
                "worksheetContextSlice": {},
                "desc": f"拉取完整结构并配置自定义动作、视图与业务规则: {name}",
            })

        if ai_assistants:
            tasks.append({
                "taskId": "step4-chatbot",
                "taskName": "[Step 4a] 创建 AI 智能助手实体",
                "step": "4a",
                "target": {"type": "chatbot", "name": "AI智能助手"},
                "stepFile": "build/steps/4_create_chatbots.md",
                "references": ["references/hap-domain-chatbot-spec.md"],
                "allowedTools": ["create_chatbot"],
                "receiptPath": ".build/receipts/step4-chatbot.json",
                "taskContextPath": ".build/task-context/step4-chatbot.json",
                "planSlice": {
                    "aiAssistants": ai_assistants,
                    "worksheetsSummary": [{"name": w.get("name"), "description": w.get("description", "")} for w in worksheets if isinstance(w, dict)],
                    "appLanguage": app_lang,
                },
                "contextSlice": {
                    "appId": app_id,
                    "sectionIdByName": sec_id_by_name,
                    "worksheetIdByName": ws_id_by_name,
                },
                "worksheetContextSlice": {},
                "desc": "创建应用专属 AI 智能助手实体并获取 chatbotId",
            })

    # 阶段 3: Step 4b + Step 5 + Step 6 + Step 7 + Step 8 + Step 9a/9b
    elif stage in ("fields_refreshed", "phase3_configs", "page_shells_created", "phase3"):
        page_id_by_name = context.get("customPageIdByName", {})
        view_id_by_name = context.get("viewIdByName", {})
        views_by_ws = context.get("viewsByWorksheet", {})

        # Step 4b: 为每个已建 AI 助手配置关联工作流 ai_agent 节点
        for bot in ai_assistants:
            if not isinstance(bot, dict):
                continue
            b_name = bot.get("name", "")
            b_id = chatbot_id_by_name.get(b_name, "")
            if b_name and b_id:
                tasks.append({
                    "taskId": f"step4b-chatbot-config-{normalize_name(b_name)}",
                    "taskName": f"[Step 4b] 配置 AI 助手节点 - {b_name}",
                    "step": "4b",
                    "target": {"type": "chatbot", "id": b_id, "name": b_name},
                    "stepFile": "build/steps/4_create_chatbots.md",
                    "references": ["references/hap-domain-chatbot-spec.md"],
                    "allowedTools": [
                        "get_workflow_structure",
                        "get_workflow_node",
                        "update_workflow_node",
                        "publish_process",
                        "get_app_ai_models",
                        "get_app_knowledge_list",
                        "get_worksheet_structure",
                        "get_view_structure",
                    ],
                    "receiptPath": f".build/receipts/step4b-chatbot-config-{normalize_name(b_name)}.json",
                    "taskContextPath": f".build/task-context/step4b-chatbot-config-{normalize_name(b_name)}.json",
                    "planSlice": {"assistant": bot, "appLanguage": app_lang},
                    "contextSlice": {
                        "appId": app_id,
                        "chatbotId": b_id,
                        "worksheetIdByName": ws_id_by_name,
                        "viewIdByName": view_id_by_name,
                    },
                    "worksheetContextSlice": ws_context,
                    "desc": f"为 AI 助手 [{b_name}] 配置关联工作流节点并发布",
                })

        # Step 5: 示例数据（后台任务，裁剪只读/分段字段与冗余选项元数据，同时保留关联目标表 dataSource 供外键/主从映射）
        readonly_types = {
            "Divider",
            "AutoNumber",
            "Concatenate",
            "Formula",
            "DateFormula",
            "FormulaFunc",
            "FunctionFormula",
            "Rollup",
            "Lookup",
            "SubTable",
        }
        slim_ws_ctx = []
        ws_list_raw = ws_context.get("worksheets", []) if isinstance(ws_context, dict) else (ws_context if isinstance(ws_context, list) else [])
        for w_item in ws_list_raw:
            if not isinstance(w_item, dict):
                continue
            slim_fields = []
            for fld in w_item.get("fields", []) or []:
                if not isinstance(fld, dict) or fld.get("type") in readonly_types:
                    continue
                sf: Dict[str, Any] = {"id": fld.get("id"), "name": fld.get("name"), "type": fld.get("type")}
                if fld.get("alias"):
                    sf["alias"] = fld["alias"]
                if fld.get("dataSource"):
                    sf["dataSource"] = fld["dataSource"]
                if fld.get("options") and isinstance(fld["options"], list):
                    sf["options"] = [o.get("value") for o in fld["options"] if isinstance(o, dict) and o.get("value") and not o.get("isDelete")]
                slim_fields.append(sf)
            slim_ws_ctx.append({
                "worksheetId": w_item.get("worksheetId"),
                "worksheetName": w_item.get("worksheetName"),
                "fields": slim_fields,
            })

        step5_task_def = {
            "taskId": "step5-sample-data",
            "taskName": "[Step 5] 填充示例数据",
            "step": "5",
            "target": {"type": "sample_data", "name": "全局示例数据"},
            "stepFile": "build/steps/5_create_sample_data.md",
            "references": ["references/hap-sample-data-spec.md"],
            "allowedTools": ["batch_create_records", "get_worksheet_structure", "get_record_details"],
            "receiptPath": ".build/receipts/step5-sample-data.json",
            "taskContextPath": ".build/task-context/step5-sample-data.json",
            "isBackground": True,
            "planSlice": {
                "worksheets": [
                    {
                        "name": w.get("name"),
                        "worksheetType": w.get("worksheetType", "normal"),
                        "parentWorksheet": w.get("parentWorksheet", ""),
                        "requirements": w.get("requirements", []),
                    }
                    for w in worksheets
                    if isinstance(w, dict)
                ],
                "appLanguage": app_lang,
            },
            "contextSlice": {
                "appId": app_id,
                "worksheetIdByName": ws_id_by_name,
            },
            "worksheetContextSlice": {"worksheets": slim_ws_ctx},
            "desc": "按示例规范填报业务记录，匹配并回读适用的示例成员与附件",
        }
        tasks.append(step5_task_def)

        # Step 6: 自定义页面组装与 summary 布局校正
        for page in custom_pages:
            if not isinstance(page, dict):
                continue
            name = page.get("name", "")
            tasks.append({
                "taskId": f"step6-page-{normalize_name(name)}",
                "taskName": f"[Step 6] 页面组件组装 - {name}",
                "step": "6",
                "target": {"type": "page", "id": page_id_by_name.get(name, ""), "name": name},
                "stepFile": "build/steps/6_create_pages.md",
                "references": [
                    "references/hap-domain-custom-page-spec.md",
                    "references/hap-chart-design-guide.md",
                    "references/hap-icon-palette.md",
                ],
                "allowedTools": ["update_custom_page", "get_custom_page_structure", "patch_custom_page_components"],
                "receiptPath": f".build/receipts/step6-page-{normalize_name(name)}.json",
                "taskContextPath": f".build/task-context/step6-page-{normalize_name(name)}.json",
                "planSlice": {"page": page, "appColor": app_color, "appLanguage": app_lang},
                "contextSlice": {
                    "appId": app_id,
                    "pageId": page_id_by_name.get(name, ""),
                    "worksheetIdByName": ws_id_by_name,
                    "viewIdByName": view_id_by_name,
                    "viewsByWorksheet": views_by_ws,
                },
                "worksheetContextSlice": ws_context,
                "desc": f"配置自定义页面组件并通过 summary 校验布局: {name}",
            })

        # Step 8: 角色精细权限并发构建（注：Step 7 应用项排序收归主调度器内联执行；工作流设计与创建在阶段 4 一体化执行）
        for role in roles:
            if not isinstance(role, dict):
                continue
            name = role.get("name", "")
            authorized_names = {
                permission[:-len("(worksheet)")]
                for permission in (role.get("permissions") or [])
                if isinstance(permission, str) and permission.endswith("(worksheet)")
            }
            raw_worksheets = ws_context.get("worksheets", []) if isinstance(ws_context, dict) else (ws_context if isinstance(ws_context, list) else [])
            role_worksheets = [w for w in raw_worksheets if isinstance(w, dict) and w.get("worksheetName") in authorized_names]
            # 阶段 2 的真实动作映射以“表名/动作名”为键。按最长真实表名前缀匹配，避免表名包含斜杠时误归属。
            raw_actions = context.get("actionIdByName", {})
            raw_actions = raw_actions if isinstance(raw_actions, dict) else {}
            known_names = sorted((n for n in ws_id_by_name if isinstance(n, str) and n), key=len, reverse=True)
            role_actions = {}
            for key, action_id in raw_actions.items():
                if not isinstance(key, str) or not isinstance(action_id, str) or not action_id:
                    continue
                owner = next((n for n in known_names if key.startswith(n + "/") and key[len(n) + 1:]), None)
                if owner in authorized_names:
                    role_actions[key] = action_id
            tasks.append({
                "taskId": f"step8-role-{normalize_name(name)}",
                "taskName": f"[Step 8] 角色权限 - {name}",
                "step": "8",
                "target": {"type": "role", "name": name},
                "stepFile": "build/steps/8_create_roles.md",
                "references": ["references/hap-domain-role-spec.md", "references/hap-app-design-guide.md"],
                "allowedTools": ["create_role", "get_role_list", "get_role_details", "get_role_worksheet_permission", "update_role"],
                "receiptPath": f".build/receipts/step8-role-{normalize_name(name)}.json",
                "taskContextPath": f".build/task-context/step8-role-{normalize_name(name)}.json",
                "planSlice": {"role": role, "appLanguage": app_lang},
                "contextSlice": {
                    "appId": app_id,
                    "worksheetIdByName": ws_id_by_name,
                    "viewIdByName": view_id_by_name,
                    "viewsByWorksheet": views_by_ws,
                    "actionIdByName": role_actions,
                    "customPageIdByName": page_id_by_name,
                    "chatbotIdByName": chatbot_id_by_name,
                },
                "worksheetContextSlice": {"worksheets": role_worksheets},
                "desc": f"创建角色并推演精细权限矩阵: {name}",
            })

    # 阶段 4: Step 10 系统流与 Step 11 动作流「设计+创建+校验发布」一体化并发执行
    elif stage in ("config_completed", "phase4_deploy"):
        # 历史回执可能只生成 roleIdByName；保留原有 roleContext 的完整字段与顺序，
        # 仅为缺少的名称补充真实 ID，不覆盖已有上下文，也不推测角色成员。
        raw_role_ctx = context.get("roleContext", [])
        role_ctx = [dict(r) if isinstance(r, dict) else r for r in raw_role_ctx] if isinstance(raw_role_ctx, list) else []
        role_ids = context.get("roleIdByName", {})
        role_ids = role_ids if isinstance(role_ids, dict) else {}
        for entry in role_ctx:
            if isinstance(entry, dict) and entry.get("name") in role_ids and not entry.get("id"):
                entry["id"] = role_ids[entry["name"]]
        names_with_id = {r.get("name") for r in role_ctx if isinstance(r, dict) and r.get("name") and r.get("id")}
        for role_name, role_id in role_ids.items():
            if role_name and role_id and role_name not in names_with_id:
                role_ctx.append({"name": role_name, "id": role_id})
        view_id_by_name = context.get("viewIdByName", {})
        proc_id_by_key = context.get("actionProcessIdByKey", {})
        wf_index = [{"name": w.get("name"), "description": w.get("description", ""), "trigger": w.get("trigger", {})} for w in workflows if isinstance(w, dict)]
        act_index = [{"worksheet": a.get("worksheet"), "name": a.get("name"), "description": a.get("description", "")} for a in action_workflows]

        for wf in workflows:
            if not isinstance(wf, dict):
                continue
            name = wf.get("name", "")
            tasks.append({
                "taskId": f"step10-sys-wf-{normalize_name(name)}",
                "taskName": f"[Step 10] 设计并部署系统流 - {name}",
                "step": "10",
                "target": {"type": "workflow", "name": name},
                "stepFile": "build/steps/10_create_workflows.md",
                "references": ["references/hap-workflow-design-guide.md", "references/hap-domain-workflow-spec.md"],
                "allowedTools": SYSTEM_WORKFLOW_TOOLS,
                "receiptPath": f".build/receipts/step10-sys-wf-{normalize_name(name)}.json",
                "taskContextPath": f".build/task-context/step10-sys-wf-{normalize_name(name)}.json",
                "planSlice": {
                    "workflow": wf,
                    "workflowIndex": wf_index,
                    "customActionIndex": act_index,
                    "relationLayouts": rel_layout_by_ws,
                    "appLanguage": app_lang,
                },
                "contextSlice": {
                    "appId": app_id,
                    "org_id": org_id,
                    "worksheetIdByName": ws_id_by_name,
                    "roleContext": role_ctx,
                    "roleIdByName": role_ids,
                    "viewIdByName": view_id_by_name,
                },
                "worksheetContextSlice": ws_context,
                "desc": f"一体化设计、创建、校验并发布系统工作流: {name}",
            })

        for act in action_workflows:
            ws_n = act.get("worksheet", "")
            act_n = act.get("name", "未命名动作流")
            comp_key = f"{ws_n}::{act_n}"
            safe_key = f"{normalize_name(ws_n)}_{normalize_name(act_n)}"
            proc_id = act.get("processId") or proc_id_by_key.get(comp_key, "")
            tasks.append({
                "taskId": f"step11-act-wf-{safe_key}",
                "taskName": f"[Step 11] 设计并部署动作流 - {ws_n}/{act_n}",
                "step": "11",
                "target": {"type": "workflow", "id": proc_id, "name": f"{ws_n}/{act_n}"},
                "stepFile": "build/steps/11_create_action_workflows.md",
                "references": ["references/hap-workflow-design-guide.md", "references/hap-domain-workflow-spec.md"],
                "allowedTools": ACTION_WORKFLOW_TOOLS,
                "receiptPath": f".build/receipts/step11-act-wf-{safe_key}.json",
                "taskContextPath": f".build/task-context/step11-act-wf-{safe_key}.json",
                "planSlice": {
                    "actionWorkflow": act,
                    "workflowIndex": wf_index,
                    "customActionIndex": act_index,
                    "relationLayouts": rel_layout_by_ws,
                    "appLanguage": app_lang,
                },
                "contextSlice": {
                    "appId": app_id,
                    "org_id": org_id,
                    "processId": proc_id,
                    "actionId": context.get("actionIdByName", {}).get(f"{ws_n}/{act_n}", ""),
                    "actionProvenance": context.get("actionProvenanceByKey", {}).get(comp_key, {}),
                    "worksheetIdByName": ws_id_by_name,
                    "roleContext": role_ctx,
                    "roleIdByName": role_ids,
                    "viewIdByName": view_id_by_name,
                },
                "worksheetContextSlice": ws_context,
                "desc": f"一体化设计节点、注入预建动作流、校验并发布: {ws_n}/{act_n}",
            })

        # 若阶段 3 后台任务 Step 5 尚未成功完成（如中途报错中断需 reset-task 重派），在阶段 4 继续挂载追踪
        step5_receipt = os.path.join(app_dir, ".build", "receipts", "step5-sample-data.json")
        run_id_cur = (load_json(os.path.join(app_dir, ".build", "run.json")) or {}).get("runId", "")
        if not is_task_succeeded(step5_receipt, "step5-sample-data", run_id_cur):
            readonly_types = {"Divider", "AutoNumber", "Concatenate", "Formula", "Rollup", "Lookup", "SubTable"}
            slim_ws_ctx = []
            ws_list_raw = ws_context.get("worksheets", []) if isinstance(ws_context, dict) else (ws_context if isinstance(ws_context, list) else [])
            for w_item in ws_list_raw:
                if not isinstance(w_item, dict):
                    continue
                slim_fields = []
                for fld in w_item.get("fields", []) or []:
                    if not isinstance(fld, dict) or fld.get("type") in readonly_types:
                        continue
                    sf = {"id": fld.get("id"), "name": fld.get("name"), "type": fld.get("type")}
                    if fld.get("options") and isinstance(fld["options"], list):
                        sf["options"] = [o.get("value") for o in fld["options"] if isinstance(o, dict) and o.get("value") and not o.get("isDelete")]
                    slim_fields.append(sf)
                slim_ws_ctx.append({
                    "worksheetId": w_item.get("worksheetId"),
                    "worksheetName": w_item.get("worksheetName"),
                    "fields": slim_fields,
                })
            tasks.append({
                "taskId": "step5-sample-data",
                "taskName": "[Step 5] 填充示例数据",
                "step": "5",
                "target": {"type": "sample_data", "name": "全局示例数据"},
                "stepFile": "build/steps/5_create_sample_data.md",
                "references": ["references/hap-sample-data-spec.md"],
                "allowedTools": ["batch_create_records", "get_worksheet_structure", "get_record_details"],
                "receiptPath": ".build/receipts/step5-sample-data.json",
                "taskContextPath": ".build/task-context/step5-sample-data.json",
                "isBackground": True,
                "planSlice": {
                    "worksheets": [
                        {
                            "name": w.get("name"),
                            "worksheetType": w.get("worksheetType", "normal"),
                            "parentWorksheet": w.get("parentWorksheet", ""),
                            "requirements": w.get("requirements", []),
                        }
                        for w in worksheets
                        if isinstance(w, dict)
                    ],
                    "appLanguage": app_lang,
                },
                "contextSlice": {
                    "appId": app_id,
                    "worksheetIdByName": ws_id_by_name,
                },
                "worksheetContextSlice": {"worksheets": slim_ws_ctx},
                "desc": "按示例规范填报业务记录，匹配并回读适用的示例成员与附件",
            })

    # 保留目标工作表的完整设计，避免各步骤自行挑字段时丢失后续用途。
    worksheets_by_name = {w.get("name"): w for w in worksheets if isinstance(w, dict)}
    for task in tasks:
        if task["target"].get("type") == "worksheet":
            worksheet = worksheets_by_name.get(task["target"].get("name"))
            if worksheet is not None:
                task["planSlice"]["worksheet"] = worksheet
    return unique_task_paths(app_dir, tasks)


def extract_h2_sections(md_text: str, keywords: List[str]) -> str:
    """从大型指南中按二级标题关键词提取指定章节，避免塞入数十 KB 无关内容。"""
    lines = md_text.splitlines(keepends=True)
    spans = []
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            spans.append((idx, line.strip()))
    if not spans:
        return md_text
    selected = []
    for pos, (start, title) in enumerate(spans):
        end = spans[pos + 1][0] if pos + 1 < len(spans) else len(lines)
        if any(kw in title for kw in keywords):
            selected.extend(lines[start:end])
    return "".join(selected).strip() + "\n" if selected else md_text


def _slim_worksheet_list(ws_list: List[ Any ]) -> List[Dict[str, Any]]:
    """无损剥离下游（页面/助手/角色/工作流）无需使用的纯 UI 分段 Divider、栅格 layout、advancedSettings 与默认 false/空属性。"""
    out = []
    for w in ws_list:
        if not isinstance(w, dict):
            continue
        w_copy = dict(w)
        raw_fields = w_copy.get("fields")
        if isinstance(raw_fields, list):
            slim_fields = []
            for f in raw_fields:
                if not isinstance(f, dict) or f.get("type") == "Divider":
                    continue
                sf: Dict[str, Any] = {
                    "id": f.get("id", ""),
                    "name": f.get("name", ""),
                    "type": f.get("type", ""),
                    "alias": f.get("alias", ""),
                }
                for flag in ("required", "isTitle", "isReadOnly", "isHidden", "isHiddenOnCreate", "isUnique"):
                    if f.get(flag) is True:
                        sf[flag] = True
                if f.get("defaultValue"):
                    sf["defaultValue"] = f["defaultValue"]
                raw_cfg = f.get("config")
                if isinstance(raw_cfg, dict) and raw_cfg:
                    cfg = {k: v for k, v in raw_cfg.items() if k != "advancedSettings" and v not in (None, "", [], {})}
                    if cfg:
                        sf["config"] = cfg
                slim_fields.append(sf)
            w_copy["fields"] = slim_fields
        out.append(w_copy)
    return out


def _format_task_context_for_bundle(task_ctx_data: Dict[str, Any]) -> str:
    """将 taskContext 转为紧凑易读的 JSON 文本：对 worksheetContextSlice 中的每个字段对象采用单行 JSON 表示，避免 1 个字段展开成 30 行撑爆分卷数。"""
    ctx_copy = dict(task_ctx_data)
    ws_slice = ctx_copy.get("worksheetContextSlice")
    if isinstance(ws_slice, list):
        ctx_copy["worksheetContextSlice"] = _slim_worksheet_context_marker(ws_slice)
    elif isinstance(ws_slice, dict) and isinstance(ws_slice.get("worksheets"), list):
        ws_dict = dict(ws_slice)
        ws_dict["worksheets"] = _slim_worksheet_context_marker(ws_slice["worksheets"])
        ctx_copy["worksheetContextSlice"] = ws_dict

    dumped = json.dumps(ctx_copy, ensure_ascii=False, indent=2)
    # 将标记占位符还原为单行字段 JSON
    return _restore_inline_field_markers(dumped)


_INLINE_FIELD_REGISTRY: List[str] = []


def _slim_worksheet_context_marker(ws_list: List[Any]) -> List[Dict[str, Any]]:
    _INLINE_FIELD_REGISTRY.clear()
    slimmed = _slim_worksheet_list(ws_list)
    for w in slimmed:
        fields = w.get("fields")
        if isinstance(fields, list):
            markers = []
            for f in fields:
                idx = len(_INLINE_FIELD_REGISTRY)
                _INLINE_FIELD_REGISTRY.append(json.dumps(f, ensure_ascii=False))
                markers.append(f"__INLINE_FIELD_{idx}__")
            w["fields"] = markers
    return slimmed


def _restore_inline_field_markers(dumped: str) -> str:
    for idx, inline_json in enumerate(_INLINE_FIELD_REGISTRY):
        dumped = dumped.replace(f'"__INLINE_FIELD_{idx}__"', inline_json)
    _INLINE_FIELD_REGISTRY.clear()
    return dumped


def compile_task_bundles(
    app_dir: str,
    skill_root: str,
    task_def: Dict[str, Any],
    task_ctx_data: Dict[str, Any],
    max_lines: int = 700,
    max_bytes: int = 41000,
) -> List[str]:
    """
    复刻线上 MDAgentService 的 inline:true 预编译机制：
    将 stepFile (SOP) + 必读 references 全文 + taskContext 数据打包为 .build/task-bundles/{taskId}*.md，
    按行数和字节数无损分卷，供执行器按宿主读取能力读取。
    """
    bundle_dir = os.path.join(app_dir, ".build", "task-bundles")
    os.makedirs(bundle_dir, exist_ok=True)
    task_id = task_def["taskId"]
    step = str(task_def.get("step", ""))

    # 清理该 taskId 的历史分卷
    for fname in os.listdir(bundle_dir):
        if fname == f"{task_id}.md" or fname.startswith(f"{task_id}.part"):
            try:
                os.remove(os.path.join(bundle_dir, fname))
            except OSError:
                pass

    step_rel = task_def["stepFile"]
    step_text = load_text(os.path.join(skill_root, step_rel))
    ctx_json_str = _format_task_context_for_bundle(task_ctx_data)

    app_id_val = task_ctx_data.get("contextSlice", {}).get("appId", "")
    receipt_contract = load_text(os.path.join(skill_root, "build", "OUTPUT_CONTRACT.md"))
    acceptance_rules = extract_h2_sections(receipt_contract, ["派发与回执共用的本步验收规则"])
    sections: List[str] = [
        f"# 预编译任务执行包：{task_def.get('taskName', task_id)}\n\n"
        f"- **Task ID**: `{task_id}` | **Step**: `{step}` | **Run ID**: `{task_ctx_data.get('runId', '')}`\n"
        f"- **MCP Server**: `{task_ctx_data.get('mcpServer', '')}` | **当前目标 `appId`**: `{app_id_val}`\n"
        f"- **准许工具白名单 (`allowedTools`)**: `{json.dumps(task_ctx_data.get('allowedTools', []), ensure_ascii=False)}`\n"
        f"- **回执落盘路径 (`receiptPath`)**: `{task_ctx_data.get('receiptPath', '')}`\n"
        "- **执行范围**：Plan 给出本步的业务目标、对象和用户明确的取舍。开工前读齐任务包中的领域规范正文，结合真实字段、用途与状态落实适用条款。Plan 未逐项列出的配置也按规范补全；区分必须、默认、按需及例外，新增业务政策或权限仍以用户授权为准。\n"
        f"- **接口调用**：配置目标依领域规范确定，参数和可用能力以当前服务的实时 MCP Schema 为准；优先使用支持的原生配置。写入限于本步白名单，必要时只读核对。应用内调用显式携带 `appId`（`{app_id_val}`）。分卷读取及 Schema 定位遵循 `{os.path.join(skill_root, 'HOST_ADAPTER.md')}`。\n"
        "- **完成与续作**：保留规划类型及已建 ID，用写入结果或定向回读核对核心配置。在现有回执记录具体证据及有影响的缺项；已有对象在原对象补齐，续作先核对 previousReceipt 和线上状态。回执写入 `receiptPath` 后直接输出简短总结并结束当前轮次，切勿调用 `send_message` 等跨代理通信工具向父会话发送消息。\n\n"
        f"{acceptance_rules}\n"
        f"---\n\n## [1] 步骤执行 SOP (`{step_rel}`)\n\n{step_text.strip()}\n\n"
    ]

    plan_dump = json.dumps(task_def.get("planSlice", {}), ensure_ascii=False).lower()
    ref_rel_list = task_def.get("references") or []
    # 示例规范含写入所需的资源表，置于全应用字段清单之前。
    context_section = f"专属任务上下文数据 (`taskContext`)\n\n```json\n{ctx_json_str}\n```\n"
    if step != "5":
        sections[0] += f"---\n\n## [2] {context_section}"
    for idx, ref_rel in enumerate(ref_rel_list, start=2 if step == "5" else 3):
        # Step 2a 若不涉及自定义自由字段，无需内联 custom-field-spec
        if step == "2a" and "custom-field-spec" in ref_rel:
            if not any(k in plan_dump for k in ("customfield", "customwidget", "自由字段", "自定义字段", "48", "54")):
                continue
        ref_text = load_text(os.path.join(skill_root, ref_rel))
        if not ref_text:
            continue
        # Step 8 角色权限只需 hap-app-design-guide 中的角色与外部门户章节
        if step == "8" and ref_rel.endswith("hap-app-design-guide.md"):
            ref_text = extract_h2_sections(ref_text, ["角色权限", "外部门户"])
        sections.append(f"---\n\n## [{idx}] 必读领域规范全文 (`{ref_rel}`)\n\n{ref_text.strip()}\n")

    if step == "5":
        sections.append(f"---\n\n## [{len(sections) + 1}] {context_section}")

    full_lines = ("\n".join(sections)).splitlines(keepends=True)

    # 按行数与 UTF-8 字节数双重安全阈值切分分卷
    chunks: List[List[str]] = []
    cur_lines: List[str] = []
    cur_bytes = 0
    header_reserve_bytes = 350

    for line in full_lines:
        lb = len(line.encode("utf-8"))
        if cur_lines and (len(cur_lines) + 1 > max_lines or cur_bytes + lb + header_reserve_bytes > max_bytes):
            chunks.append(cur_lines)
            cur_lines = []
            cur_bytes = 0
        cur_lines.append(line)
        cur_bytes += lb
    if cur_lines:
        chunks.append(cur_lines)

    out_paths: List[str] = []
    total_parts = len(chunks)
    for i, ch in enumerate(chunks, start=1):
        if total_parts == 1:
            p = os.path.join(bundle_dir, f"{task_id}.md")
            banner = "> **[完整单卷 1/1]** 本文件已内联 SOP、专属数据与全部必读规范正文，无需额外读取外部参考文档。\n\n"
        else:
            p = os.path.join(bundle_dir, f"{task_id}.part{i}.md")
            banner = f"> **[预编译任务包 分卷 {i}/{total_parts}]** 按宿主适配的读取方式读齐全部 {total_parts} 卷后执行。\n\n"
        with open(p, "w", encoding="utf-8") as f:
            f.write(banner + "".join(ch))
        out_paths.append(p)

    return out_paths


def cmd_init(app_dir: str, skill_dir: str, mcp_server: str) -> Dict[str, Any]:
    app_dir = os.path.abspath(app_dir)
    if not isinstance(mcp_server, str) or not mcp_server.strip():
        raise ValueError("init 必须指定入口已选定的 --mcp-server。")
    mcp_server = mcp_server.strip()
    run_path = os.path.join(app_dir, ".build", "run.json")
    if os.path.exists(run_path):
        existing = require_run(app_dir)
        if existing["mcpServer"] != mcp_server:
            raise ValueError(f"工程环境为 {existing['mcpServer']}，与本次选择不一致；请使用对应工程，不能覆盖原环境。")
        return {"runId": existing["runId"], "executionMode": "subagent_required",
                "initialized": False, "reused": True, "buildDir": os.path.dirname(run_path)}
    build_dir = os.path.dirname(run_path)
    if os.path.isdir(build_dir) and any(files for _, _, files in os.walk(build_dir)):
        raise ValueError("已有构建产物但缺少 run.json；请核对并恢复原批次，禁止重新初始化后重复写入。")
    # 若位于 .hap-copilot/ 隐藏工作目录内，自动写入 .gitignore 防止污染宿主仓库
    parts = app_dir.split(os.sep)
    if ".hap-copilot" in parts:
        idx = parts.index(".hap-copilot")
        hidden_root = os.sep.join(parts[: idx + 1]) or os.sep
        os.makedirs(hidden_root, exist_ok=True)
        gi_path = os.path.join(hidden_root, ".gitignore")
        if not os.path.exists(gi_path):
            with open(gi_path, "w", encoding="utf-8") as f:
                f.write("*\n")
    build_dir = os.path.join(app_dir, ".build")
    os.makedirs(os.path.join(build_dir, "task-context"), exist_ok=True)
    os.makedirs(os.path.join(build_dir, "task-bundles"), exist_ok=True)
    os.makedirs(os.path.join(build_dir, "receipts"), exist_ok=True)
    os.makedirs(os.path.join(build_dir, "artifacts"), exist_ok=True)

    run_id = f"build-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:12]}"
    run_data = {
        "runId": run_id,
        "appDir": app_dir,
        "skillDir": os.path.abspath(skill_dir),
        "mcpServer": mcp_server,
        "executionMode": "subagent_required",
        "createdAt": datetime.datetime.now().isoformat(),
        "status": "active",
    }
    save_json(os.path.join(build_dir, "run.json"), run_data)
    return {
        "runId": run_id,
        "executionMode": "subagent_required",
        "initialized": True,
        "buildDir": build_dir,
    }


def cmd_prepare(app_dir: str, progress: Optional[str], include_pending_capacity: bool = True) -> Dict[str, Any]:
    app_dir = os.path.abspath(app_dir)
    skill_root = get_skill_root()
    context = load_json(os.path.join(app_dir, "hap-context.json")) or {}
    run_data = require_run(app_dir)
    run_id = run_data.get("runId", "")
    registry = load_json(os.path.join(app_dir, ".build", "dispatch-registry.json")) or {}

    current_progress = progress or context.get("progress", "")
    stage = current_progress if current_progress else "step1"

    all_tasks = get_stage_tasks_definitions(app_dir, stage)
    ready_tasks = []
    running_tasks = []
    pending_capacity_tasks = []
    completed_task_ids = []
    blocked_tasks = []
    failed_task_ids = []

    for t in all_tasks:
        task_id = t["taskId"]
        abs_receipt = os.path.join(app_dir, t["receiptPath"])
        state, issue = task_state(abs_receipt, task_id, run_id, registry.get(task_id, {}), t.get("target"))
        if state == "blocked":
            blocked_tasks.append({"taskId": task_id, "receiptPath": abs_receipt, "reason": issue})
            continue
        if state == "succeeded":
            completed_task_ids.append(task_id)
            continue
        if state == "running":
            running_tasks.append(task_id)
            continue
        if state == "failed":
            failed_task_ids.append(task_id)
        if state == "pending_capacity":
            pending_capacity_tasks.append(task_id)
            if not include_pending_capacity:
                continue
        abs_task_ctx = os.path.join(app_dir, t["taskContextPath"])
        ref_rel_list = t.get("references") or ([t["primaryRef"]] if t.get("primaryRef") else [])
        abs_refs = [os.path.join(skill_root, r) for r in ref_rel_list]
        allowed_tools = t.get("allowedTools", [])
        host_adapter = os.path.join(skill_root, "HOST_ADAPTER.md")
        source_files = {
            "plan": os.path.join(app_dir, "hap-plan.json"),
            "context": os.path.join(app_dir, "hap-context.json"),
            "worksheetContext": os.path.join(app_dir, "worksheetContext.json"),
            "receipts": os.path.join(app_dir, ".build", "receipts"),
            "artifacts": os.path.join(app_dir, ".build", "artifacts"),
        }

        task_ctx_data = {
            "taskId": task_id,
            "taskName": t.get("taskName", task_id),
            "runId": run_id,
            "step": t["step"],
            "target": t["target"],
            "mcpServer": run_data["mcpServer"],
            "stepFile": os.path.join(skill_root, t["stepFile"]),
            "hostAdapter": host_adapter,
            "sourceFiles": source_files,
            "references": abs_refs,
            "allowedTools": allowed_tools,
            "receiptPath": abs_receipt,
            "planSlice": t.get("planSlice", {}),
            "contextSlice": t.get("contextSlice", {}),
            "worksheetContextSlice": t.get("worksheetContextSlice", {}),
        }
        if state == "failed" and os.path.exists(abs_receipt):
            task_ctx_data["previousReceipt"] = load_json(abs_receipt)
        save_json(abs_task_ctx, task_ctx_data)

        bundle_files = compile_task_bundles(app_dir, skill_root, t, task_ctx_data)
        ready_entry = {
            "taskId": task_id,
            "taskName": t.get("taskName", task_id),
            "step": t["step"],
            "stepFile": os.path.join(skill_root, t["stepFile"]),
            "primaryRef": abs_refs[0] if abs_refs else "",
            "references": abs_refs,
            "bundleFiles": bundle_files,
            "hostAdapter": host_adapter,
            "sourceFiles": source_files,
            "allowedTools": allowed_tools,
            "taskContext": abs_task_ctx,
            "receiptPath": abs_receipt,
            "isBackground": t.get("isBackground", False),
            "desc": t.get("desc", ""),
            "resume": state == "failed",
        }
        ready_tasks.append(ready_entry)

    blocking_ids = [t["taskId"] for t in all_tasks if not t.get("isBackground", False)]
    can_advance = all(tid in completed_task_ids for tid in blocking_ids)

    manifest_data = {
        "stage": stage,
        "currentProgress": current_progress,
        "totalTasks": len(all_tasks),
        "readyCount": len(ready_tasks),
        "runningCount": len(running_tasks),
        "pendingCapacityCount": len(pending_capacity_tasks),
        "completedCount": len(completed_task_ids),
        "failedCount": len(failed_task_ids),
        "blockedCount": len(blocked_tasks),
        "updatedAt": datetime.datetime.now().isoformat(),
    }
    save_json(os.path.join(app_dir, ".build", "task-manifest.json"), manifest_data)

    return {
        "runId": run_id,
        "progress": current_progress,
        "stage": stage,
        "totalExpected": len(all_tasks),
        "readyTaskCount": len(ready_tasks),
        "runningTaskCount": len(running_tasks),
        "pendingCapacityCount": len(pending_capacity_tasks),
        "completedCount": len(completed_task_ids),
        "failedCount": len(failed_task_ids),
        "blockedCount": len(blocked_tasks),
        "failedTaskIds": failed_task_ids,
        "blockedTasks": blocked_tasks,
        "canAdvance": can_advance,
        "readyTasks": ready_tasks,
        "sourceFiles": {
            "plan": os.path.join(app_dir, "hap-plan.json"),
            "context": os.path.join(app_dir, "hap-context.json"),
            "receipts": os.path.join(app_dir, ".build", "receipts"),
        },
    }


def cmd_record_dispatch(app_dir: str, task_id: str, agent_id: str, status: str, reason: str = "") -> Dict[str, Any]:
    app_dir = os.path.abspath(app_dir)
    run_data = require_run(app_dir)
    record_file = os.path.join(app_dir, ".build", "dispatch-registry.json")
    registry = load_json(record_file) or {}

    resume_version = ""
    receipt_path = os.path.join(app_dir, ".build", "receipts", task_id + ".json")
    if status == "running":
        previous_state, _ = task_state(receipt_path, task_id, run_data["runId"], registry.get(task_id, {}))
        if previous_state == "failed" and registry.get(task_id, {}).get("agentId") and os.path.exists(receipt_path):
            resume_version = receipt_version(receipt_path)
        elif previous_state == "running" and registry.get(task_id, {}).get("agentId") == agent_id:
            resume_version = registry[task_id].get("resumeReceiptVersion", "")
    registry[task_id] = {
        "taskId": task_id,
        "agentId": agent_id,
        "runId": run_data.get("runId", ""),
        "status": status,
        "reason": reason,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    if resume_version:
        registry[task_id]["resumeReceiptVersion"] = resume_version
    save_json(record_file, registry)
    return {"taskId": task_id, "status": status, "agentId": agent_id, "recorded": True}


def cmd_reset_task(app_dir: str, task_id: str) -> Dict[str, Any]:
    """核实线上状态后，安全归档损坏/阻塞的异常回执并解除死锁，使该任务重新进入 readyTasks。"""
    app_dir = os.path.abspath(app_dir)
    require_run(app_dir)
    receipt_path = os.path.join(app_dir, ".build", "receipts", task_id + ".json")
    archived_path = ""
    if os.path.exists(receipt_path):
        archive_dir = os.path.join(app_dir, ".build", "archived-receipts")
        os.makedirs(archive_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        archived_path = os.path.join(archive_dir, f"{task_id}.{ts}.bak")
        os.replace(receipt_path, archived_path)

    record_file = os.path.join(app_dir, ".build", "dispatch-registry.json")
    registry = load_json(record_file) or {}
    if task_id in registry:
        del registry[task_id]
        save_json(record_file, registry)

    return {"taskId": task_id, "reset": True, "archivedReceipt": archived_path}


def cmd_validate_plan(app_dir: str) -> Dict[str, Any]:
    """构建前静态检查 hap-plan.json 的主从子表闭环、导航分组覆盖及自定义动作人工输入入口完整性。"""
    app_dir = os.path.abspath(app_dir)
    plan_path = os.path.join(app_dir, "hap-plan.json")
    plan = load_json(plan_path)
    if not isinstance(plan, dict):
        raise ValueError(f"未找到合法的 hap-plan.json：{plan_path}")

    errors: List[str] = []
    warnings: List[str] = []

    worksheets = [w for w in (plan.get("worksheets") or []) if isinstance(w, dict)]
    ws_by_name = {w.get("name", ""): w for w in worksheets if w.get("name")}
    nav_groups = set(plan.get("navGroups") or plan.get("sections") or [])

    # 1. 导航分组覆盖检查（子表不独立占顶层导航项，随主表归组）
    if nav_groups:
        for obj_kind, items in (
            ("工作表", [w for w in worksheets if w.get("worksheetType") != "subTable"]),
            ("自定义页面", [p for p in (plan.get("customPages") or []) if isinstance(p, dict)]),
            ("AI助手", [b for b in (plan.get("aiAssistants") or plan.get("chatbots") or []) if isinstance(b, dict)]),
        ):
            for it in items:
                grp = it.get("groupName") or it.get("navGroup") or it.get("section") or ""
                if grp and grp not in nav_groups:
                    errors.append(f"{obj_kind} [{it.get('name')}] 的分组 [{grp}] 未在顶层 navGroups 中声明。")

    # 2. 主从子表双向挂载闭环检查 & 非法伪文本类型 (Textarea/LongText) 检查
    for ws in worksheets:
        ws_name = ws.get("name", "")
        for f_str in (ws.get("fields") or ws.get("customFields") or []):
            if isinstance(f_str, str):
                for bad_t in ("Textarea", "LongText", "MultilineText"):
                    if f"({bad_t})" in f_str or f"({bad_t}:" in f_str:
                        errors.append(
                            f"工作表 [{ws_name}] 的字段 [{f_str}] 使用了非法类型 {bad_t}：明道云单行与多行纯文本统一使用 (Text)，富文本使用 (RichText)。"
                        )
        if ws.get("worksheetType") == "subTable":
            parent_name = ws.get("parentWorksheet", "")
            parent_ws = ws_by_name.get(parent_name)
            if not parent_name or not parent_ws:
                errors.append(f"子表 [{ws_name}] 缺少有效的主表 parentWorksheet（当前：{parent_name or '空'}）。")
            else:
                p_fields = [str(f) for f in (parent_ws.get("fields") or parent_ws.get("customFields") or [])]
                if not any(f"(SubTable:{ws_name})" in f for f in p_fields):
                    errors.append(f"子表 [{ws_name}] 未在主表 [{parent_name}] 的 fields 中声明 (SubTable:{ws_name}) 挂载字段。")

    # 3. 自定义动作类型与人工输入入口检查（拦截错把需填表操作设为 triggerWorkflow）
    action_groups: List[Tuple[str, Dict[str, Any]]] = []
    for ws in worksheets:
        ws_n = ws.get("name", "")
        for act in (ws.get("customActions") or ws.get("worksheetCustomActions") or []):
            if isinstance(act, dict):
                action_groups.append((ws_n, act))
    for grp in (plan.get("customActions") or plan.get("worksheetCustomActions") or []):
        if isinstance(grp, dict):
            ws_n = grp.get("worksheet", "")
            for act in (grp.get("actions") or []):
                if isinstance(act, dict):
                    action_groups.append((ws_n, act))

    forbidden_approval_btns = {"审批通过", "审批驳回", "审批否决", "同意审批", "拒绝审批"}
    input_signal_keywords = (
        "发起借阅", "申请续借", "续借", "登记异常", "登记损坏", "损坏", "遗失", "赔偿", "报修",
        "填写", "输入", "录入", "选择借阅人", "选择读者", "选择人员", "指派", "指定日期", "应还日期",
    )

    seen_actions = set()
    for ws_name, act in action_groups:
        act_name = str(act.get("name") or act.get("actionName") or "").strip()
        if not act_name:
            continue
        dedup_key = f"{ws_name}::{act_name}"
        if dedup_key in seen_actions:
            continue
        seen_actions.add(dedup_key)

        if act_name in forbidden_approval_btns:
            errors.append(f"工作表 [{ws_name}] 存在禁用动作按钮 [{act_name}]：审批通过/驳回必须由工作流 approval_block 处理，严禁拆成按钮。")

        act_type = str(act.get("type") or act.get("clickType") or "").strip()
        if act_type == "createRelatedRecord":
            target_ws = str(act.get("targetWorksheet") or "").strip()
            rel_field = str(act.get("relateFieldName") or "").strip()
            if not target_ws or not rel_field:
                errors.append(f"动作 [{ws_name}/{act_name}] (createRelatedRecord) 必须同时声明 targetWorksheet 与 relateFieldName。")
            else:
                if ws_by_name and target_ws not in ws_by_name:
                    errors.append(f"动作 [{ws_name}/{act_name}] 的 targetWorksheet [{target_ws}] 在 worksheets 中不存在。")
                src_ws = ws_by_name.get(ws_name)
                if src_ws:
                    s_fields = [str(f) for f in (src_ws.get("fields") or src_ws.get("customFields") or [])]
                    if not any(f.startswith(f"{rel_field}(Relation:") for f in s_fields):
                        errors.append(
                            f"动作 [{ws_name}/{act_name}] 引用的关联字段 [{rel_field}] 未在源表 [{ws_name}] 的 fields 中声明为 Relation 字段。"
                        )

        needs_wf = (act_type == "triggerWorkflow") or bool(act.get("runWorkflowAfterSubmit"))
        if needs_wf:
            hints = act.get("intentHints")
            if not isinstance(hints, list) or len(hints) == 0:
                errors.append(f"动作 [{ws_name}/{act_name}] 启用了工作流但缺少非空 intentHints 数组。")

        if act_type == "triggerWorkflow":
            combined_text = " ".join([
                act_name,
                str(act.get("description") or ""),
                json.dumps(act.get("intentHints") or [], ensure_ascii=False),
                json.dumps(act.get("requirements") or [], ensure_ascii=False),
            ])
            # 剔除后台自动赋值与关联字段定语（如“将指派无人机状态置为…”“自动填写”），避免名词定语误触发人工输入警告
            sanitized_text = combined_text
            for benign_phrase in (
                "指派无人机", "指派设备", "指派车辆", "指派人员", "已指派", "所指派",
                "自动填写", "自动写入", "自动录入", "自动设置", "无需填写", "无需输入", "零输入",
            ):
                sanitized_text = sanitized_text.replace(benign_phrase, "")
            matched_kw = [kw for kw in input_signal_keywords if kw in sanitized_text]
            if matched_kw:
                warnings.append(
                    f"动作 [{ws_name}/{act_name}] 当前为 triggerWorkflow（无输入表单），但命中疑似需人工输入的语义（{'/'.join(matched_kw[:3])}）："
                    f"若操作时需现场选择人员、填写日期/金额/原因或异常类型，请改为 createRelatedRecord 或 updateCurrentRecord 并开启 runWorkflowAfterSubmit: true！"
                )

    # 4. 仅对同一表、不同动作的完整文本意图做保守比较：去掉各自动作名前缀，避免共用模板掩盖业务差异。
    intents: Dict[Tuple[str, Tuple[str, ...]], List[str]] = {}
    distinct_actions = set()
    for ws_name, act in action_groups:
        name = str(act.get("name") or act.get("actionName") or "").strip()
        key = (ws_name, name)
        if not ws_name or not name or key in distinct_actions:
            continue
        distinct_actions.add(key)
        hints = act.get("intentHints")
        if not isinstance(hints, list) or not hints:
            continue
        normalized = []
        for hint in hints:
            value = hint.get("label") if isinstance(hint, dict) else hint
            if not isinstance(value, str) or not value.strip():
                normalized = []
                break
            value = value.strip()
            if value.startswith(name):
                value = value[len(name):].lstrip(" ：:，,。;；-—\t\n")
            value = " ".join(value.split())
            if not value:
                normalized = []
                break
            normalized.append(value)
        if normalized:
            intents.setdefault((ws_name, tuple(normalized)), []).append(name)
    for (ws_name, _), names in intents.items():
        if len(names) > 1:
            warnings.append(f"工作表 [{ws_name}] 的动作 [{'/'.join(names)}] 去除动作名前缀后意图相同，请核对各自动作的状态、结果与权限。")

    # 5. 可选显式绑定只作提示，不改变旧方案与静态预检通过条件。
    for page in (plan.get("customPages") or []):
        if not isinstance(page, dict) or "viewBindings" not in page:
            continue
        bindings = page.get("viewBindings")
        if not isinstance(bindings, dict):
            warnings.append(f"页面 [{page.get('name', '')}] 的 viewBindings 应为组件名到工作表和视图的映射。")
            continue
        components = set()
        for component in page.get("components") or []:
            if isinstance(component, str) and component.endswith("(View)"):
                components.add(component[:-len("(View)")].strip())
        for component, binding in bindings.items():
            if not isinstance(binding, dict):
                warnings.append(f"页面 [{page.get('name', '')}] 组件 [{component}] 的视图绑定应包含 worksheet 和 view。")
                continue
            ws_name, view_name = binding.get("worksheet"), binding.get("view")
            if not isinstance(ws_name, str) or not ws_name.strip() or not isinstance(view_name, str) or not view_name.strip():
                warnings.append(f"页面 [{page.get('name', '')}] 组件 [{component}] 的视图绑定缺少 worksheet 或 view。")
                continue
            if component not in components:
                warnings.append(f"页面 [{page.get('name', '')}] 的绑定组件 [{component}] 不在 View 组件列表中。")
            ws = ws_by_name.get(ws_name)
            if not ws:
                warnings.append(f"页面 [{page.get('name', '')}] 组件 [{component}] 绑定的工作表 [{ws_name}] 不存在。")
                continue
            view_names = {v.rsplit("(", 1)[0].strip() for v in (ws.get("views") or [])
                          if isinstance(v, str) and v.endswith(")") and "(" in v}
            if view_name not in view_names:
                warnings.append(f"页面 [{page.get('name', '')}] 组件 [{component}] 绑定的视图 [{ws_name}/{view_name}] 不存在。")

    return {
        "passed": len(errors) == 0,
        "errorCount": len(errors),
        "warningCount": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def cmd_resolve_task(app_dir: str, task_id: str, evidence: str, outputs_json: str = "") -> Dict[str, Any]:
    """跨步骤返工后依据实际修复及核验证据归并回执；未实测时如实说明。"""
    app_dir = os.path.abspath(app_dir)
    run_data = require_run(app_dir)
    run_id = run_data["runId"]
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("resolve-task 必须提供非空的线上核验依据 --evidence。")

    extra_outputs: Dict[str, Any] = {}
    if outputs_json and outputs_json.strip():
        try:
            parsed = json.loads(outputs_json)
            if not isinstance(parsed, dict):
                raise ValueError("outputs-json 必须是 JSON 对象")
            extra_outputs = parsed
        except Exception as exc:
            raise ValueError(f"--outputs-json 不是合法的 JSON 对象：{exc}") from exc

    context = load_json(os.path.join(app_dir, "hap-context.json")) or {}
    current_stage = context.get("progress", "step1") or "step1"
    matched_def: Optional[Dict[str, Any]] = None
    for candidate_stage in (
        current_stage,
        "step1",
        "app_created",
        "step2a_done",
        "worksheets_created",
        "fields_refreshed",
        "config_completed",
    ):
        for t in get_stage_tasks_definitions(app_dir, candidate_stage):
            if t["taskId"] == task_id:
                matched_def = t
                break
        if matched_def is not None:
            break

    receipt_rel = matched_def["receiptPath"] if matched_def else os.path.join(".build", "receipts", f"{task_id}.json")
    receipt_path = os.path.join(app_dir, receipt_rel)
    previous = load_json(receipt_path)
    archived_path = ""
    if os.path.exists(receipt_path):
        archive_dir = os.path.join(app_dir, ".build", "archived-receipts")
        os.makedirs(archive_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        archived_path = os.path.join(archive_dir, f"{task_id}.reconciled-{ts}.bak")
        with open(receipt_path, "rb") as src_f, open(archived_path, "wb") as dst_f:
            dst_f.write(src_f.read())

    merged_outputs: Dict[str, Any] = {}
    if isinstance(previous, dict) and isinstance(previous.get("outputs"), dict):
        merged_outputs.update(previous["outputs"])
    merged_outputs.update(extra_outputs)

    target_meta = (
        matched_def["target"]
        if matched_def
        else (previous.get("target") if isinstance(previous, dict) and isinstance(previous.get("target"), dict) else {"type": "task", "name": task_id})
    )
    step_val = (
        matched_def["step"]
        if matched_def
        else (str(previous.get("step", "")) if isinstance(previous, dict) else "")
    )

    reconciled_receipt = {
        "taskId": task_id,
        "runId": run_id,
        "executor": {"kind": "reconciled", "agentId": "orchestrator-reconciled"},
        "step": step_val,
        "target": target_meta,
        "status": "succeeded",
        "outputs": merged_outputs,
        "verification": {
            "passed": True,
            "evidence": [evidence.strip()],
        },
        "issues": [],
    }
    grp_err = _group_receipt_missing_worksheets(reconciled_receipt, matched_def["target"] if matched_def else None)
    if grp_err:
        raise ValueError(grp_err)

    save_json(receipt_path, reconciled_receipt)

    record_file = os.path.join(app_dir, ".build", "dispatch-registry.json")
    registry = load_json(record_file) or {}
    registry[task_id] = {
        "taskId": task_id,
        "agentId": "orchestrator-reconciled",
        "runId": run_id,
        "status": "succeeded",
        "reason": "reconciled",
        "timestamp": datetime.datetime.now().isoformat(),
    }
    save_json(record_file, registry)

    return {
        "taskId": task_id,
        "resolved": True,
        "receiptPath": receipt_path,
        "archivedPreviousReceipt": archived_path,
    }


def cmd_refresh(app_dir: str) -> Dict[str, Any]:
    app_dir = os.path.abspath(app_dir)
    context = load_json(os.path.join(app_dir, "hap-context.json")) or {}
    run_data = require_run(app_dir)
    run_id = run_data.get("runId", "")
    stage = context.get("progress", "step1")

    all_tasks = get_stage_tasks_definitions(app_dir, stage)
    registry = load_json(os.path.join(app_dir, ".build", "dispatch-registry.json")) or {}

    counts = {"succeeded": 0, "running": 0, "pending_capacity": 0, "failed": 0, "blocked": 0, "planned": 0}
    succeeded_ids = set()
    for t in all_tasks:
        tid = t["taskId"]
        r_path = os.path.join(app_dir, t["receiptPath"])
        state, _ = task_state(r_path, tid, run_id, registry.get(tid, {}), t.get("target"))
        counts[state if state in counts else "planned"] += 1
        if state == "succeeded":
            succeeded_ids.add(tid)

    blocking_ids = [t["taskId"] for t in all_tasks if not t.get("isBackground", False)]

    return {
        "stage": stage,
        "total": len(all_tasks),
        "succeeded": counts["succeeded"],
        "running": counts["running"],
        "pendingCapacity": counts["pending_capacity"],
        "failed": counts["failed"],
        "blocked": counts["blocked"],
        "ready": counts["planned"],
        "phaseComplete": all(tid in succeeded_ids for tid in blocking_ids),
    }


def workflow_publication_status(outputs: Dict[str, Any]) -> str:
    status = outputs.get("status")
    if isinstance(status, str) and status:
        return status
    # 兼容旧回执的显式布尔标记。processId 在按钮建壳时就有，不能证明发布。
    if isinstance(outputs.get("published"), bool):
        return "published" if outputs["published"] else "draft"
    return "unknown"


def rule_condition_matches_fields(condition, fields):
    if not isinstance(condition, dict):
        return False
    if condition.get("type") == "group":
        children = condition.get("children")
        return (isinstance(children, list) and bool(children)
                and all(rule_condition_matches_fields(child, fields) for child in children))
    fid = condition.get("fieldId") or condition.get("field")
    return (condition.get("type") == "condition" and isinstance(fid, str)
            and fid in fields and bool(condition.get("operator")))


def has_rule_evidence(app_dir: str, outputs: Dict[str, Any], intents=()) -> bool:
    ids = outputs.get("ruleIds")
    checks = outputs.get("ruleChecks")
    if not isinstance(ids, list) or not isinstance(checks, list) or not checks:
        return False
    sheet_id = outputs.get("worksheetId")
    if not isinstance(sheet_id, str) or not sheet_id or os.path.basename(sheet_id) != sheet_id:
        return False
    artifact = load_json(os.path.join(app_dir, ".build", "artifacts", f"worksheet-{sheet_id}.json")) or {}
    if not isinstance(artifact, dict) or artifact.get("worksheetId") != sheet_id:
        return False
    fields = {f["id"]: f for f in artifact.get("fields", []) if isinstance(f, dict) and f.get("id")}
    covered, verified_ids = set(), set()
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("intent"), str) or not check["intent"].strip():
            return False
        covered.add(check["intent"].strip())
        src_intent = check.get("sourceIntent")
        if isinstance(src_intent, str) and src_intent.strip():
            covered.add(src_intent.strip())
        if "ruleId" in check:
            rule_id = check["ruleId"]
            if not isinstance(rule_id, str) or not rule_id.strip() or not check.get("name") or check.get("enabled") is not True:
                return False
            if not rule_condition_matches_fields(check.get("conditions"), fields):
                return False
            verified_ids.add(rule_id)
        else:
            raw_field_id, prop = check.get("fieldId"), check.get("property")
            field_ids_list = check.get("fieldIds")
            if isinstance(field_ids_list, list) and field_ids_list:
                fids = [str(x).strip() for x in field_ids_list if str(x).strip()]
            elif isinstance(raw_field_id, str) and raw_field_id.strip():
                fids = [x.strip() for x in raw_field_id.split(",") if x.strip()]
            else:
                return False
            if not fids or not isinstance(prop, str) or prop in {"name", "alias", "id"} or "value" not in check:
                return False
            if not isinstance(check.get("reason"), str) or not check["reason"].strip():
                return False
            for fid in fids:
                field = fields.get(fid, {})
                if prop not in field or field[prop] != check["value"]:
                    return False
    if not (all(isinstance(i, str) for i in ids) and verified_ids == set(ids)):
        return False
    valid_intents = [i.strip() for i in set(intents) if isinstance(i, str) and i.strip()]
    if not valid_intents:
        return True
    # 支持子代理将复合意图拆分为多条精细规则或字段属性核验：逐字命中、子串包含，或已验真的规则/拆分检查项覆盖规划意图数
    all_matched = all(
        i in covered or any(i in c or c in i for c in covered)
        for i in valid_intents
    )
    return (
        all_matched
        or (len(verified_ids) >= len(valid_intents))
        or (len(checks) > len(valid_intents) and len(verified_ids) >= 1)
    )


def receipt_delivery_notes(app_dir: str, run_id: str) -> List[Dict[str, Any]]:
    """列出本次运行最新回执中需要核对的交付项，独立于阶段推进门禁。"""
    folder = os.path.join(app_dir, ".build", "receipts")
    notes = []
    if not os.path.isdir(folder):
        return notes
    context = load_json(os.path.join(app_dir, "hap-context.json")) or {}
    plan = load_json(os.path.join(app_dir, "hap-plan.json")) or {}
    rule_notes = current_rule_notes(app_dir, context, run_id)
    planned = {w.get("name"): w.get("businessRules") or w.get("businessRulesNotes") or []
               for w in plan.get("worksheets", []) if isinstance(w, dict)}
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".json"):
            continue
        try:
            data = load_json(os.path.join(folder, filename))
        except FileNotFoundError:
            continue  # 并行恢复期间，旧回执可能刚被 reset-task 归档。
        if not isinstance(data, dict) or data.get("runId") != run_id or data.get("taskId") != filename[:-5]:
            continue
        outputs = data.get("outputs")
        outputs = outputs if isinstance(outputs, dict) else {}
        entry = {"taskId": data["taskId"], "issues": data.get("issues") or []}
        step = str(data.get("step") or filename.split("-", 1)[0][4:])
        if step == "3":
            name = outputs.get("worksheetName") or (data.get("target") or {}).get("name")
            if not has_rule_evidence(app_dir, outputs, planned.get(name, []) + rule_notes.get(name, [])):
                entry["ruleEvidenceMissing"] = True
        if step in ("10", "11"):
            status = workflow_publication_status(outputs)
            if status != "published":
                entry["publicationStatus"] = status
        if step == "11" and outputs.get("actionEnabled") is not True:
            entry["actionEnabled"] = False if outputs.get("actionEnabled") is False else "unknown"
        if step == "6":
            if outputs.get("completed") is not True:
                entry["pageCompleted"] = False if outputs.get("completed") is False else "unknown"
            if outputs.get("notes"):
                entry["pageNotes"] = outputs["notes"]
        if entry["issues"] or "ruleEvidenceMissing" in entry or "publicationStatus" in entry or "actionEnabled" in entry or "pageCompleted" in entry or "pageNotes" in entry:
            notes.append(entry)
    return notes


def cmd_finalize(app_dir: str, progress: Optional[str]) -> Dict[str, Any]:
    app_dir = os.path.abspath(app_dir)
    skill_root = get_skill_root()
    context = load_json(os.path.join(app_dir, "hap-context.json")) or {}
    run_data = require_run(app_dir)
    run_id = run_data.get("runId", "")
    registry = load_json(os.path.join(app_dir, ".build", "dispatch-registry.json")) or {}

    current_progress = progress or context.get("progress", "")
    stage = current_progress if current_progress else "step1"

    all_tasks = get_stage_tasks_definitions(app_dir, stage)
    total_expected = len(all_tasks)

    succeeded_tasks = []
    failed_tasks = []
    running_tasks = []
    pending_capacity_tasks = []
    planned_tasks = []
    errors = []

    for t in all_tasks:
        task_id = t["taskId"]
        r_path = os.path.join(app_dir, t["receiptPath"])
        state, issue = task_state(r_path, task_id, run_id, registry.get(task_id, {}), t.get("target"))
        if state == "succeeded":
            succeeded_tasks.append(task_id)
        elif state in {"failed", "blocked"}:
            failed_tasks.append(task_id)
            errors.append(f"任务 [{task_id}] {state}: {issue}")
        elif state == "running":
            running_tasks.append(task_id)
        elif state == "pending_capacity":
            pending_capacity_tasks.append(task_id)
        else:
            planned_tasks.append(task_id)

    blocking_tasks = [t["taskId"] for t in all_tasks if not t.get("isBackground", False)]

    can_advance = set(blocking_tasks).issubset(succeeded_tasks)

    next_progress = current_progress
    stage_outputs: Dict[str, Any] = {}

    if can_advance:
        if stage in ("step1", "initial"):
            r_data = load_json(os.path.join(app_dir, ".build", "receipts", "step1-app-init.json")) or {}
            outputs = r_data.get("outputs", {})
            next_progress = "app_created"
            stage_outputs.update({
                "appId": outputs.get("appId"),
                "sections": len(outputs.get("sectionIdByName", {})),
                "customPages": len(outputs.get("customPageIdByName", {})),
            })

        elif stage in ("app_created", "step2a"):
            ws_id_by_name = dict(context.get("worksheetIdByName", {}))
            has_relation_todo = False
            for t in all_tasks:
                if t["step"] == "2a":
                    r_data = load_json(os.path.join(app_dir, t["receiptPath"])) or {}
                    outputs = r_data.get("outputs", {})
                    ws_name = outputs.get("worksheetName") or t["target"].get("name")
                    ws_id = outputs.get("worksheetId")
                    if ws_name and ws_id:
                        ws_id_by_name[ws_name] = ws_id
                    if outputs.get("relationLayout"):
                        has_relation_todo = True
            next_progress = "step2a_done" if has_relation_todo else "worksheets_created"
            stage_outputs["worksheetsCreated"] = len(ws_id_by_name)

        elif stage in ("step2a_done", "step2b"):
            next_progress = "worksheets_created"
            stage_outputs["relationsConfigured"] = True

        elif stage in ("worksheets_created", "phase2_single_table"):
            merge_script = os.path.join(skill_root, "scripts", "merge_worksheet_context.py")
            res = subprocess.run([sys.executable, merge_script, app_dir], capture_output=True, text=True)
            if res.returncode != 0:
                can_advance = False
                errors.append(f"merge_worksheet_context.py 校验失败: {res.stderr or res.stdout}")
            else:
                view_id_by_name = dict(context.get("viewIdByName", {}))
                action_id_by_name = dict(context.get("actionIdByName", {}))
                chatbot_id_by_name = dict(context.get("chatbotIdByName", {}))
                rule_evidence_by_sheet = []
                for t in all_tasks:
                    r_data = load_json(os.path.join(app_dir, t["receiptPath"])) or {}
                    outputs = r_data.get("outputs", {})
                    if t["step"] == "3":
                        intents = t["planSlice"]["businessRules"] + t["contextSlice"]["businessRulesNotes"]
                        rule_evidence_by_sheet.append(has_rule_evidence(app_dir, outputs, intents))
                    if isinstance(outputs.get("viewIdByName"), dict):
                        view_id_by_name.update(outputs["viewIdByName"])
                    if isinstance(outputs.get("actionIdByName"), dict):
                        action_id_by_name.update(outputs["actionIdByName"])
                    if isinstance(outputs.get("chatbotIdByName"), dict):
                        chatbot_id_by_name.update(outputs["chatbotIdByName"])
                    elif outputs.get("chatbotName") and outputs.get("chatbotId"):
                        chatbot_id_by_name[outputs["chatbotName"]] = outputs["chatbotId"]

                next_progress = "fields_refreshed"
                stage_outputs.update({
                    "fieldsRefreshed": True,
                    "viewsCreated": len(view_id_by_name),
                    "actionsCreated": len(action_id_by_name),
                    "chatbotsCreated": len(chatbot_id_by_name),
                    "businessRulesConfigured": all(rule_evidence_by_sheet),
                })

        elif stage in ("fields_refreshed", "phase3_configs", "page_shells_created", "phase3"):
            role_id_by_name = dict(context.get("roleIdByName", {}))
            wf_designed_count = 0
            for t in all_tasks:
                r_data = load_json(os.path.join(app_dir, t["receiptPath"])) or {}
                outputs = r_data.get("outputs", {})
                if isinstance(outputs.get("roleIdByName"), dict):
                    role_id_by_name.update(outputs["roleIdByName"])
                elif outputs.get("roleName") and outputs.get("roleId"):
                    role_id_by_name[outputs["roleName"]] = outputs["roleId"]
                if outputs.get("workflowDesign") or outputs.get("actionWorkflowDesign"):
                    wf_designed_count += 1

            next_progress = "config_completed"
            stage_outputs.update({
                "rolesCreated": len(role_id_by_name),
                "workflowsDesigned": wf_designed_count,
                "sampleDataDispatched": (
                    "step5-sample-data" in succeeded_tasks
                    or "step5-sample-data" in running_tasks
                    or bool(registry.get("step5-sample-data", {}).get("agentId"))
                ),
            })

        elif stage in ("config_completed", "phase4_deploy"):
            next_progress = "completed"
            stage_outputs["buildCompleted"] = True

    report_data = {
        "schemaVersion": "1.1",
        "runId": run_id,
        "phase": stage,
        "progressBefore": current_progress,
        "taskSummary": {
            "expected": total_expected,
            "succeeded": len(succeeded_tasks),
            "failed": len(failed_tasks),
            "running": len(running_tasks),
            "pendingCapacity": len(pending_capacity_tasks),
            "planned": len(planned_tasks),
            "retryPending": 0,
        },
        "execution": {
            "mode": "subagent_required",
            "subagentExecutionVerified": (all(tid in succeeded_tasks for tid in blocking_tasks) if total_expected > 0 else True),
            "inlineExecutionDetected": False,
        },
        "outputs": stage_outputs,
        "validation": {"passed": can_advance, "errors": errors, "warnings": []},
        "nextProgress": next_progress,
        "canAdvance": can_advance,
        "nextAction": "advance" if can_advance else "prepare",
        "runningTaskIds": running_tasks,
        "pendingCapacityTaskIds": pending_capacity_tasks,
        "plannedTaskIds": planned_tasks,
        "failedTaskIds": failed_tasks,
        "deliveryNotes": receipt_delivery_notes(app_dir, run_id),
    }
    if canonical_stage(stage) == "fields_refreshed" and set(failed_tasks).intersection(blocking_tasks):
        report_data["reviewLaterTasks"] = {
            "prepareProgress": "config_completed",
            "instruction": "准备下一阶段候选包，按各任务的真实字段、角色和入口依赖派发可独立完成项；当前阶段仍按原回执验收。",
        }
    save_json(os.path.join(app_dir, ".build", "phase-report.json"), report_data)
    return report_data


def cmd_advance(app_dir: str) -> Dict[str, Any]:
    app_dir = os.path.abspath(app_dir)
    run_data = require_run(app_dir)
    report = load_json(os.path.join(app_dir, ".build", "phase-report.json"))
    if report and report.get("runId") != run_data["runId"]:
        raise ValueError("阶段报告不属于当前运行，须重新核验本批次回执，不能直接推进。")
    if not report or not report.get("canAdvance"):
        return {
            "advanced": False,
            "nextAction": "prepare" if report else "finalize",
            "reason": "阶段尚未完成；继续核实回执、修复未完成任务并处理无依赖工作。",
        }

    context_path = os.path.join(app_dir, "hap-context.json")
    plan_path = os.path.join(app_dir, "hap-plan.json")
    context = load_json(context_path) or {}
    plan = load_json(plan_path) or {}

    stage = report.get("phase", "")
    next_progress = report.get("nextProgress", "")
    if canonical_stage(stage) != canonical_stage(context.get("progress", "")):
        return {
            "advanced": False,
            "nextAction": "finalize",
            "progress": context.get("progress", ""),
            "reason": "已保留其他阶段的任务回执；须按当前全局进度重新汇总，不能据此跳过未完成阶段。",
        }
    all_tasks = get_stage_tasks_definitions(app_dir, stage)

    # finalize 与 advance 之间可能有任务被重置或补回，按当前回执再次核实门禁。
    for task in all_tasks:
        if task.get("isBackground"):
            continue
        state, _ = task_state(os.path.join(app_dir, task["receiptPath"]), task["taskId"],
                              run_data["runId"], {}, task.get("target"))
        if state != "succeeded":
            return {"advanced": False, "nextAction": "finalize", "taskId": task["taskId"],
                    "reason": "阶段报告生成后阻塞任务已有变动，请重新汇总当前回执。"}

    if stage in ("step1", "initial"):
        r_data = load_json(os.path.join(app_dir, ".build", "receipts", "step1-app-init.json")) or {}
        outputs = r_data.get("outputs", {})
        context["appId"] = outputs.get("appId")
        context["sectionIdByName"] = outputs.get("sectionIdByName", {})
        context["customPageIdByName"] = outputs.get("customPageIdByName", {})
        if plan.get("language"):
            context["language"] = plan["language"]

    elif stage in ("app_created", "step2a"):
        ws_id_by_name = context.get("worksheetIdByName", {})
        rel_layout_by_ws = context.get("relationLayoutByWorksheet", {})
        ws_fields_preview = context.get("worksheetFieldsPreview", {})
        rule_notes_by_sheet = {}
        field_options_ctx = list(context.get("fieldOptionsContext", []))
        existing_opt_ws = {item.get("name") for item in field_options_ctx if isinstance(item, dict)}

        for t in all_tasks:
            if t["step"] == "2a":
                r_data = load_json(os.path.join(app_dir, t["receiptPath"])) or {}
                outputs = r_data.get("outputs", {})
                ws_name = outputs.get("worksheetName") or t["target"].get("name")
                ws_id = outputs.get("worksheetId")
                if ws_name and outputs.get("businessRulesNotes"):
                    rule_notes_by_sheet[ws_name] = outputs["businessRulesNotes"]
                if ws_name and ws_id:
                    ws_id_by_name[ws_name] = ws_id
                if ws_name and isinstance(outputs.get("relationLayout"), list) and outputs["relationLayout"]:
                    rel_layout_by_ws[ws_name] = outputs["relationLayout"]
                if ws_name and isinstance(outputs.get("fields"), list):
                    ws_fields_preview[ws_name] = [
                        {"name": f.get("name"), "id": f.get("id"), "alias": f.get("alias"), "type": f.get("type")}
                        for f in outputs["fields"]
                        if isinstance(f, dict)
                    ]
                    opt_fields = [
                        {"name": f.get("name"), "alias": f.get("alias"), "options": f.get("options")}
                        for f in outputs["fields"]
                        if isinstance(f, dict) and f.get("options")
                    ]
                    if opt_fields and ws_name not in existing_opt_ws:
                        field_options_ctx.append({"name": ws_name, "fields": opt_fields})
                        existing_opt_ws.add(ws_name)
            elif t["step"] == "1b":
                if os.path.exists(os.path.join(app_dir, t["receiptPath"])):
                    context["appDescUpdated"] = True

        context["worksheetIdByName"] = ws_id_by_name
        context["businessRulesNotesByWorksheet"] = rule_notes_by_sheet
        context["relationLayoutByWorksheet"] = rel_layout_by_ws
        context["worksheetFieldsPreview"] = ws_fields_preview
        context["fieldOptionsContext"] = field_options_ctx

    elif stage in ("worksheets_created", "phase2_single_table"):
        view_id_by_name = context.get("viewIdByName", {})
        views_by_ws = context.get("viewsByWorksheet", {})
        action_id_by_name = context.get("actionIdByName", {})
        action_proc_by_key = context.get("actionProcessIdByKey", {})
        action_provenance = dict(context.get("actionProvenanceByKey", {}))
        chatbot_id_by_name = context.get("chatbotIdByName", {})

        for t in all_tasks:
            r_data = load_json(os.path.join(app_dir, t["receiptPath"])) or {}
            outputs = r_data.get("outputs", {})
            ws_name = outputs.get("worksheetName") or t["target"].get("name", "")
            if isinstance(outputs.get("viewIdByName"), dict):
                view_id_by_name.update(outputs["viewIdByName"])
            if ws_name and isinstance(outputs.get("views"), list):
                views_by_ws[ws_name] = outputs["views"]
                for v in outputs["views"]:
                    if isinstance(v, dict) and v.get("name") and v.get("id"):
                        view_id_by_name.setdefault(f"{ws_name}/{v['name']}", v["id"])
            if isinstance(outputs.get("actionIdByName"), dict):
                action_id_by_name.update(outputs["actionIdByName"])
            if isinstance(outputs.get("actionProcessIdByKey"), dict):
                action_proc_by_key.update({k: v for k, v in outputs["actionProcessIdByKey"].items() if v})
            if ws_name and isinstance(outputs.get("actions"), list):
                for act in outputs["actions"]:
                    if isinstance(act, dict) and act.get("name"):
                        a_name = act["name"]
                        if act.get("id"):
                            action_id_by_name.setdefault(f"{ws_name}/{a_name}", act["id"])
                        proc_id = act.get("processId") or act.get("workflowId")
                        if proc_id:
                            action_proc_by_key[f"{ws_name}::{a_name}"] = proc_id
                        if act.get("id") and isinstance(act.get("createdByBuild"), bool):
                            action_provenance[f"{ws_name}::{a_name}"] = {
                                k: act[k] for k in ("id", "createdByBuild", "disabledForWorkflowSetup", "initialEnabled") if k in act
                            }
            if isinstance(outputs.get("chatbotIdByName"), dict):
                chatbot_id_by_name.update(outputs["chatbotIdByName"])
            elif outputs.get("chatbotName") and outputs.get("chatbotId"):
                chatbot_id_by_name[outputs["chatbotName"]] = outputs["chatbotId"]
            if isinstance(outputs.get("chatbotContext"), list):
                for b in outputs["chatbotContext"]:
                    if isinstance(b, dict) and b.get("name") and b.get("id"):
                        chatbot_id_by_name[b["name"]] = b["id"]

        context["viewIdByName"] = view_id_by_name
        context["viewsByWorksheet"] = views_by_ws
        context["actionIdByName"] = action_id_by_name
        context["actionProcessIdByKey"] = action_proc_by_key
        context["actionProvenanceByKey"] = action_provenance
        context["chatbotIdByName"] = chatbot_id_by_name

    elif stage in ("fields_refreshed", "phase3_configs", "page_shells_created", "phase3"):
        role_id_by_name = context.get("roleIdByName", {})
        role_ctx = list(context.get("roleContext", []))
        seen_roles = {r.get("name") for r in role_ctx if isinstance(r, dict)}
        wf_designs = context.get("workflowDesigns", {})
        act_wf_designs = context.get("actionWorkflowDesigns", {})
        page_results = []

        for t in all_tasks:
            r_path = os.path.join(app_dir, t["receiptPath"])
            if not os.path.exists(r_path):
                continue
            r_data = load_json(r_path) or {}
            outputs = r_data.get("outputs", {})
            if isinstance(outputs.get("roleIdByName"), dict):
                role_id_by_name.update(outputs["roleIdByName"])
            if outputs.get("roleName") and outputs.get("roleId"):
                r_name = outputs["roleName"]
                r_id = outputs["roleId"]
                role_id_by_name[r_name] = r_id
                if r_name not in seen_roles:
                    role_ctx.append({"name": r_name, "id": r_id, "roleScope": outputs.get("roleScope", "general")})
                    seen_roles.add(r_name)
            if isinstance(outputs.get("workflowDesign"), dict):
                wd = outputs["workflowDesign"]
                if wd.get("name"):
                    wf_designs[wd["name"]] = wd
            if isinstance(outputs.get("actionWorkflowDesign"), dict):
                ad = outputs["actionWorkflowDesign"]
                ws_n = ad.get("worksheet") or ad.get("worksheetName", "")
                act_n = ad.get("name") or ad.get("actionName", "")
                if act_n:
                    act_wf_designs[f"{ws_n}::{act_n}"] = ad
            if t["step"] == "6":
                page_results.append({
                    "pageName": outputs.get("pageName") or t["target"].get("name"),
                    "completed": bool(outputs.get("completed", True)),
                    "notes": outputs.get("notes", []),
                })
            if t["step"] == "5" and r_data.get("status") == "succeeded":
                context["sampleDataCreated"] = True

        context["roleIdByName"] = role_id_by_name
        context["roleContext"] = role_ctx
        context["workflowDesigns"] = wf_designs
        context["actionWorkflowDesigns"] = act_wf_designs
        context["pageConfigurationResults"] = page_results

    elif stage in ("config_completed", "phase4_deploy"):
        workflows = plan.get("workflows", [])
        wf_map = {wf.get("name"): wf for wf in workflows if isinstance(wf, dict)}
        wf_results = []
        act_wf_results = []

        for t in all_tasks:
            r_data = load_json(os.path.join(app_dir, t["receiptPath"])) or {}
            outputs = r_data.get("outputs", {})
            if t["step"] == "10":
                wf_name = outputs.get("workflowName") or t["target"].get("name")
                proc_id = outputs.get("processId", "")
                st = workflow_publication_status(outputs)
                wf_results.append({
                    "name": wf_name,
                    "id": proc_id,
                    "status": st,
                    "description": outputs.get("description", ""),
                })
                if wf_name in wf_map and proc_id:
                    wf_map[wf_name]["processId"] = proc_id
                    if st in ("published", "draft"):
                        wf_map[wf_name]["published"] = (st == "published")
                    else:
                        wf_map[wf_name].pop("published", None)
            elif t["step"] == "11":
                ws_n = outputs.get("worksheetName", "")
                act_n = outputs.get("actionName", "")
                proc_id = outputs.get("processId") or t["target"].get("id", "")
                st = workflow_publication_status(outputs)
                action_result = {
                    "worksheet": ws_n,
                    "name": act_n,
                    "id": proc_id,
                    "status": st,
                    "description": outputs.get("description", ""),
                }
                if isinstance(outputs.get("actionEnabled"), bool):
                    action_result["actionEnabled"] = outputs["actionEnabled"]
                act_wf_results.append(action_result)

        # 终态顺带收口后台任务标记
        if is_task_succeeded(os.path.join(app_dir, ".build", "receipts", "step5-sample-data.json"),
                             "step5-sample-data", run_data["runId"]):
            context["sampleDataCreated"] = True
        if os.path.exists(os.path.join(app_dir, ".build", "receipts", "step1b-app-desc.json")):
            context["appDescUpdated"] = True

        plan["workflows"] = list(wf_map.values())
        context["workflowResults"] = wf_results
        context["customActionWorkflowResults"] = act_wf_results
        save_json(plan_path, plan)

    context["progress"] = next_progress
    context["buildRun"] = {
        "runId": report.get("runId", ""),
        "executionMode": "subagent_required",
        "lastPhaseReport": ".build/phase-report.json",
        "blocked": False,
    }
    save_json(context_path, context)

    return {
        "advanced": True,
        "stage": stage,
        "newProgress": next_progress,
        "contextPath": context_path,
    }


def main():
    parser = argparse.ArgumentParser(description="HAP App Copilot 报告驱动型薄运行时引擎")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init", help="初始化 .build 运行目录与执行策略")
    p_init.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")
    p_init.add_argument("--skill-dir", type=str, default="", help="Skill 根目录")
    p_init.add_argument("--mcp-server", type=str, required=True, help="入口已选定的 MCP 服务名")

    p_prep = subparsers.add_parser("prepare", help="准备任务上下文与原始规则、计划入口")
    p_prep.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")
    p_prep.add_argument("--progress", type=str, default="", help="准备指定阶段候选任务，不改变全局进度；执行前核实实际依赖")
    p_prep.add_argument("--include-pending-capacity", action="store_true", default=True, help="兼容旧调用；默认已包含容量等待任务")

    p_disp = subparsers.add_parser("dispatched", help="记录已成功派发任务")
    p_disp.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")
    p_disp.add_argument("--task-id", type=str, required=True, help="任务 ID")
    p_disp.add_argument("--agent-id", type=str, required=True, help="Subagent 实例 ID")

    p_cap = subparsers.add_parser("capacity-wait", help="标记任务进入容量等待")
    p_cap.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")
    p_cap.add_argument("--task-id", type=str, required=True, help="任务 ID")

    p_df = subparsers.add_parser("dispatch-failed", help="记录任务派发失败")
    p_df.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")
    p_df.add_argument("--task-id", type=str, required=True, help="任务 ID")
    p_df.add_argument("--reason-code", type=str, default="SUBAGENT_TOOL_ERROR", help="失败原因码")

    p_rst = subparsers.add_parser("reset-task", help="归档异常回执并解除单任务阻塞以便重新派发")
    p_rst.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")
    p_rst.add_argument("--task-id", type=str, required=True, help="任务 ID")

    p_rsv = subparsers.add_parser("resolve-task", help="线上返工修复核实后将失败/阻塞任务正式归并为 succeeded 回执")
    p_rsv.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")
    p_rsv.add_argument("--task-id", type=str, required=True, help="任务 ID")
    p_rsv.add_argument("--evidence", type=str, required=True, help="线上核验通过的具体事实依据")
    p_rsv.add_argument("--outputs-json", type=str, default="", help="可选：补充或覆盖写入 outputs 的 JSON 对象字符串")

    p_val = subparsers.add_parser("validate-plan", help="构建前静态预检 hap-plan.json 结构闭环与自定义动作人工输入入口")
    p_val.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")

    p_ref = subparsers.add_parser("refresh", help="刷新任务状态与进度摘要")
    p_ref.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")

    p_fin = subparsers.add_parser("finalize", help="汇总校验回执并生成阶段报告")
    p_fin.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")
    p_fin.add_argument("--progress", type=str, default="", help="可选显式指定 progress")

    p_adv = subparsers.add_parser("advance", help="在报告放行后原子推进状态机")
    p_adv.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")

    p_stat = subparsers.add_parser("status", help="查看当前阶段状态")
    p_stat.add_argument("--app-dir", type=str, required=True, help="应用项目根目录")

    args = parser.parse_args()

    if args.command == "init":
        skill_dir = args.skill_dir if args.skill_dir else get_skill_root()
        res = cmd_init(args.app_dir, skill_dir, args.mcp_server)
    elif args.command == "prepare":
        res = cmd_prepare(args.app_dir, args.progress if args.progress else None, args.include_pending_capacity)
    elif args.command == "dispatched":
        res = cmd_record_dispatch(args.app_dir, args.task_id, args.agent_id, "running")
    elif args.command == "capacity-wait":
        res = cmd_record_dispatch(args.app_dir, args.task_id, "", "pending_capacity")
    elif args.command == "dispatch-failed":
        res = cmd_record_dispatch(args.app_dir, args.task_id, "", "failed", args.reason_code)
    elif args.command == "reset-task":
        res = cmd_reset_task(args.app_dir, args.task_id)
    elif args.command == "resolve-task":
        res = cmd_resolve_task(args.app_dir, args.task_id, args.evidence, args.outputs_json)
    elif args.command == "validate-plan":
        res = cmd_validate_plan(args.app_dir)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res["passed"] else 1)
    elif args.command == "refresh":
        res = cmd_refresh(args.app_dir)
    elif args.command == "finalize":
        res = cmd_finalize(args.app_dir, args.progress if args.progress else None)
    elif args.command == "advance":
        res = cmd_advance(args.app_dir)
    elif args.command == "status":
        res = cmd_refresh(args.app_dir)
    else:
        res = {"error": f"Unknown command: {args.command}"}

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        sys.exit(2)
