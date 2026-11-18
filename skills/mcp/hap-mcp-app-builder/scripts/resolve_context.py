#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resolve_context.py
HAP App Copilot 渐进加载上下文动态解析与章节级点读引擎。

支持能力：
1. --mode {plan,build,modify,data} --assets/--domains ... [--render]：
   按当前场景与目标领域计算最小参考清单，或直接渲染裁剪后的 Modify 上下文包；
2. --file <rel_path> [--section <关键词> | --list-sections]：
   对大体积设计指南或领域 Spec 执行二级章节精准点读（对齐线上 load_skill(skillName, section)）；
3. --validate：
   自检全库所有模式、构建步骤与领域资产映射文件的物理存在性。
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set

# modify/modify_guide.md 章节映射（支持多项映射，如 chart 同时关联页面图表与工作表统计图）
MODIFY_GUIDE_SECTION_MAPPING: Dict[str, List[str]] = {
    "app": ["第 2 章"],
    "navigation": ["第 2 章"],
    "app_nav": ["第 2 章"],
    "app_navigation": ["第 2 章"],
    "worksheet": ["第 3 章"],
    "field": ["第 3 章"],
    "relation": ["第 3 章"],
    "layout": ["第 3 章"],
    "rule": ["第 3 章"],
    "business_rule": ["第 3 章"],
    "index": ["第 3 章"],
    "worksheet_index": ["第 3 章"],
    "worksheet_filter": ["第 3 章"],
    "custom_field": ["第 3 章"],
    "free_field": ["第 3 章"],
    "view": ["第 4 章"],
    "action": ["第 4 章"],
    "view_action": ["第 4 章"],
    "role": ["第 5 章"],
    "permission": ["第 5 章"],
    "role_permission": ["第 5 章"],
    "page": ["第 6 章"],
    "custom_page": ["第 6 章"],
    "worksheet_chart": ["第 7 章"],
    "page_chart": ["第 6 章", "第 7 章"],
    "chart": ["第 6 章", "第 7 章"],
    "chatbot": ["第 8 章"],
    "print_template": ["第 9 章"],
    "template": ["第 9 章"],
    "public_form": ["第 10 章"],
    "external_portal": ["第 11 章"],
    "portal": ["第 11 章"],
    "workflow": ["第 12 章"],
    "workflow_design": ["第 12 章"],
    "record": ["第 13 章"],
    "data": ["第 13 章"],
    "record_data": ["第 13 章"],
    "sample_data": ["第 13 章"],
}

MODIFY_GUIDE_SECTION_ORDER: List[str] = [
    "第 1 章",
    "第 2 章",
    "第 3 章",
    "第 4 章",
    "第 5 章",
    "第 6 章",
    "第 7 章",
    "第 8 章",
    "第 9 章",
    "第 10 章",
    "第 11 章",
    "第 12 章",
    "第 13 章",
]

# modify/impact-map.md 二级章节关键词映射
IMPACT_MAP_SECTION_MAPPING: Dict[str, List[str]] = {
    "app": ["应用与导航"],
    "navigation": ["应用与导航"],
    "app_nav": ["应用与导航"],
    "app_navigation": ["应用与导航"],
    "public_form": ["应用与导航"],
    "external_portal": ["应用与导航"],
    "portal": ["应用与导航"],
    "worksheet": ["工作表、字段、业务规则与索引"],
    "field": ["工作表、字段、业务规则与索引"],
    "relation": ["工作表、字段、业务规则与索引"],
    "layout": ["工作表、字段、业务规则与索引"],
    "rule": ["工作表、字段、业务规则与索引"],
    "business_rule": ["工作表、字段、业务规则与索引"],
    "index": ["工作表、字段、业务规则与索引"],
    "worksheet_index": ["工作表、字段、业务规则与索引"],
    "worksheet_filter": ["工作表、字段、业务规则与索引"],
    "custom_field": ["工作表、字段、业务规则与索引"],
    "free_field": ["工作表、字段、业务规则与索引"],
    "view": ["视图与自定义动作"],
    "action": ["视图与自定义动作"],
    "view_action": ["视图与自定义动作"],
    "page": ["自定义页面与统计图表"],
    "custom_page": ["自定义页面与统计图表"],
    "page_chart": ["自定义页面与统计图表"],
    "chart": ["自定义页面与统计图表"],
    "worksheet_chart": ["自定义页面与统计图表"],
    "chatbot": ["AI 助手、打印模板、角色与工作流/数据"],
    "print_template": ["AI 助手、打印模板、角色与工作流/数据"],
    "template": ["AI 助手、打印模板、角色与工作流/数据"],
    "role": ["AI 助手、打印模板、角色与工作流/数据"],
    "permission": ["AI 助手、打印模板、角色与工作流/数据"],
    "role_permission": ["AI 助手、打印模板、角色与工作流/数据"],
    "workflow": ["AI 助手、打印模板、角色与工作流/数据"],
    "workflow_design": ["AI 助手、打印模板、角色与工作流/数据"],
    "record": ["AI 助手、打印模板、角色与工作流/数据"],
    "data": ["AI 助手、打印模板、角色与工作流/数据"],
    "record_data": ["AI 助手、打印模板、角色与工作流/数据"],
    "sample_data": ["AI 助手、打印模板、角色与工作流/数据"],
}

