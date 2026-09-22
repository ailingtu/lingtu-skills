#!/usr/bin/env python3
"""Publish one local Skill to Lingtu SkillHub or Tencent WorkBuddy."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LINGTU_ENV = "LINGTU_SKILLHUB_TOKEN"
WORKBUDDY_ENV = "SKILLHUB_KEY"
LINGTU_TOKEN = re.compile(r"^blg_[A-Za-z0-9_-]{43}$")
WORKBUDDY_TOKEN = re.compile(r"^skh_[A-Za-z0-9]{20,}$")
LINGTU_NAME = re.compile(r"^lingtu-[a-z0-9]+(?:-[a-z0-9]+)*$")
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
FRONTMATTER_KEYS = {
    "name", "slug", "version", "auth", "displayName", "summary",
    "description", "license", "homepage",
}
SKIP_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", ".venv", "tests",
}
SKIP_FILES = {".DS_Store", "Thumbs.db", "README.md", "LICENSE"}
MAX_ZIP_BYTES = 32 * 1024 * 1024
LINGTU_URL = "https://ailingtu.com/api/supermanage/skills"
WORKBUDDY_HOST = "https://api.skillhub.cn"
ICON_KEYS = {"arrow-up-tray", "video-camera", "chart-bar", "eye", "play-circle", "chat-bubble"}
TONES = {"emerald", "violet", "rose", "cyan", "sky", "amber"}
LOCALE_FIELDS = ("title", "description", "prompt", "input", "output", "requirement", "categoryLabel")


class PublishError(Exception):
    def __init__(self, message: str, code: str = "error", details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def redact(text: str, secrets: list[str]) -> str:
    cleaned = text
    for secret in secrets:
        if secret:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def credential(env_name: str, pattern: re.Pattern[str], label: str) -> dict:
    raw = os.environ.get(env_name, "")
    value = raw.strip()
    if not value:
        return {"env": env_name, "configured": False, "accepted": False, "label": label}
    if pattern.fullmatch(value) is None:
        return {
            "env": env_name,
            "configured": True,
            "accepted": False,
            "label": label,
            "reason": f"{env_name} 已设置，但不是{label}的密钥格式",
        }
    return {"env": env_name, "configured": True, "accepted": True, "label": label}


def status_payload() -> dict:
    return {
        "ok": True,
        "ignored": ["LINGTU_API_KEY", "BLOG_AGENT_TOKEN"],
        "platforms": {
            "lingtu": credential(LINGTU_ENV, LINGTU_TOKEN, "灵途发布密钥"),
            "workbuddy": credential(WORKBUDDY_ENV, WORKBUDDY_TOKEN, "腾讯 SkillHub API Key"),
            "other": {"available": False, "reason": "其它平台接入中"},
        },
    }


def require_credential(env_name: str, pattern: re.Pattern[str], label: str) -> str:
    item = credential(env_name, pattern, label)
    if not item["configured"]:
        raise PublishError(f"未配置 {env_name}。读取 references/credentials.md 后再试。", "missing_credential")
    if not item["accepted"]:
        raise PublishError(item["reason"], "invalid_credential")
    value = os.environ[env_name].strip()
    return value


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", text, re.DOTALL)
    if not match:
        raise PublishError(f"{skill_md} 缺少 YAML frontmatter", "invalid_skill")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in FRONTMATTER_KEYS:
            values[key.strip()] = value.strip().strip("\"'")
    return values


def skill_dir(path: Path) -> Path:
    directory = path.expanduser().resolve()
    if not directory.is_dir() or not (directory / "SKILL.md").is_file():
        raise PublishError(f"{directory} 不是包含 SKILL.md 的技能目录", "invalid_skill")
    return directory


def lint_lingtu(metadata: dict[str, str], directory: Path) -> list[str]:
    errors: list[str] = []
    name = metadata.get("name", "")
    if LINGTU_NAME.fullmatch(name) is None:
        errors.append("灵途 SkillHub 要求 name 为 lingtu- 开头的 kebab-case")
    if metadata.get("slug") != name:
        errors.append("灵途 SkillHub 要求 slug 与 name 相同")
    if SEMVER.fullmatch(metadata.get("version", "")) is None:
        errors.append("灵途 SkillHub 要求 version 为 x.y.z")
    if metadata.get("auth") not in {"lingtu-api-key", "none"}:
        errors.append("auth 只能是 lingtu-api-key 或 none")
    for key in ("displayName", "summary"):
        if not metadata.get(key):
            errors.append(f"缺少 {key}")
    catalog_path = directory / "catalog.json"
    if catalog_path.is_file():
        errors.extend(validate_catalog_file(catalog_path, name))
    return errors


def lint_workbuddy(metadata: dict[str, str]) -> list[str]:
    errors: list[str] = []
    slug = metadata.get("slug") or metadata.get("name") or ""
    if KEBAB.fullmatch(slug) is None or not 2 <= len(slug) <= 128:
        errors.append("WorkBuddy 要求 slug（或 name）为 2–128 位 kebab-case")
    if SEMVER.fullmatch(metadata.get("version", "")) is None:
        errors.append("WorkBuddy 要求 version 为 x.y.z")
    if not metadata.get("displayName"):
        errors.append("WorkBuddy 要求 displayName")
    return errors


def validate_catalog_file(path: Path, package_name: str) -> list[str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["catalog.json 不是有效 JSON"]
    return validate_catalog(document, package_name)


def validate_catalog(catalog: object, package_name: str) -> list[str]:
    if not isinstance(catalog, dict):
        return ["catalog 必须是对象"]
    errors: list[str] = []
    slug = catalog.get("slug")
    if not isinstance(slug, str) or KEBAB.fullmatch(slug) is None:
        errors.append("catalog.slug 不合法")
    elif package_name and f"lingtu-{slug}" != package_name:
        errors.append("catalog.slug 与技能包 name 不一致")
    if not isinstance(catalog.get("category"), str) or not re.fullmatch(r"[a-z0-9-]+", catalog["category"]):
        errors.append("catalog.category 不合法")
    if catalog.get("iconKey") not in ICON_KEYS:
        errors.append("catalog.iconKey 不在允许列表")
    if catalog.get("tone") not in TONES:
        errors.append("catalog.tone 不在允许列表")
    platforms = catalog.get("platforms")
    if not isinstance(platforms, list) or not platforms or any(not isinstance(item, str) or not item.strip() for item in platforms):
        errors.append("catalog.platforms 必须是非空字符串数组")
    if not isinstance(catalog.get("sortOrder"), int) or isinstance(catalog.get("sortOrder"), bool):
        errors.append("catalog.sortOrder 必须是整数")
    locales = catalog.get("locales")
    if not isinstance(locales, dict):
        errors.append("catalog.locales 缺少 zh-CN 与 en-US")
        return errors
    for locale in ("zh-CN", "en-US"):
        copy = locales.get(locale)
        if not isinstance(copy, dict):
            errors.append(f"缺少 locales.{locale}")
            continue
        for field in LOCALE_FIELDS:
            if not isinstance(copy.get(field), str) or not copy[field].strip():
                errors.append(f"缺少 locales.{locale}.{field}")
        highlights = copy.get("highlights")
        if not isinstance(highlights, list) or not highlights or any(not isinstance(item, str) or not item.strip() for item in highlights):
            errors.append(f"缺少 locales.{locale}.highlights")
    return errors


def lint_payload(directory: Path, platform: str) -> dict:
    metadata = parse_frontmatter(directory / "SKILL.md")
    reports = {}
    if platform in {"lingtu", "all"}:
        issues = lint_lingtu(metadata, directory)
        reports["lingtu"] = {
            "ok": not issues,
            "issues": issues,
            "catalog": "embedded" if (directory / "catalog.json").is_file() else "required-for-new-skill",
        }
    if platform in {"workbuddy", "all"}:
        issues = lint_workbuddy(metadata)
        reports["workbuddy"] = {"ok": not issues, "issues": issues}
    return {
        "ok": all(item["ok"] for item in reports.values()),
        "directory": str(directory),
        "name": metadata.get("name") or metadata.get("slug"),
        "version": metadata.get("version"),
        "platforms": reports,
    }


def build_zip(directory: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for dirpath, dirnames, filenames in os.walk(directory):
            current = Path(dirpath)
            dirnames[:] = sorted(
                name for name in dirnames
                if name not in SKIP_DIRS and not name.startswith(".")
            )
            for name in sorted(filenames):
                path = current / name
                if name.startswith(".") or name in SKIP_FILES:
                    continue
                if path.is_symlink():
                    raise PublishError(f"技能目录包含符号链接，已停止打包: {path}", "invalid_skill")
                if not path.is_file():
                    continue
                arcname = path.relative_to(directory).as_posix()
                if ".." in Path(arcname).parts:
                    raise PublishError(f"非法打包路径: {arcname}", "invalid_skill")
                archive.write(path, arcname)
    body = buffer.getvalue()
    if not body or len(body) > MAX_ZIP_BYTES:
        raise PublishError("技能包必须是不超过 32 MB 的 ZIP", "invalid_skill")
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        if "SKILL.md" not in archive.namelist():
            raise PublishError("ZIP 根目录必须包含 SKILL.md", "invalid_skill")
    return body


def encode_multipart(fields: list[tuple[str, str]], file_field: tuple[str, str, bytes]) -> tuple[str, bytes]:
    boundary = f"----lingtu{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    filename, content_type, payload = file_field
    chunks.append(
        (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + payload + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode())
    return boundary, b"".join(chunks)


def lingtu_base_url() -> str:
    raw = os.environ.get("LINGTU_SKILLHUB_BASE_URL", "https://ailingtu.com").strip().rstrip("/")
    if not re.fullmatch(r"https?://[A-Za-z0-9._:-]+", raw):
        raise PublishError("LINGTU_SKILLHUB_BASE_URL 必须是不含路径的 http(s) 地址", "invalid_request")
    return raw


def publish_lingtu(directory: Path, catalog_path: Path | None, confirm: bool, opener=urlopen) -> dict:
    report = lint_payload(directory, "lingtu")
    if not report["ok"]:
        raise PublishError("；".join(report["platforms"]["lingtu"]["issues"]), "invalid_skill")
    token = require_credential(LINGTU_ENV, LINGTU_TOKEN, "灵途发布密钥")
    metadata = parse_frontmatter(directory / "SKILL.md")
    fields = [("packageName", metadata["name"])]
    catalog_source = "embedded" if (directory / "catalog.json").is_file() else "existing-or-required"
    if catalog_path is not None:
        document = json.loads(catalog_path.read_text(encoding="utf-8"))
        issues = validate_catalog(document, metadata["name"])
        if issues:
            raise PublishError("；".join(issues), "invalid_skill")
        fields.append(("catalog", json.dumps(document, ensure_ascii=False)))
        catalog_source = "request"
    plan = {
        "ok": True,
        "platform": "lingtu",
        "dryRun": not confirm,
        "packageName": metadata["name"],
        "version": metadata["version"],
        "catalog": catalog_source,
        "endpoint": f"{lingtu_base_url()}/api/supermanage/skills",
    }
    if not confirm:
        return plan
    body = build_zip(directory)
    boundary, payload = encode_multipart(fields, (f"{metadata['name']}.zip", "application/zip", body))
    request = Request(
        plan["endpoint"],
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with opener(request, timeout=120) as response:
            raw = response.read()
            status_code = getattr(response, "status", 200)
    except HTTPError as exc:
        detail = redact(exc.read().decode("utf-8", "replace"), [token])
        raise PublishError(f"灵途发布失败（HTTP {exc.code}）：{detail[:500]}", "publish_failed") from None
    except URLError as exc:
        raise PublishError(f"无法连接灵途 SkillHub：{exc.reason}", "publish_failed") from None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        parsed = {"raw": redact(raw.decode("utf-8", "replace"), [token])[:500]}
    plan.update({"dryRun": False, "httpStatus": status_code, "result": parsed, "bytes": len(body)})
    return plan


def run_skillhub(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)


def publish_workbuddy(directory: Path, confirm: bool, runner=run_skillhub, cli_available: bool | None = None) -> dict:
    available = shutil.which("skillhub") is not None if cli_available is None else cli_available
    if not available:
        raise PublishError(
            "未找到 skillhub 命令。请客户打开 https://skillhub.cn/tutorials 安装 CLI，"
            "安装后执行 skillhub --version，确认有版本号后再继续。不要代替客户下载或执行安装脚本。",
            "missing_cli",
            {"installUrl": "https://skillhub.cn/tutorials", "check": "skillhub --version"},
        )
    configured = credential(WORKBUDDY_ENV, WORKBUDDY_TOKEN, "腾讯 SkillHub API Key")
    if configured["configured"] and not configured["accepted"]:
        raise PublishError(configured["reason"], "invalid_credential")
    token = os.environ.get(WORKBUDDY_ENV, "").strip() if configured["accepted"] else ""
    if confirm:
        token = require_credential(WORKBUDDY_ENV, WORKBUDDY_TOKEN, "腾讯 SkillHub API Key")
    try:
        metadata = parse_frontmatter(directory / "SKILL.md")
    except PublishError:
        metadata = {}
    plan = {
        "ok": True,
        "platform": "workbuddy",
        "dryRun": not confirm,
        "slug": metadata.get("slug") or metadata.get("name"),
        "version": metadata.get("version"),
        "host": WORKBUDDY_HOST,
    }
    if confirm:
        login = runner(["skillhub", "login", "--key", token, "--host", WORKBUDDY_HOST], directory)
        login_text = redact((login.stdout or "") + (login.stderr or ""), [token])
        unsupported = login.returncode != 0 and any(
            phrase in login_text.lower()
            for phrase in ("unknown flag", "unknown command", "unrecognized", "flag provided but not defined")
        )
        if unsupported:
            login = runner(["skillhub", "auth", "login", "--token", token, "--host", WORKBUDDY_HOST], directory)
            login_text = redact((login.stdout or "") + (login.stderr or ""), [token])
        if login.returncode != 0:
            raise PublishError(f"WorkBuddy 登录失败：{login_text[:500]}", "publish_failed")
    command = ["skillhub", "publish", "--json", "--host", WORKBUDDY_HOST, str(directory)]
    if not confirm:
        command.insert(2, "--dry-run")
    published = runner(command, directory)
    output = redact((published.stdout or "") + (published.stderr or ""), [token])
    if published.returncode != 0:
        raise PublishError(f"WorkBuddy 发布失败：{output[:500]}", "publish_failed")
    plan.update({"output": output.strip()})
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="发布 AI Skill 到灵途 SkillHub 或腾讯 WorkBuddy。")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    lint = sub.add_parser("lint")
    lint.add_argument("directory", type=Path)
    lint.add_argument("--platform", choices=("lingtu", "workbuddy", "all"), default="all")
    for name in ("lingtu", "workbuddy"):
        command = sub.add_parser(name)
        command.add_argument("directory", type=Path)
        command.add_argument("--confirm", action="store_true")
        if name == "lingtu":
            command.add_argument("--catalog", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            emit(status_payload())
            return 0
        directory = skill_dir(args.directory)
        if args.command == "lint":
            payload = lint_payload(directory, args.platform)
            emit(payload)
            return 0 if payload["ok"] else 1
        if args.command == "lingtu":
            catalog = args.catalog.expanduser().resolve() if args.catalog else None
            if catalog is not None and not catalog.is_file():
                raise PublishError(f"找不到 catalog 文件: {catalog}", "invalid_skill")
            emit(publish_lingtu(directory, catalog, args.confirm))
            return 0
        emit(publish_workbuddy(directory, args.confirm))
        return 0
    except PublishError as exc:
        emit({"ok": False, "code": exc.code, "message": str(exc), **exc.details})
        return 2 if exc.code in {"missing_credential", "invalid_credential", "missing_cli"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
