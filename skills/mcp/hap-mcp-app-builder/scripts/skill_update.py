#!/usr/bin/env python3
"""
HAP 应用助手（hap-mcp-app-builder）只读版本检查工具。
仅使用 Python 标准库执行只读 HTTPS 版本比对（24 小时成功缓存 / 1 小时失败冷却 / 3 秒快速超时），
不修改任何本地技能文件，发现高版本时仅返回升级提示由用户确认后再升级。
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request

SUCCESS_CACHE_TTL = 86400  # 成功检查缓存 24 小时
FAILURE_CACHE_TTL = 3600   # 失败重试冷却 1 小时
HTTP_TIMEOUT = 3           # 联网快速超时 3 秒，连不上快速静默跳过


def load_json_safe(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json_safe(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def parse_version(ver: str) -> tuple:
    parts = []
    for seg in str(ver or "0").split("."):
        num = "".join(ch for ch in seg if ch.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, f"拒绝重定向至 {newurl}", headers, fp)


def http_get_bytes(url: str, allow_http: bool = False) -> bytes:
    if url.startswith("http://") and not allow_http:
        raise ValueError("默认仅允许 HTTPS 版本源；本地测试 HTTP 源须显式传入 --allow-http")
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError(f"非法版本源地址：{url}")
    opener = urllib.request.build_opener(_NoRedirectHandler)
    req = urllib.request.Request(url, headers={"User-Agent": "hap-mcp-app-builder-version-check/2.0"})
    with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def resolve_paths(skill_dir_arg: str = None):
    if skill_dir_arg:
        entry_path = Path(skill_dir_arg).expanduser()
    else:
        env_entry = os.environ.get("HAP_COPILOT_ENTRY_DIR")
        entry_path = Path(env_entry).expanduser() if env_entry else Path(__file__).resolve().parents[1]
    parent_resolved = entry_path.parent.resolve()
    entry_path = parent_resolved / entry_path.name
    real_path = entry_path.resolve()
    is_source = (
        (real_path.parent / "skill-maintainer").is_dir()
        or (real_path / ".git").exists()
        or entry_path.is_symlink()
    )
    return entry_path, real_path, is_source


def get_cache_path() -> Path:
    return Path(tempfile.gettempdir()) / "hap-mcp-app-builder-version-cache.json"


def _github_raw_version_url(st: dict) -> str:
    repo_url = st.get("repository", "")
    match = re.search(r"github\.com/([^/]+/[^/.]+)", str(repo_url))
    if not match:
        return ""
    branch = st.get("branch") or "main"
    skill_path = str(st.get("skillPath") or "").strip("/")
    rel = f"{skill_path}/version.json" if skill_path else "version.json"
    return f"https://raw.githubusercontent.com/{match.group(1)}/{branch}/{rel}"


def cmd_status(skill_dir: str = None) -> dict:
    entry_path, real_path, is_source = resolve_paths(skill_dir)
    release = load_json_safe(real_path / "version.json")
    return {
        "name": release.get("name", "hap-mcp-app-builder"),
        "version": release.get("version", "unknown"),
        "minToolsCount": release.get("minToolsCount", 170),
        "repository": release.get("repository", ""),
        "branch": release.get("branch", "main"),
        "skillPath": release.get("skillPath", ""),
        "entryPath": str(entry_path),
        "realPath": str(real_path),
        "isSourceWorkspace": is_source,
        "mode": "readonly-check",
    }


def cmd_check(skill_dir: str = None, version_url: str = None, force: bool = False, allow_http: bool = False) -> dict:
    st = cmd_status(skill_dir)
    if st["isSourceWorkspace"] and not force and not version_url:
        return {
            **st,
            "checked": False,
            "updateAvailable": False,
            "reason": "当前为源码开发目录或外部符号链接，自动跳过远端版本检查。",
        }

    target_url = (version_url or _github_raw_version_url(st) or "").strip()
    if not target_url:
        return {
            **st,
            "checked": False,
            "updateAvailable": False,
            "reason": "未配置远端版本检查地址。",
        }

    cache_path = get_cache_path()
    cache = load_json_safe(cache_path)
    now = time.time()
    if not force and cache.get("source") == target_url and cache.get("localVersion") == st["version"]:
        elapsed = now - float(cache.get("timestamp", 0))
        if cache.get("ok") and elapsed < SUCCESS_CACHE_TTL:
            return {**st, **cache.get("result", {}), "fromCache": True}
        if not cache.get("ok") and elapsed < FAILURE_CACHE_TTL:
            return {**st, "checked": False, "updateAvailable": False, "fromCache": True, "error": cache.get("error", "")}

    try:
        raw = http_get_bytes(target_url, allow_http=allow_http)
        remote_meta = json.loads(raw.decode("utf-8"))
        remote_ver = str(remote_meta.get("version", ""))
        has_update = parse_version(remote_ver) > parse_version(st["version"])
        res = {
            "checked": True,
            "source": st.get("repository") or target_url,
            "remoteVersion": remote_ver,
            "updateAvailable": has_update,
            "releaseNotes": remote_meta.get("releaseNotes", ""),
        }
        if has_update:
            res["upgradeHint"] = (
                f"检测到 HAP 应用助手新版本 v{remote_ver}（当前 v{st['version']}），"
                "可告知用户回复「升级 HAP 应用助手」或在明道云「连接 AI」重新复制提示词更新。"
            )
        save_json_safe(cache_path, {
            "source": target_url,
            "localVersion": st["version"],
            "timestamp": now,
            "ok": True,
            "result": res,
        })
        return {**st, **res, "fromCache": False}
    except Exception as exc:
        err_msg = str(exc)
        save_json_safe(cache_path, {
            "source": target_url,
            "localVersion": st["version"],
            "timestamp": now,
            "ok": False,
            "error": err_msg,
        })
        return {**st, "checked": False, "updateAvailable": False, "error": err_msg}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=str, default=None, help="指定 Skill 入口目录")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="离线查看当前版本与运行形态")

    p_chk = sub.add_parser("check", help="只读检查远端是否有新版本（默认带 24 小时缓存与 3 秒快速超时）")
    p_chk.add_argument("--url", type=str, default=None, help="可选自定义 version.json 检查地址")
    p_chk.add_argument("--force", action="store_true", help="忽略缓存立即检查")
    p_chk.add_argument("--allow-http", action="store_true", help="允许本地测试 HTTP 地址")

    args = parser.parse_args()
    if args.command == "status":
        res = cmd_status(args.skill_dir)
    elif args.command == "check":
        res = cmd_check(args.skill_dir, args.url, args.force, args.allow_http)
    else:
        raise ValueError(f"未知命令：{args.command}")

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)
