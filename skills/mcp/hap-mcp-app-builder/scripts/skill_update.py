#!/usr/bin/env python3
"""
HAP App Copilot 技能版本检查、SHA256 清单校验、多版本软链原子更新与秒级回滚工具。
仅使用 Python 标准库，对源码开发软链与本地修改提供强保护（绝不静默覆盖定制内容）。
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from zipfile import ZipFile

SUCCESS_CACHE_TTL = 300   # 成功检查缓存 5 分钟
FAILURE_CACHE_TTL = 60    # 失败重试冷却 1 分钟
HTTP_TIMEOUT = 8


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json_safe(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


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
        raise ValueError("默认仅允许 HTTPS 更新源；研发 HTTP 源须显式传入 --allow-http")
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError(f"非法更新源地址：{url}")
    opener = urllib.request.build_opener(_NoRedirectHandler)
    req = urllib.request.Request(url, headers={"User-Agent": "hap-app-copilot-updater/1.0"})
    with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def resolve_paths(skill_dir_arg: str = None):
    if skill_dir_arg:
        entry_path = Path(skill_dir_arg).expanduser()
    else:
        # 若通过符号链接调用，优先识别宿主技能入口路径
        env_entry = os.environ.get("HAP_COPILOT_ENTRY_DIR")
        entry_path = Path(env_entry).expanduser() if env_entry else Path(__file__).resolve().parents[1]
    parent_resolved = entry_path.parent.resolve()
    entry_path = parent_resolved / entry_path.name
    real_path = entry_path.resolve()
    releases_parent = parent_resolved / ".hap-app-copilot-releases"
    is_managed_release = (
        entry_path.is_symlink()
        and releases_parent in real_path.parents
    )
    is_source_Editable = (
        (real_path.parent / "skill-maintainer").is_dir()
        or (real_path / ".git").exists()
        or (entry_path.is_symlink() and not is_managed_release)
    )
    return entry_path, real_path, releases_parent, is_managed_release, is_source_Editable


def detect_dirty_files(real_path: Path, install_meta: dict) -> list:
    manifest = install_meta.get("manifest") if isinstance(install_meta, dict) else None
    recorded_files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(recorded_files, dict) or not recorded_files:
        return []
    dirty = []
    for rel_str, expected_hash in recorded_files.items():
        fp = real_path / rel_str
        if not fp.is_file():
            dirty.append(f"缺失:{rel_str}")
        elif sha256_file(fp) != expected_hash:
            dirty.append(f"已修改:{rel_str}")
    return dirty


def get_cache_path() -> Path:
    return Path.home() / ".gemini" / "config" / "skills" / ".hap-app-copilot-update-cache.json"


def cmd_status(skill_dir: str = None) -> dict:
    entry_path, real_path, _, is_managed, is_source = resolve_paths(skill_dir)
    release = load_json_safe(real_path / "version.json")
    install_meta = load_json_safe(real_path / ".installation.json")
    dirty = detect_dirty_files(real_path, install_meta)
    return {
        "name": release.get("name", "hap-mcp-app-builder"),
        "version": release.get("version", "unknown"),
        "minToolsCount": release.get("minToolsCount", 170),
        "repository": release.get("repository", ""),
        "branch": release.get("branch", "main"),
        "skillPath": release.get("skillPath", ""),
        "entryPath": str(entry_path),
        "realPath": str(real_path),
        "isManagedRelease": is_managed,
        "isSourceWorkspace": is_source,
        "source": install_meta.get("source", ""),
        "autoUpdate": bool(install_meta.get("autoUpdate", not is_source)),
        "previousRelease": install_meta.get("previous", ""),
        "dirtyFiles": dirty,
    }


def _github_raw_version_url(st: dict) -> str:
    repo_url = st.get("repository", "")
    match = re.search(r"github\.com/([^/]+/[^/.]+)", str(repo_url))
    if not match:
        return ""
    branch = st.get("branch") or "main"
    skill_path = str(st.get("skillPath") or "").strip("/")
    rel = f"{skill_path}/version.json" if skill_path else "version.json"
    return f"https://raw.githubusercontent.com/{match.group(1)}/{branch}/{rel}"


def cmd_check(skill_dir: str = None, server: str = None, force: bool = False, allow_http: bool = False) -> dict:
    st = cmd_status(skill_dir)
    source_url = (server or st["source"] or "").rstrip("/")

    if st["isSourceWorkspace"] and not server:
        return {
            **st,
            "checked": False,
            "updateAvailable": False,
            "reason": "当前为源码开发目录或外部符号链接，自动跳过远端更新检查以保护本地修改。",
        }
    if not st["autoUpdate"] and not force:
        return {
            **st,
            "checked": False,
            "updateAvailable": False,
            "reason": "自动更新已关闭（可通过 auto-update --enable 重新开启）。",
        }
    gh_raw_url = _github_raw_version_url(st) if not source_url else ""
    if not source_url and not gh_raw_url:
        return {
            **st,
            "checked": False,
            "updateAvailable": False,
            "reason": "尚未绑定更新源地址（首次受管理安装或传入 --server 后生效）。",
        }

    cache_key = source_url or gh_raw_url
    cache_path = get_cache_path()
    cache = load_json_safe(cache_path)
    now = time.time()
    if not force and cache.get("source") == cache_key and cache.get("localVersion") == st["version"]:
        elapsed = now - float(cache.get("timestamp", 0))
        if cache.get("ok") and elapsed < SUCCESS_CACHE_TTL:
            return {**st, **cache.get("result", {}), "fromCache": True}
        if not cache.get("ok") and elapsed < FAILURE_CACHE_TTL:
            return {**st, "checked": False, "updateAvailable": False, "fromCache": True, "error": cache.get("error", "")}

    try:
        if source_url:
            manifest_url = f"{source_url}/api/skills/hap-app-copilot.manifest.json"
            raw = http_get_bytes(manifest_url, allow_http=allow_http or bool(load_json_safe(Path(st["realPath"]) / ".installation.json").get("allowHttp")))
            remote_manifest = json.loads(raw.decode("utf-8"))
            remote_ver = str(remote_manifest.get("version", ""))
            has_update = parse_version(remote_ver) > parse_version(st["version"])
            res = {
                "checked": True,
                "source": source_url,
                "remoteVersion": remote_ver,
                "updateAvailable": has_update,
                "archiveSHA256": remote_manifest.get("archiveSHA256", ""),
            }
        else:
            raw = http_get_bytes(gh_raw_url, allow_http=False)
            remote_ver_meta = json.loads(raw.decode("utf-8"))
            remote_ver = str(remote_ver_meta.get("version", ""))
            has_update = parse_version(remote_ver) > parse_version(st["version"])
            res = {
                "checked": True,
                "source": st.get("repository", gh_raw_url),
                "remoteVersion": remote_ver,
                "updateAvailable": has_update,
                "releaseNotes": remote_ver_meta.get("releaseNotes", ""),
            }
        save_json_atomic(cache_path, {
            "source": cache_key,
            "localVersion": st["version"],
            "timestamp": now,
            "ok": True,
            "result": res,
        })
        return {**st, **res, "fromCache": False}
    except Exception as exc:
        err_msg = str(exc)
        save_json_atomic(cache_path, {
            "source": cache_key,
            "localVersion": st["version"],
            "timestamp": now,
            "ok": False,
            "error": err_msg,
        })
        return {**st, "checked": False, "updateAvailable": False, "error": err_msg}


def cmd_update(skill_dir: str = None, server: str = None, allow_http: bool = False) -> dict:
    entry_path, real_path, releases_parent, is_managed, is_source = resolve_paths(skill_dir)
    install_meta = load_json_safe(real_path / ".installation.json")
    st = cmd_status(skill_dir)

    if is_source:
        raise ValueError("当前目录指向源码工作区或外部自定义软链接，拒绝自动覆盖；请在源码仓库中维护或切换为独立受管理目录。")
    dirty = st["dirtyFiles"]
    if dirty:
        raise ValueError(f"检测到本地定制修改（{', '.join(dirty[:5])}），已保留现有文件并停止覆盖更新。")

    source_url = (server or st["source"] or "").rstrip("/")
    gh_raw_url = _github_raw_version_url(st) if not source_url else ""
    if not source_url and not gh_raw_url:
        raise ValueError("未指定更新源地址 --server，且当前目录无 .installation.json source 或 GitHub repository 记录。")

    if not source_url and gh_raw_url:
        raw = http_get_bytes(gh_raw_url, allow_http=False)
        remote_ver_meta = json.loads(raw.decode("utf-8"))
        remote_ver = str(remote_ver_meta.get("version", ""))
        if parse_version(remote_ver) <= parse_version(st["version"]):
            return {**st, "updated": False, "reason": f"当前已是最新版本 ({st['version']})"}
        repo_url = st.get("repository", "")
        branch = st.get("branch") or "main"
        skill_subpath = str(st.get("skillPath") or "").strip("/")
        with tempfile.TemporaryDirectory() as tmp_dir:
            clone_dir = Path(tmp_dir) / "repo"
            subprocess.run(
                ["git", "clone", "--depth", "1", "-b", branch, repo_url, str(clone_dir)],
                check=True, capture_output=True, text=True,
            )
            src_skill = (clone_dir / skill_subpath) if skill_subpath else clone_dir
            if not (src_skill / "SKILL.md").is_file():
                raise ValueError(f"远端仓库路径不存在有效 SKILL.md：{skill_subpath}")
            releases_parent.mkdir(parents=True, exist_ok=True)
            target_release = releases_parent / f"release-{remote_ver}-{int(time.time())}"
            shutil.copytree(src_skill, target_release)
            if not entry_path.is_symlink() and entry_path.exists():
                backup_dir = releases_parent / f"backup-{st['version']}-{int(time.time())}"
                os.replace(entry_path, backup_dir)
                save_json_atomic(target_release / ".installation.json", {
                    "previous": str(backup_dir),
                    "autoUpdate": True,
                    "updatedAt": int(time.time()),
                })
            tmp_link = entry_path.parent / f".hap-app-copilot-link-{os.getpid()}"
            if tmp_link.exists() or tmp_link.is_symlink():
                tmp_link.unlink()
            tmp_link.symlink_to(target_release)
            os.replace(tmp_link, entry_path)
        return {
            "updated": True,
            "previousVersion": st["version"],
            "version": remote_ver,
            "entryPath": str(entry_path),
            "realPath": str(target_release),
            "reloadRequired": "请重新调用 read_file 读取更新后的 SKILL.md 与 version.json",
        }

    use_http = allow_http or bool(install_meta.get("allowHttp"))
    manifest_url = f"{source_url}/api/skills/hap-app-copilot.manifest.json"
    manifest = json.loads(http_get_bytes(manifest_url, allow_http=use_http).decode("utf-8"))

    remote_ver = str(manifest.get("version", ""))
    expected_zip_sha = str(manifest.get("archiveSHA256", ""))
    expected_files = manifest.get("files") or {}
    if not remote_ver or not expected_zip_sha or not isinstance(expected_files, dict):
        raise ValueError("远端 manifest.json 缺少 version、archiveSHA256 或 files 清单")

    if parse_version(remote_ver) <= parse_version(st["version"]):
        return {**st, "updated": False, "reason": f"当前已是最新版本 ({st['version']})"}

    archive_rel = manifest.get("archivePath") or "/api/skills/hap-app-copilot.zip"
    zip_url = f"{source_url}{archive_rel}" if archive_rel.startswith("/") else f"{source_url}/{archive_rel}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_zip = Path(tmp_dir) / "hap-app-copilot.zip"
        tmp_zip.write_bytes(http_get_bytes(zip_url, allow_http=use_http))
        actual_zip_sha = sha256_file(tmp_zip)
        if actual_zip_sha != expected_zip_sha:
            raise ValueError(f"ZIP SHA256 校验失败：期望 {expected_zip_sha}，实际 {actual_zip_sha}")

        extract_dir = Path(tmp_dir) / "extracted"
        with ZipFile(tmp_zip) as zf:
            zf.extractall(extract_dir)

        unpacked_root = extract_dir / "hap-mcp-app-builder"
        if not unpacked_root.is_dir():
            unpacked_root = extract_dir / "hap-app-copilot"
        if not unpacked_root.is_dir():
            unpacked_root = extract_dir

        for rel_str, f_sha in expected_files.items():
            fp = unpacked_root / rel_str
            if not fp.is_file():
                raise ValueError(f"更新包缺失清单文件：{rel_str}")
            if sha256_file(fp) != f_sha:
                raise ValueError(f"更新包文件 SHA256 不匹配：{rel_str}")

        releases_parent.mkdir(parents=True, exist_ok=True)
        target_release = releases_parent / f"release-{remote_ver}-{expected_zip_sha[:10]}"
        if target_release.exists():
            shutil.rmtree(target_release)
        shutil.copytree(unpacked_root, target_release)

        new_install_meta = {
            "source": source_url,
            "allowHttp": use_http,
            "manifest": manifest,
            "autoUpdate": bool(install_meta.get("autoUpdate", True)),
            "previous": str(real_path) if real_path != target_release else install_meta.get("previous", ""),
            "updatedAt": int(time.time()),
        }
        save_json_atomic(target_release / ".installation.json", new_install_meta)

        # 若原入口是普通目录，先备份迁移至 releases_parent 下再切换为原子软链
        if not entry_path.is_symlink() and entry_path.exists():
            backup_dir = releases_parent / f"backup-{st['version']}-{int(time.time())}"
            os.replace(entry_path, backup_dir)
            new_install_meta["previous"] = str(backup_dir)
            save_json_atomic(target_release / ".installation.json", new_install_meta)

        tmp_link = entry_path.parent / f".hap-app-copilot-link-{os.getpid()}"
        if tmp_link.exists() or tmp_link.is_symlink():
            tmp_link.unlink()
        tmp_link.symlink_to(target_release)
        os.replace(tmp_link, entry_path)

    return {
        "updated": True,
        "previousVersion": st["version"],
        "version": remote_ver,
        "entryPath": str(entry_path),
        "realPath": str(target_release),
        "reloadRequired": "请重新调用 read_file 读取更新后的 SKILL.md 与 version.json",
    }


def cmd_rollback(skill_dir: str = None) -> dict:
    entry_path, real_path, _, _, is_source = resolve_paths(skill_dir)
    if is_source:
        raise ValueError("当前为源码工作区软链，不支持发行包回滚。")
    install_meta = load_json_safe(real_path / ".installation.json")
    prev_str = install_meta.get("previous", "")
    if not prev_str:
        raise ValueError("未找到可回滚的上一版本记录（previous 为空）。")
    prev_path = Path(prev_str)
    if not prev_path.is_dir() or not (prev_path / "SKILL.md").is_file():
        raise ValueError(f"上一版本目录不存在或不完整：{prev_path}")

    # 回滚后自动关闭该版本的自动更新，防止立即又被自动升回
    prev_meta = load_json_safe(prev_path / ".installation.json")
    prev_meta["autoUpdate"] = False
    save_json_atomic(prev_path / ".installation.json", prev_meta)

    tmp_link = entry_path.parent / f".hap-app-copilot-rollback-{os.getpid()}"
    if tmp_link.exists() or tmp_link.is_symlink():
        tmp_link.unlink()
    tmp_link.symlink_to(prev_path)
    os.replace(tmp_link, entry_path)

    prev_rel = load_json_safe(prev_path / "version.json")
    return {
        "rolledBack": True,
        "version": prev_rel.get("version", "unknown"),
        "realPath": str(prev_path),
        "autoUpdate": False,
        "reloadRequired": "已回滚并关闭自动更新；请重新读取 SKILL.md 与 version.json",
    }


def cmd_auto_update(skill_dir: str, enable: bool, server: str = None, allow_http: bool = False) -> dict:
    _, real_path, _, _, _ = resolve_paths(skill_dir)
    meta_path = real_path / ".installation.json"
    meta = load_json_safe(meta_path)
    meta["autoUpdate"] = bool(enable)
    if server:
        meta["source"] = server.rstrip("/")
    if allow_http:
        meta["allowHttp"] = True
    save_json_atomic(meta_path, meta)
    return {"autoUpdate": meta["autoUpdate"], "source": meta.get("source", ""), "updated": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=str, default=None, help="指定 Skill 入口目录")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="离线查看当前版本、安装形态、脏文件与自动更新状态")

    p_chk = sub.add_parser("check", help="检查远端是否有新版本（默认带 5 分钟缓存）")
    p_chk.add_argument("--server", type=str, default=None, help="更新源服务地址")
    p_chk.add_argument("--force", action="store_true", help="忽略缓存立即检查")
    p_chk.add_argument("--allow-http", action="store_true", help="允许研发 HTTP 更新源")

    p_upd = sub.add_parser("update", help="下载、校验 SHA256 并通过软链原子更新至最新版本")
    p_upd.add_argument("--server", type=str, default=None, help="更新源服务地址")
    p_upd.add_argument("--allow-http", action="store_true", help="允许研发 HTTP 更新源")

    sub.add_parser("rollback", help="离线原子回滚至上一保留版本并关闭自动更新")

    p_au = sub.add_parser("auto-update", help="开启或关闭自动更新")
    group = p_au.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true", help="开启自动更新")
    group.add_argument("--disable", action="store_true", help="关闭自动更新")
    p_au.add_argument("--server", type=str, default=None, help="可选绑定更新源地址")
    p_au.add_argument("--allow-http", action="store_true", help="允许研发 HTTP 更新源")

    args = parser.parse_args()
    if args.command == "status":
        res = cmd_status(args.skill_dir)
    elif args.command == "check":
        res = cmd_check(args.skill_dir, args.server, args.force, args.allow_http)
    elif args.command == "update":
        res = cmd_update(args.skill_dir, args.server, args.allow_http)
    elif args.command == "rollback":
        res = cmd_rollback(args.skill_dir)
    elif args.command == "auto-update":
        res = cmd_auto_update(args.skill_dir, args.enable, args.server, args.allow_http)
    else:
        raise ValueError(f"未知命令：{args.command}")

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)