MODIFY_COMPLEX_SCENARIOS: Set[str] = {
    "physical_delete",
    "published_workflow",
    "fixed_value_mapping",
    "bulk_data_update",
    "complex_conversion",
    "cross_table_migration",
    "dependency_governance",
}

MODIFY_DATA_SCENARIOS: Set[str] = {
    "fixed_value_mapping",
    "bulk_data_update",
    "complex_conversion",
    "cross_table_migration",
    "dependency_governance",
}

SCENARIO_POLICY_DOMAINS = {s: "record_data" for s in MODIFY_DATA_SCENARIOS}
SCENARIO_POLICY_DOMAINS.update({"published_workflow": "workflow", "physical_delete": "worksheet"})

# 复用操作卡的别名映射；这里只定义切片归属，不复制任何规则正文。
POLICY_DOMAIN_BY_GUIDE_SECTION = dict(zip(MODIFY_GUIDE_SECTION_ORDER[1:], [
    "app_navigation", "worksheet", "view_action", "role_permission",
    "custom_page", "worksheet_chart", "chatbot", "print_template",
    "public_form", "external_portal", "workflow", "record_data",
]))

DELETE_ROW_DOMAINS = {
    "工作表已保存筛选器": {"worksheet"},
    "常规及本表计算字段": {"worksheet"},
    "普通视图": {"view_action"},
    "打印模板": {"print_template"},
    "自定义页面": {"custom_page"},
    "统计图表": {"custom_page", "worksheet_chart"},
    "AI 智能助手": {"chatbot"},
    "表单业务规则": {"worksheet"},
    "自定义动作": {"view_action"},
    "指定工作流": {"workflow", "view_action", "chatbot"},
    "物理索引": {"worksheet"},
    "空角色": {"role_permission"},
    "导航分组": {"app_navigation"},
    "空工作表": {"worksheet"},
}

BOUNDARY_ROW_DOMAINS = {
    "自定义页面背景": {"custom_page"},
    "自定义页面内容与外链": {"custom_page"},
    "统计图表": {"custom_page", "worksheet_chart"},
    "自定义动作": {"view_action", "workflow"},
    "AI 智能助手": {"chatbot"},
    "打印模板": {"print_template"},
    "公开表单与外部门户": {"public_form", "external_portal"},
    "角色合并": {"role_permission"},
    "记录数据处理": {"record_data"},
}

IMPACT_MIXED_ROW_DOMAINS = {
    "修改应用名称、说明、图标或颜色": {"app_navigation"},
    "修改单个或多个应用项导航名称/图标/显示模式/备注/用户说明": {"app_navigation"},
    "新建、重命名或调整导航分组": {"app_navigation"},
    "删除导航分组": {"app_navigation"},
    "调整导航项顺序": {"app_navigation"},
    "移动或隐藏入口": {"app_navigation"},
    "原生公开表单启停与配置": {"public_form"},
    "门户名称、登录页外观、协议及通知模板": {"external_portal"},
    "启用并交付可用外部门户": {"external_portal"},
    "门户启停、注册登录、讨论及资料控制": {"external_portal"},
    "新建或修改 AI 助手": {"chatbot"},
    "新建、修改或删除打印模板": {"print_template"},
    "新建、修改、排序、删除或合并角色": {"role_permission"},
    "新建、修改、发布、关闭或删除工作流": {"workflow"},
    "结构修订连带记录数据与示例写入": {"record_data"},
}


