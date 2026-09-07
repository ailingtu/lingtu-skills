#!/usr/bin/env python3
"""Create a Lingtu Skill package with the repository's distribution contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = ROOT / "packages"
AUTH_MODES = ("lingtu-api-key", "none")


def normalize_package_id(value: str) -> str:
    package_id = value.removeprefix("lingtu-")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", package_id):
        raise ValueError("package id 必须是 kebab-case，例如 creator-insights")
    return package_id


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def ui_short_description(display_name: str, summary: str) -> str:
    value = summary.strip()
    if len(value) < 25:
        value = f"{display_name}：{value}"
    if len(value) < 25:
        value += "，提供可复用的灵途 AI 工作流。"
    return value[:64]


def skill_markdown(
    *,
    slug: str,
    display_name: str,
    summary: str,
    description: str,
    auth: str,
    homepage: str,
) -> str:
    auth_section = ""
    if auth == "lingtu-api-key":
        auth_section = """
## Authentication

All authenticated requests use only `LINGTU_API_KEY` and send it as the
`x-api-key` header. Installation does not require authentication. If the key is
missing when running a task, execute
`python3 shared/scripts/user_keys.py single bind` from this Skill root and give
the generated authorization URL to the user. Never ask for, display, or store
the user's API key.
"""
    else:
        auth_section = """
## Authentication

This Skill does not call authenticated Lingtu business APIs and does not read an
API key or start the account-binding flow.
"""

    return f"""---
name: {slug}
slug: {slug}
version: 0.1.0
auth: {auth}
displayName: {yaml_string(display_name)}
summary: {yaml_string(summary)}
description: {yaml_string(description)}
license: Apache-2.0
homepage: {homepage}
---

# {display_name}

## Installation and upgrades

Follow https://ailingtu.com/install/skills.md. Do not install or upgrade this
Skill from GitHub or another skill store.

## Purpose

{description}
{auth_section}
"""


def openai_yaml(slug: str, display_name: str, summary: str) -> str:
    short_description = ui_short_description(display_name, summary)
    default_prompt = f"Use ${slug} to help me with this task: {summary}"
    return f"""interface:
  display_name: {yaml_string(display_name)}
  short_description: {yaml_string(short_description)}
  default_prompt: {yaml_string(default_prompt)}
"""


def create_package(
    package_id: str,
    *,
    display_name: str,
    summary: str,
    description: str,
    auth: str = "lingtu-api-key",
    homepage: str | None = None,
    packages_dir: Path = PACKAGES_DIR,
) -> Path:
    normalized_id = normalize_package_id(package_id)
    if auth not in AUTH_MODES:
        raise ValueError(f"auth 必须是 {', '.join(AUTH_MODES)} 之一")
    for label, value in (
        ("display-name", display_name),
        ("summary", summary),
        ("description", description),
    ):
        if not value.strip():
            raise ValueError(f"{label} 不能为空")

    destination = packages_dir / normalized_id
    if destination.exists():
        raise FileExistsError(f"目标已存在，不会覆盖: {destination}")

    slug = f"lingtu-{normalized_id}"
    resolved_homepage = homepage or f"https://ailingtu.com/skills/{normalized_id}"
    (destination / "agents").mkdir(parents=True)
    (destination / "SKILL.md").write_text(
        skill_markdown(
            slug=slug,
            display_name=display_name.strip(),
            summary=summary.strip(),
            description=description.strip(),
            auth=auth,
            homepage=resolved_homepage,
        ),
        encoding="utf-8",
    )
    (destination / "agents" / "openai.yaml").write_text(
        openai_yaml(slug, display_name.strip(), summary.strip()),
        encoding="utf-8",
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="创建符合灵途认证与独立分发规范的 Skill 包。"
    )
    parser.add_argument("package_id", help="包 ID，例如 creator-insights")
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--auth", choices=AUTH_MODES, default="lingtu-api-key")
    parser.add_argument("--homepage")
    args = parser.parse_args()

    try:
        destination = create_package(
            args.package_id,
            display_name=args.display_name,
            summary=args.summary,
            description=args.description,
            auth=args.auth,
            homepage=args.homepage,
        )
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"[ok] 已创建: {destination}")
    print(f"[next] 完善 SKILL.md 和业务脚本后运行: python3 scripts/build_package.py {destination.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
