#!/usr/bin/env python3
"""Manage the persistent material-library path for the XHS remake Skill."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def config_path() -> Path:
    return Path.home() / ".config" / "lingtu" / "xhs-remake.json"


def default_material_library() -> Path:
    return Path.home() / "Lingtu" / "xhs-material-library"


def read_config(path: Path | None = None) -> dict[str, Any]:
    target = path or config_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise ValueError(f"无法读取素材库配置 {target}：{exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"素材库配置格式错误：{target}")
    unknown = set(data) - {"materialLibrary"}
    if unknown:
        raise ValueError(f"素材库配置包含未知字段：{', '.join(sorted(unknown))}")
    value = data.get("materialLibrary")
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValueError(f"素材库路径格式错误：{target}")
    return data


def write_config(data: dict[str, Any], path: Path | None = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def set_material_library(value: str, path: Path | None = None) -> Path:
    library = Path(value).expanduser()
    if not library.exists():
        raise ValueError(f"素材库目录不存在：{library}")
    if not library.is_dir():
        raise ValueError(f"素材库路径不是目录：{library}")
    resolved = library.resolve()
    write_config({"materialLibrary": str(resolved)}, path)
    return resolved


def initialize_material_library(
    path: Path | None = None,
    default_library: Path | None = None,
) -> tuple[Path, bool]:
    target = path or config_path()
    data = read_config(target)
    configured = data.get("materialLibrary")
    if configured:
        return Path(configured), False

    library = (default_library or default_material_library()).expanduser()
    if library.exists() and not library.is_dir():
        raise ValueError(f"默认素材库路径不是目录：{library}")
    library.mkdir(parents=True, exist_ok=True)
    resolved = library.resolve()
    write_config({"materialLibrary": str(resolved)}, target)
    return resolved, True


def reset_material_library(path: Path | None = None) -> None:
    target = path or config_path()
    data = read_config(target)
    data.pop("materialLibrary", None)
    if data:
        write_config(data, target)
    else:
        target.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="查看或修改小红书图文复刻素材库路径。")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="首次使用时创建并保存默认素材库；已有配置不覆盖。")
    commands.add_parser("show", help="显示当前素材库路径。")
    set_parser = commands.add_parser("set", help="设置长期素材库路径。")
    set_parser.add_argument("--path", required=True, help="已存在的素材库目录。")
    commands.add_parser("reset", help="清除素材库配置。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = config_path()
    if args.command == "init":
        library, created = initialize_material_library(target)
        print(json.dumps({
            "configPath": str(target),
            "materialLibrary": str(library),
            "exists": library.is_dir(),
            "created": created,
        }, ensure_ascii=False, indent=2))
        return 0
    if args.command == "show":
        data = read_config(target)
        library = data.get("materialLibrary")
        print(json.dumps({
            "configPath": str(target),
            "materialLibrary": library,
            "exists": bool(library and Path(library).is_dir()),
        }, ensure_ascii=False, indent=2))
        return 0
    if args.command == "set":
        library = set_material_library(args.path, target)
        print(json.dumps({
            "configPath": str(target),
            "materialLibrary": str(library),
            "exists": True,
        }, ensure_ascii=False, indent=2))
        return 0
    reset_material_library(target)
    print(json.dumps({
        "configPath": str(target),
        "materialLibrary": None,
        "exists": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