def get_skill_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_files(
    mode: str,
    assets: List[str],
    scenarios: List[str] = None,
    step: str = None,
) -> List[str]:
    files: Set[str] = {"HOST_ADAPTER.md"}
    scenarios = scenarios or []

    if mode == "plan":
        files.update([
            "workflows/plan.md",
            "plan/1a_plan_overview.md",
            "plan/1b_plan_schema.md",
            "references/hap-app-design-guide.md",
            "references/hap-workflow-design-guide.md",
            "references/hap-domain-app-spec.md",
            "references/hap-icon-palette.md",
        ])
    elif mode == "build":
        files.update([
            "workflows/build.md",
            "build/CONTEXT.md",
            "build/PROGRESS.md",
            "build/OUTPUT_CONTRACT.md",
            "scripts/build_runtime.py",
            "scripts/merge_worksheet_context.py",
        ])
    elif mode == "modify":
        files.update([
            "workflows/modify.md",
            "modify/impact-map.md",
            "modify/safety-rules.md",
            "modify/execution-boundaries.md",
            "modify/modify_guide.md",
        ])
    elif mode == "data":
        files.update([
            "workflows/data.md",
        ])

    step_mapping: Dict[str, List[str]] = {
        "1": ["build/steps/1_create_app.md", "references/hap-domain-app-spec.md", "references/hap-icon-palette.md"],
        "1b": ["build/steps/1b_update_app_desc.md", "references/hap-domain-app-spec.md"],
        "2a": ["build/steps/2a_create_worksheets.md", "references/hap-domain-worksheet-spec.md", "references/hap-domain-custom-field-spec.md"],
        "2b": ["build/steps/2b_create_relations.md", "references/hap-domain-worksheet-spec.md"],
        "3": [
            "build/steps/3_create_actions_views_rules.md",
            "references/hap-domain-view-spec.md",
            "references/hap-domain-custom-action-spec.md",
            "references/hap-domain-business-rule-spec.md",
        ],
        "4": ["build/steps/4_create_chatbots.md", "references/hap-domain-chatbot-spec.md"],
        "4a": ["build/steps/4_create_chatbots.md", "references/hap-domain-chatbot-spec.md"],
        "4b": ["build/steps/4_create_chatbots.md", "references/hap-domain-chatbot-spec.md"],
        "5": ["build/steps/5_create_sample_data.md", "references/hap-sample-data-spec.md"],
        "6": [
            "build/steps/6_create_pages.md",
            "references/hap-domain-custom-page-spec.md",
            "references/hap-chart-design-guide.md",
            "references/hap-icon-palette.md",
        ],
        "7": ["build/steps/7_sort_app_items.md", "references/hap-domain-app-spec.md"],
        "8": ["build/steps/8_create_roles.md", "references/hap-domain-role-spec.md", "references/hap-app-design-guide.md"],
        "10": [
            "build/steps/10_create_workflows.md",
            "references/hap-workflow-design-guide.md",
            "references/hap-domain-workflow-spec.md",
        ],
        "11": [
            "build/steps/11_create_action_workflows.md",
            "references/hap-workflow-design-guide.md",
            "references/hap-domain-workflow-spec.md",
        ],
    }

    if step:
        if mode != "build" or step not in step_mapping:
            raise ValueError("--step 仅接受 Build 步骤：" + ", ".join(step_mapping))
        files.update(step_mapping[step])

    asset_mapping: Dict[str, List[str]] = {
        "app": ["references/hap-domain-app-spec.md", "references/hap-icon-palette.md"],
        "navigation": ["references/hap-domain-app-spec.md", "references/hap-icon-palette.md"],
        "app_nav": ["references/hap-domain-app-spec.md", "references/hap-icon-palette.md"],
        "app_navigation": ["references/hap-domain-app-spec.md", "references/hap-icon-palette.md"],
        "worksheet": ["references/hap-domain-worksheet-spec.md"],
        "field": ["references/hap-domain-worksheet-spec.md"],
        "relation": ["references/hap-domain-worksheet-spec.md"],
        "layout": ["references/hap-domain-worksheet-spec.md"],
        "worksheet_filter": ["references/hap-domain-worksheet-spec.md"],
        "custom_field": ["references/hap-domain-custom-field-spec.md"],
        "free_field": ["references/hap-domain-custom-field-spec.md"],
        "index": ["references/hap-domain-worksheet-index-spec.md"],
        "worksheet_index": ["references/hap-domain-worksheet-index-spec.md"],
        "rule": ["references/hap-domain-business-rule-spec.md"],
        "business_rule": ["references/hap-domain-business-rule-spec.md"],
        "view": ["references/hap-domain-view-spec.md"],
        "action": ["references/hap-domain-custom-action-spec.md"],
        "view_action": ["references/hap-domain-view-spec.md", "references/hap-domain-custom-action-spec.md"],
        "role": ["references/hap-domain-role-spec.md"],
        "permission": ["references/hap-domain-role-spec.md"],
        "role_permission": ["references/hap-domain-role-spec.md"],
        "page": ["references/hap-domain-custom-page-spec.md", "references/hap-chart-design-guide.md"],
        "custom_page": ["references/hap-domain-custom-page-spec.md", "references/hap-chart-design-guide.md"],
        "worksheet_chart": ["references/hap-domain-worksheet-chart-spec.md", "references/hap-chart-design-guide.md"],
        "page_chart": [
            "references/hap-domain-custom-page-spec.md",
            "references/hap-domain-worksheet-chart-spec.md",
            "references/hap-chart-design-guide.md",
        ],
        "chart": [
            "references/hap-domain-custom-page-spec.md",
            "references/hap-domain-worksheet-chart-spec.md",
            "references/hap-chart-design-guide.md",
        ],
        "chatbot": ["references/hap-domain-chatbot-spec.md"],
        "print_template": ["modify/print-template-file.md"],
        "template": ["modify/print-template-file.md"],
        "public_form": ["references/hap-domain-worksheet-spec.md"],
        "external_portal": ["references/hap-domain-external-portal-spec.md"],
        "portal": ["references/hap-domain-external-portal-spec.md"],
        "workflow": ["references/hap-domain-workflow-spec.md", "references/hap-workflow-design-guide.md"],
        "workflow_design": ["references/hap-workflow-design-guide.md"],
        "record": ["references/hap-domain-record-data-spec.md"],
        "data": ["references/hap-domain-record-data-spec.md"],
        "record_data": ["references/hap-domain-record-data-spec.md", "references/hap-sample-data-spec.md"],
        "sample_data": ["references/hap-sample-data-spec.md"],
        "icon": ["references/hap-icon-palette.md"],
        "style": ["references/hap-domain-app-spec.md", "references/hap-icon-palette.md"],
        "design": ["references/hap-app-design-guide.md"],
    }

    for a in assets:
        key = a.strip().lower()
        if key not in asset_mapping:
            raise ValueError(f"未知领域：{a}；可选值：" + ", ".join(sorted(asset_mapping)))
        files.update(asset_mapping[key])

    if mode == "modify":
        for scenario in scenarios:
            domain = SCENARIO_POLICY_DOMAINS.get(scenario.strip().lower())
            if domain:
                files.update(asset_mapping[domain])

    return sorted(list(files))


