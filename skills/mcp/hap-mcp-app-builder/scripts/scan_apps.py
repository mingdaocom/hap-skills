#!/usr/bin/env python3
"""
scan_apps.py — 扫描 .hap-copilot/apps/（兼容旧版 apps/）目录，输出每个应用的路径、名称与搭建状态。

用法：python3 scan_apps.py <projectRoot>
输出：JSON 对象 { "apps": [...] }
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

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
    output = {"apps": scan_apps()}
    print(json.dumps(output, ensure_ascii=False, indent=2))
