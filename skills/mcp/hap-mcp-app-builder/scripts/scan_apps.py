#!/usr/bin/env python3
"""
scan_apps.py — 扫描 .hap-copilot/apps/（兼容旧版 apps/）目录，输出每个应用的路径、名称与搭建状态。

用法：python3 scan_apps.py <projectRoot>
输出：JSON 对象 { "apps": [...] }
"""

import json
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)

# 从 hap-mcp-app-builder v1.0.0 覆盖升级时可能残留的旧版废弃文件与目录
LEGACY_V1_PATHS = (
    "plan/SKILL.md",
    "plan/design_guide.md",
    "plan/icon_and_style_guide.md",
    "plan/scripts",
    "build/SKILL.md",
    "build/CAPABILITY_MATRIX.md",
    "build/resources",
    "build/scripts",
    "build/steps/2_create_worksheets.md",
    "build/steps/3_refresh_fields.md",
    "build/steps/4_create_actions.md",
    "build/steps/5_create_views.md",
    "build/steps/5b_create_page_shells.md",
    "build/steps/6_create_sample_data.md",
    "build/steps/7_create_pages.md",
    "build/steps/9_design_workflows.md",
    "build/steps/12_cli_refinement.md",
    "build/steps/workflow_rules.md",
)


def cleanup_legacy_v1_files(skill_root: str = SKILL_ROOT) -> list:
    """清理从 v1.0.0 覆盖复制升级后残留的旧版文件，保持本地 Skill 目录纯净。"""
    removed = []
    for rel in LEGACY_V1_PATHS:
        target = os.path.join(skill_root, rel)
        if not os.path.exists(target):
            continue
        try:
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            removed.append(rel)
        except OSError:
            pass
    return removed

project_root = (
    os.path.abspath(sys.argv[1])
    if len(sys.argv) > 1
    else os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
)


def ensure_hidden_gitignore(hidden_root: str) -> None:
    """确保 .hap-copilot/.gitignore 存在并忽略内部过程文件，防止污染宿主 Git 仓库。"""
    if os.path.isdir(hidden_root):
        gi = os.path.join(hidden_root, ".gitignore")
        if not os.path.exists(gi):
            try:
                with open(gi, "w", encoding="utf-8") as f:
                    f.write("*\n")
            except OSError:
                pass


def scan_single_root(apps_dir: str, is_legacy: bool, seen_paths: set) -> list:
    items = []
    if not os.path.isdir(apps_dir):
        return items

    for entry in sorted(os.listdir(apps_dir)):
        entry_path = os.path.join(apps_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        plan_path = os.path.join(entry_path, "hap-plan.json")
        if not os.path.isfile(plan_path):
            continue

        real_path = os.path.realpath(entry_path)
        if real_path in seen_paths:
            continue
        seen_paths.add(real_path)
        app_name = entry
        plan = {}
        ctx = {}
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
            if not isinstance(plan, dict):
                plan = {}
            if plan.get("appName"):
                app_name = plan["appName"]
        except Exception:
            pass

        ctx_path = os.path.join(entry_path, "hap-context.json")
        progress = None
        status = "planned"

        if os.path.isfile(ctx_path):
            try:
                with open(ctx_path, "r", encoding="utf-8") as f:
                    ctx = json.load(f)
                if not isinstance(ctx, dict):
                    ctx = {}
                progress = ctx.get("progress")
                status = "completed" if progress == "completed" else "in_progress"
            except Exception:
                pass

        try:
            with open(os.path.join(entry_path, ".build", "run.json"), encoding="utf-8") as f:
                run = json.load(f)
            if not isinstance(run, dict):
                run = {}
        except (OSError, ValueError):
            run = {}

        items.append({
            "dir": entry,
            "appDir": entry_path,
            "appName": app_name,
            "mcpServer": run.get("mcpServer") or ctx.get("mcpServer") or plan.get("mcpServer"),
            "orgId": plan.get("orgId") or plan.get("org_id") or ctx.get("orgId") or ctx.get("org_id"),
            "appId": ctx.get("appId"),
            "runId": run.get("runId"),
            "progress": progress,
            "status": status,
            "legacyLocation": is_legacy,
        })

    return items


def scan_apps():
    hidden_root = os.path.join(project_root, ".hap-copilot")
    ensure_hidden_gitignore(hidden_root)

    seen_paths = set()
    results = []
    # 1. 优先扫描标准隐藏工作目录 {PROJECT_ROOT}/.hap-copilot/apps/
    results.extend(scan_single_root(os.path.join(hidden_root, "apps"), False, seen_paths))
    # 2. 兼容扫描历史目录 {PROJECT_ROOT}/apps/
    results.extend(scan_single_root(os.path.join(project_root, "apps"), True, seen_paths))
    return results


if __name__ == "__main__":
    cleanup_legacy_v1_files()
    output = {"apps": scan_apps()}
    print(json.dumps(output, ensure_ascii=False, indent=2))