def validate_all_mappings() -> bool:
    skill_root = get_skill_root()
    all_files: Set[str] = set()
    for m in ["plan", "build", "modify", "data"]:
        all_files.update(resolve_files(m, []))
    for s in ["1", "1b", "2a", "2b", "3", "4a", "4b", "5", "6", "7", "8", "10", "11"]:
        all_files.update(resolve_files("build", [], step=s))
    all_assets = list(MODIFY_GUIDE_SECTION_MAPPING.keys()) + ["icon", "style", "design"]
    for a in all_assets:
        all_files.update(resolve_files("modify", [a]))
    for scenario in sorted(MODIFY_COMPLEX_SCENARIOS):
        all_files.update(resolve_files("modify", [], scenarios=[scenario]))

    missing = []
    for rel_path in sorted(list(all_files)):
        abs_path = os.path.join(skill_root, rel_path)
        if not os.path.exists(abs_path):
            missing.append(rel_path)

    if missing:
        print(f"❌ 发现 {len(missing)} 个缺失的映射文件：", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return False
    # 不只核对路径：检查每个领域实际能命中对应操作卡和影响章节。
    def read(rel_path: str) -> str:
        with open(os.path.join(skill_root, rel_path), encoding="utf-8") as file_obj:
            return file_obj.read()

    guide = read("modify/modify_guide.md")
    impact = read("modify/impact-map.md")
    errors = []
    guide_sections = {f"第 {number} 章" for number in re.findall(r"^##\s+([0-9]+)\.", guide, re.MULTILINE)}
    for asset, sections in MODIFY_GUIDE_SECTION_MAPPING.items():
        for section in sections:
            if section not in guide_sections:
                errors.append(f"{asset} 未命中操作卡 {section}")
    for asset, sections in IMPACT_MAP_SECTION_MAPPING.items():
        for section in sections:
            try:
                extract_markdown_section_by_keyword(impact, section)
            except ValueError:
                errors.append(f"{asset} 未命中影响章节 {section}")
    try:
        validate_policy_row_mappings(read("modify/safety-rules.md"),
                                     read("modify/execution-boundaries.md"), impact)
        for asset in all_assets:
            render_modify_policy_bundle(resolve_files("modify", [asset]), [asset], [])
    except ValueError as exc:
        errors.append(str(exc))
    if errors:
        print("❌ 章节映射无效：\n" + "\n".join(errors), file=sys.stderr)
        return False
    print(f"✅ 所有映射文件（共 {len(all_files)} 个）均真实存在且路径有效！")
    print("✅ 领域操作卡、公共规则与表格行切片均能实际加载。")
    return True


def reference_sections(rel_path: str, assets: List[str], scenarios: List[str]) -> List[str]:
    if rel_path == "modify/modify_guide.md":
        domains = policy_domains(assets, scenarios)
        if domains is None:
            return list(MODIFY_GUIDE_SECTION_ORDER)
        sections = {"第 1 章"}
        for asset in domains:
            for sec in MODIFY_GUIDE_SECTION_MAPPING.get(asset.strip().lower(), []):
                sections.add(sec)
        if {s.strip().lower() for s in scenarios}.intersection(MODIFY_DATA_SCENARIOS):
            sections.add("第 13 章")
        return [s for s in MODIFY_GUIDE_SECTION_ORDER if s in sections]
    if rel_path == "modify/print-template-file.md":
        return ["仅文件制作或替换时读取；纯配置和删除跳过"]
    if rel_path.startswith("references/"):
        return ["使用 --file <path> --section <关键词> 按需点读"]
    return ["已裁剪渲染"]


def reference_purpose(rel_path: str) -> str:
    if rel_path == "workflows/modify.md":
        return "Modify 内联执行流程与沟通红线"
    if rel_path == "workflows/data.md":
        return "Data 日常业务数据查询、增删改、审批处理与流程触发规范"
    if rel_path == "modify/impact-map.md":
        return "跨领域连带分类与固定依赖顺序"
    if rel_path == "modify/modify_guide.md":
        return "12 领域增量读写规则与精确工具集"
    if rel_path == "modify/safety-rules.md":
        return "二元风险、14 类删除直通与数据阈值底线"
    if rel_path == "modify/execution-boundaries.md":
        return "平台能力边界与跨应用数据源引用规则"
    if rel_path == "modify/print-template-file.md":
        return "本地文件制作步骤、HAP 专用语法与交付检查"
    if rel_path.endswith("-guide.md"):
        return "业务建模与设计指南"
    if rel_path.startswith("references/hap-domain-"):
        return "领域对象底层参数与合法结构规范"
    return "任务所需参考规范"


def build_reference_records(
    resolved_rel_paths: List[str],
    assets: List[str],
    scenarios: List[str],
    absolute: bool = False,
) -> List[Dict[str, object]]:
    skill_root = get_skill_root()
    records = []
    for rel_path in resolved_rel_paths:
        output_path = os.path.join(skill_root, rel_path) if absolute else rel_path
        records.append({
            "path": output_path,
            "sections": reference_sections(rel_path, assets, scenarios),
            "purpose": reference_purpose(rel_path),
        })
    return records


def full_source_fallback(content: str, reason: str) -> str:
    """运行时切片不适用时保留原文；维护侧 --validate 仍单独检查映射。"""
    print(f"提示：{reason}，已回退加载完整原文。", file=sys.stderr)
    return content.rstrip()


def extract_guide_sections(content: str, requested_sections: List[str]) -> str:
    """从 modify_guide.md 提取指定的编号二级章节。"""
    lines = content.splitlines(keepends=True)
    heading_indexes = []
    for index, line in enumerate(lines):
        match = re.match(r"^##\s+([0-9]+)\.", line)
        if match:
            heading_indexes.append((index, f"第 {match.group(1)} 章"))

    requested_keys = set(requested_sections)
    if not heading_indexes or requested_keys - {key for _, key in heading_indexes}:
        return full_source_fallback(content, "领域指南章节与截取映射不匹配")
    selected = []
    for position, (start, key) in enumerate(heading_indexes):
        if key not in requested_keys:
            continue
        end = heading_indexes[position + 1][0] if position + 1 < len(heading_indexes) else len(lines)
        selected.extend(lines[start:end])
    return "".join(selected).rstrip()


def extract_impact_map_sections(content: str, assets: List[str], scenarios: List[str]) -> str:
    """从 impact-map.md 提取公共原则、命中领域的连带表格及固定顺序速查。"""
    domains = policy_domains(assets, scenarios)
    if domains is None:
        return content.rstrip()
    lines = content.splitlines(keepends=True)
    h2_spans = []
    for idx, line in enumerate(lines):
        if re.match(r"^##\s+", line):
            h2_spans.append((idx, line.strip()))

    needed_keywords = {"统一分类与交互原则", "跨领域固定依赖顺序速查"}
    for a in domains:
        for kw in IMPACT_MAP_SECTION_MAPPING.get(a.strip().lower(), []):
            needed_keywords.add(kw)
    if {s.strip().lower() for s in scenarios}.intersection(MODIFY_DATA_SCENARIOS):
        needed_keywords.add("AI 助手、打印模板、角色与工作流/数据")

    if any(not any(kw in title for _, title in h2_spans) for kw in needed_keywords):
        return full_source_fallback(content, "影响地图章节与截取映射不匹配")
    selected = []
    for pos, (start, title) in enumerate(h2_spans):
        end = h2_spans[pos + 1][0] if pos + 1 < len(h2_spans) else len(lines)
        if any(kw in title for kw in needed_keywords):
            block = "".join(lines[start:end])
            if "应用与导航" in title or "AI 助手、打印模板、角色与工作流/数据" in title:
                # 同一二级章节可能含多个领域，进一步保留命中的原始表格行。
                chunks = re.split(r"(?=^### )", block, flags=re.MULTILINE)
                for index, chunk in enumerate(chunks):
                    filtered, count = filter_policy_tables(chunk, IMPACT_MIXED_ROW_DOMAINS, domains)
                    if index == 0 or count:
                        selected.append(filtered)
            else:
                selected.append(block)
    return "".join(selected).rstrip()


def policy_domains(assets: List[str], scenarios: List[str]):
    """未指定领域或仅有设计/风格等宽泛标签时完整加载，不猜测操作范围。"""
    if not assets or any(a.strip().lower() not in MODIFY_GUIDE_SECTION_MAPPING for a in assets):
        return None
    domains = {POLICY_DOMAIN_BY_GUIDE_SECTION[section]
               for asset in assets
               for section in MODIFY_GUIDE_SECTION_MAPPING[asset.strip().lower()]}
    domains.update(SCENARIO_POLICY_DOMAINS[s.strip().lower()] for s in scenarios
                   if s.strip().lower() in SCENARIO_POLICY_DOMAINS)
    return domains


def policy_row_key(line: str) -> str:
    cell = line.split("|", 2)[1].strip().strip("*")
    return re.sub(r"^\d+\.\s*", "", cell)


def policy_table_keys(content: str) -> Set[str]:
    return {policy_row_key(line) for line in content.splitlines()
            if line.startswith("|") and not is_policy_table_header(line)}


def is_policy_table_header(line: str) -> bool:
    key = policy_row_key(line)
    return key in {"对象类别", "领域能力", "变化"} or bool(re.fullmatch(r":?-+:?", key))


def filter_policy_tables(content: str, row_domains: Dict[str, Set[str]], domains: Set[str]):
    """只按第一列选择整行；出现未映射条目时保留整张原表。"""
    lines = content.splitlines(keepends=True)
    output = []
    count = index = 0
    while index < len(lines):
        if not lines[index].startswith("|"):
            output.append(lines[index])
            index += 1
            continue
        table = []
        while index < len(lines) and lines[index].startswith("|"):
            table.append(lines[index])
            index += 1
        unknown = [policy_row_key(line) for line in table
                   if not is_policy_table_header(line) and policy_row_key(line) not in row_domains]
        if unknown:
            print(f"提示：规则表格有未映射条目 {', '.join(unknown)}，已保留整张原表。", file=sys.stderr)
            output.extend(table)
            count += sum(not is_policy_table_header(line) for line in table)
            continue
        selected = []
        for line in table:
            if is_policy_table_header(line):
                continue
            key = policy_row_key(line)
            if row_domains[key].intersection(domains):
                selected.append(line)
        if selected:
            output.extend(line for line in table if is_policy_table_header(line) or line in selected)
            count += len(selected)
    return "".join(output), count


def extract_policy_sections(content: str, domains, kind: str) -> str:
    if domains is None:
        return content.rstrip()
    headings = list(re.finditer(r"^## .+$", content, flags=re.MULTILINE))
    if not headings:
        return full_source_fallback(content, f"{kind} 缺少可截取的二级标题")
    selected = [content[:headings[0].start()]]
    for index, heading in enumerate(headings):
        title = heading.group()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        block = content[heading.start():end]
        if kind == "safety" and "记录数据修订硬约束" in title and "record_data" not in domains:
            continue
        if kind == "safety" and "删除与关闭轻量直通条件" in title:
            block, _ = filter_policy_tables(block, DELETE_ROW_DOMAINS, domains)
        elif kind == "boundary" and "核心领域能力边界矩阵" in title:
            block, _ = filter_policy_tables(block, BOUNDARY_ROW_DOMAINS, domains)
        selected.append(block)
    return "".join(selected).rstrip()


def validate_policy_row_mappings(safety: str, boundary: str, impact: str) -> None:
    for content, query, mapping in [
        (safety, "删除与关闭轻量直通条件", DELETE_ROW_DOMAINS),
        (boundary, "核心领域能力边界矩阵", BOUNDARY_ROW_DOMAINS),
        (impact, "应用与导航,AI 助手、打印模板、角色与工作流/数据", IMPACT_MIXED_ROW_DOMAINS),
    ]:
        actual = policy_table_keys(extract_markdown_section_by_keyword(content, query))
        if actual != set(mapping):
            raise ValueError(f"{query} 的表格行映射不完整：新增={sorted(actual - set(mapping))}，缺失={sorted(set(mapping) - actual)}")


def extract_markdown_section_by_keyword(content: str, section_query: str = "", list_only: bool = False) -> str:
    """通用二级章节目录展示与按标题关键词点读（对齐线上 load_skill(skillName, section)）。"""
    lines = content.splitlines(keepends=True)
    h2_spans = []
    for idx, line in enumerate(lines):
        if re.match(r"^##\s+", line):
            h2_spans.append((idx, line.strip()))

    if list_only or not section_query:
        toc = [title for _, title in h2_spans]
        return "可用二级章节列表：\n" + "\n".join(f"- {t}" for t in toc) + "\n"

    queries = [q.strip().lower() for q in section_query.split(",") if q.strip()]
    header = lines[: h2_spans[0][0]] if h2_spans else lines
    matched = []
    found_queries = set()
    for pos, (start, title) in enumerate(h2_spans):
        end = h2_spans[pos + 1][0] if pos + 1 < len(h2_spans) else len(lines)
        title_lower = title.lower()
        hits = {q for q in queries if q in title_lower}
        if hits:
            found_queries.update(hits)
            matched.extend(lines[start:end])

    if not matched or set(queries) - found_queries:
        toc = "\n".join(f"- {t}" for _, t in h2_spans)
        missing = ", ".join(sorted(set(queries) - found_queries)) or section_query
        raise ValueError(f"未找到二级章节：{missing}。当前文件可用章节如下：\n{toc}")

    return "".join(header + matched).rstrip() + "\n"


def render_modify_policy_bundle(
    resolved_rel_paths: List[str],
    assets: List[str],
    scenarios: List[str],
    absolute: bool = False,
) -> str:
    skill_root = get_skill_root()
    spec_paths = [p for p in resolved_rel_paths if p.startswith("references/")]
    references = build_reference_records(spec_paths, assets, scenarios, absolute=absolute)
    step_paths = [p for p in resolved_rel_paths if p == "modify/print-template-file.md"]
    metadata = {
        "mode": "modify",
        "assets": assets,
        "scenarios": scenarios,
        "specReferences": references,
        "stepReferences": build_reference_records(step_paths, assets, scenarios, absolute=absolute),
        "note": "公共底线必读，领域专属规则按原文截取；未指定领域时完整加载。新增领域或记录操作须先补充领域/场景重新加载。底层 references/hap-*.md 仅在构造复杂参数时用 --file <path> --section <关键词> 按需点读。",
    }
    parts = [
        "# Modify 最小上下文规则包",
        "",
        "## 按需底层规格清单",
        "",
        "```json",
        json.dumps(metadata, ensure_ascii=False, indent=2),
        "```",
    ]

    render_plan = [
        ("modify/safety-rules.md", "safety"),
        ("modify/execution-boundaries.md", "boundary"),
        ("modify/impact-map.md", "impact"),
        ("modify/modify_guide.md", "guide"),
    ]
    for rel_path, mode_tag in render_plan:
        abs_fp = os.path.join(skill_root, rel_path)
        if not os.path.exists(abs_fp):
            raise ValueError(f"必读规则文件不存在：{rel_path}")
        with open(abs_fp, "r", encoding="utf-8") as file_obj:
            content = file_obj.read()
        if mode_tag in {"safety", "boundary"}:
            content = extract_policy_sections(content, policy_domains(assets, scenarios), mode_tag)
        elif mode_tag == "impact":
            content = extract_impact_map_sections(content, assets, scenarios)
        elif mode_tag == "guide":
            content = extract_guide_sections(content, reference_sections(rel_path, assets, scenarios))
        parts.extend([
            "",
            f"## 已加载：{rel_path}",
            "",
            content.rstrip(),
        ])
    return "\n".join(parts).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="HAP App Copilot 上下文渐进加载与章节级点读引擎")
    parser.add_argument("--mode", choices=["plan", "build", "modify", "data"], default="modify", help="工作流模式")
    parser.add_argument("--assets", type=str, default="", help="目标资产/领域列表，逗号分隔 (如 worksheet,public_form,role_permission)")
    parser.add_argument("--domains", type=str, default="", help="--assets 的同义别名，逗号分隔")
    parser.add_argument("--scenarios", type=str, default="", help="可选复杂场景列表，逗号分隔")
    parser.add_argument("--step", type=str, default="", help="Build 步骤编号 (如 2a, 3, 4b, 10)")
    parser.add_argument("--file", type=str, default="", help="指定单个参考文件相对路径进行二级章节检索 (如 references/hap-app-design-guide.md)")
    parser.add_argument("--section", type=str, default="", help="配合 --file 按关键词点读二级章节正文 (逗号分隔可多选)")
    parser.add_argument("--list-sections", action="store_true", help="配合 --file 仅列出该文件的二级章节目录")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出文件清单")
    parser.add_argument("--render", action="store_true", help="渲染输出裁剪后的 Modify 最小规则包")
    parser.add_argument("--absolute", action="store_true", help="输出绝对文件路径")
    parser.add_argument("--validate", action="store_true", help="自检所有映射文件的物理存在性")

    args = parser.parse_args()

    if args.validate:
        sys.exit(0 if validate_all_mappings() else 1)

    skill_root = get_skill_root()
    if args.file:
        target_fp = args.file if os.path.isabs(args.file) else os.path.join(skill_root, args.file)
        if not os.path.isfile(target_fp):
            print(f"❌ 参考文件不存在：{args.file}", file=sys.stderr)
            sys.exit(1)
        with open(target_fp, "r", encoding="utf-8") as f:
            content = f.read()
        print(extract_markdown_section_by_keyword(content, section_query=args.section, list_only=args.list_sections), end="")
        sys.exit(0)

    if args.render and args.json:
        parser.error("--render 与 --json 不能同时使用")
    if args.render and args.mode != "modify":
        parser.error("--render 仅支持 --mode modify")

    raw_assets = ",".join(x for x in (args.assets, args.domains) if x)
    assets = [a.strip() for a in raw_assets.split(",") if a.strip()]
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]

    unknown_scenarios = sorted({s.lower() for s in scenarios} - MODIFY_COMPLEX_SCENARIOS)
    if args.mode == "modify" and unknown_scenarios:
        parser.error(
            "未知 Modify 复杂场景：" + ", ".join(unknown_scenarios)
            + "；可选值：" + ", ".join(sorted(MODIFY_COMPLEX_SCENARIOS))
        )

    resolved_rel_paths = resolve_files(args.mode, assets, scenarios=scenarios, step=args.step)
    final_paths = [os.path.join(skill_root, p) for p in resolved_rel_paths] if args.absolute else resolved_rel_paths

    if args.render:
        print(render_modify_policy_bundle(resolved_rel_paths, assets, scenarios, absolute=args.absolute), end="")
    elif args.json:
        references = build_reference_records(resolved_rel_paths, assets, scenarios, absolute=args.absolute)
        output_data = {
            "mode": args.mode,
            "guideIncluded": "modify/modify_guide.md" in resolved_rel_paths if args.mode == "modify" else None,
            "assets": assets,
            "scenarios": scenarios,
            "step": args.step if args.step else None,
            "resolvedCount": len(final_paths),
            "files": final_paths,
            "references": references,
        }
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        for p in final_paths:
            print(p)


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        sys.exit(2)
