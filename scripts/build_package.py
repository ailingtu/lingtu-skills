#!/usr/bin/env python3
"""Build one self-contained Lingtu CDN package and root-level ZIP archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
from datetime import datetime, timedelta, timezone
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = ROOT / "packages"
SHARED_DIR = ROOT / "shared"
DEFAULT_OUTPUT = ROOT / "dist" / "packages"
AUTH_MODES = {"lingtu-api-key", "none"}

PACKAGE_IDS = tuple(
    sorted(path.parent.name for path in PACKAGES_DIR.glob("*/SKILL.md"))
)

EXCLUDED_NAMES = {
    ".DS_Store",
    "LICENSE",
    "README.md",
    "Thumbs.db",
}
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "tests",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", text, re.DOTALL)
    if not match:
        raise ValueError(f"{skill_md} 缺少合法的 YAML frontmatter")

    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in {
            "name",
            "slug",
            "version",
            "auth",
            "displayName",
            "summary",
            "description",
            "license",
            "homepage",
        }:
            values[key.strip()] = value.strip().strip('"\'')
    return values


def validate_skill_name(name: str, skill_md: Path) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"{skill_md} 的 name 不是合法 kebab-case: {name!r}")


def validate_metadata(metadata: dict[str, str], skill_md: Path) -> None:
    required = ("name", "slug", "version", "auth", "displayName", "summary", "description", "license")
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise ValueError(f"{skill_md} 缺少分发必填字段: {', '.join(missing)}")

    validate_skill_name(metadata["name"], skill_md)
    validate_skill_name(metadata["slug"], skill_md)
    if metadata["name"] != metadata["slug"]:
        raise ValueError(f"{skill_md} 的 name 与 slug 必须一致")
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", metadata["version"]):
        raise ValueError(f"{skill_md} 的 version 不是合法 semver: {metadata['version']!r}")
    if metadata["auth"] not in AUTH_MODES:
        raise ValueError(
            f"{skill_md} 的 auth 必须是 {', '.join(sorted(AUTH_MODES))} 之一: "
            f"{metadata['auth']!r}"
        )


def validate_auth_instructions(metadata: dict[str, str], skill_md: Path) -> None:
    if metadata["auth"] != "lingtu-api-key":
        return
    text = skill_md.read_text(encoding="utf-8")
    required_fragments = (
        "LINGTU_API_KEY",
        "x-api-key",
        "https://ailingtu.com/api-keys",
        "shared/references/api-key-setup.md",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        raise ValueError(
            f"{skill_md} 缺少灵途 API Key 配置说明: {', '.join(missing)}"
        )


def ignore_entry(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in EXCLUDED_NAMES or name in EXCLUDED_DIRS:
            ignored.add(name)
        elif Path(name).suffix in EXCLUDED_SUFFIXES:
            ignored.add(name)
    return ignored


def bundle_content_understand_helpers(skill_dir: Path) -> None:
    """Bundle video analysis for reference-based generation without sibling Skills."""
    shutil.copy2(PACKAGES_DIR / "video-understand/scripts/lingtu_video_understand.py",
                 skill_dir / "scripts/lingtu_video_understand.py")
    shutil.copy2(PACKAGES_DIR / "video-understand/references/api.md",
                 skill_dir / "references/video-understand-api.md")
    target = skill_dir / "references/viral-remake-workflow.md"
    text = target.read_text(encoding="utf-8")
    text = text.replace("../../video-understand/references/api.md", "video-understand-api.md")
    text = text.replace("../video-understand/scripts/", "scripts/")
    target.write_text(text, encoding="utf-8")


def patch_portable_documentation(skill_dir: Path) -> None:
    """Make repository-root examples valid from an installed Skill root."""
    for target in skill_dir.rglob("*.md"):
        text = target.read_text(encoding="utf-8")
        portable = text.replace("../../shared/scripts/", "shared/scripts/")
        if portable != text:
            target.write_text(portable, encoding="utf-8")


def iter_files(directory: Path):
    for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_file():
            yield path


def write_root_level_zip(skill_dir: Path, zip_path: Path) -> None:
    """Write entries relative to skill_dir so SKILL.md is at the ZIP root."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in iter_files(skill_dir):
            relative = path.relative_to(skill_dir).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2020, 1, 1, 0, 0, 0))
            mode = path.stat().st_mode
            permissions = 0o755 if mode & stat.S_IXUSR else 0o644
            info.external_attr = (stat.S_IFREG | permissions) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def validate_zip(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if "SKILL.md" not in names:
            raise ValueError(f"{zip_path} 的 ZIP 根目录没有 SKILL.md")
        if any(name.startswith("__MACOSX/") or "/.DS_Store" in name for name in names):
            raise ValueError(f"{zip_path} 包含 macOS 垃圾文件")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_package(package_id: str, output: Path) -> tuple[Path, Path]:
    source = PACKAGES_DIR / package_id
    skill_md = source / "SKILL.md"
    if not skill_md.is_file():
        raise ValueError(f"{source} 缺少 SKILL.md")

    metadata = parse_frontmatter(skill_md)
    validate_metadata(metadata, skill_md)
    validate_auth_instructions(metadata, skill_md)
    skill_name = metadata["name"]

    destination = output / skill_name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=ignore_entry)

    # Authentication behavior is declared by SKILL.md rather than inferred from
    # a package name, so future API and public-only Skills follow the same path.
    if metadata["auth"] == "lingtu-api-key":
        shutil.copytree(SHARED_DIR, destination / "shared", ignore=ignore_entry)
    elif (destination / "shared").exists():
        raise ValueError(f"{skill_md} 声明 auth: none，但包内包含 shared 认证运行时")

    if package_id == "content-create":
        bundle_content_understand_helpers(destination)
    patch_portable_documentation(destination)

    if not (destination / "SKILL.md").is_file():
        raise ValueError(f"{destination} 构建后缺少根目录 SKILL.md")
    if metadata["auth"] == "lingtu-api-key":
        for relative_path in (
            "shared/scripts/lingtu_auth.py",
            "shared/references/api-key-setup.md",
        ):
            if not (destination / relative_path).is_file():
                raise ValueError(f"{destination} 构建后缺少认证运行时: {relative_path}")

    zip_path = output / f"{skill_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    write_root_level_zip(destination, zip_path)
    validate_zip(zip_path)
    return destination, zip_path



TABLE_START = "<!-- skills-table:start -->"
TABLE_END = "<!-- skills-table:end -->"


def table_cell(value: str) -> str:
    """Keep metadata and names inside a single Markdown table cell."""
    return " ".join(value.split()).replace("|", "&#124;").replace("<", "&lt;").replace(">", "&gt;")


def prepare_readme_update(package_id: str, metadata: dict[str, str], owner: str | None,
                          readme: Path, now: datetime | None = None) -> str:
    text = readme.read_text(encoding="utf-8")
    if text.count(TABLE_START) != 1 or text.count(TABLE_END) != 1:
        raise ValueError("README.md 必须包含唯一的 skills-table 起止标记")
    start = text.index(TABLE_START) + len(TABLE_START)
    end = text.index(TABLE_END)
    if end <= start:
        raise ValueError("README.md 的 skills-table 标记顺序错误")
    lines = text[start:end].strip().splitlines()
    prefix = f"| [`{package_id}`](packages/{package_id}/) |"
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) > 1:
        raise ValueError(f"README.md 重复登记了 {package_id}")
    index = matches[0] if matches else None
    cells = [cell.strip() for cell in lines[index].strip("|").split("|")] if index is not None else None
    if cells is not None and len(cells) != 5:
        raise ValueError(f"README.md 中 {package_id} 必须有五列")
    existing_owner = cells[4] if cells else ""
    if owner is not None:
        if not owner.strip():
            raise ValueError("--owner 不能为空")
        resolved_owner = table_cell(owner)
    elif existing_owner and existing_owner != "待指定":
        resolved_owner = existing_owner
    else:
        result = subprocess.run(["git", "config", "user.name"], cwd=readme.parent,
                                capture_output=True, text=True, check=False)
        if result.returncode != 0 or not result.stdout.strip():
            raise ValueError("首次打包请通过 --owner 指定负责人，或配置 Git user.name")
        resolved_owner = table_cell(result.stdout)
    timestamp = (now or datetime.now(timezone.utc)).astimezone(
        timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    description = cells[1] if cells else table_cell(metadata["summary"])
    row = f"{prefix} {description} | {table_cell(metadata['version'])} | {timestamp} | {resolved_owner} |"
    if index is None:
        lines.append(row)
    else:
        lines[index] = row
    return text[:start] + "\n" + "\n".join(lines) + "\n" + text[end:]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="构建可分别上传到灵途 TOS/CDN 的自包含 Skill 目录和 ZIP。"
    )
    parser.add_argument(
        "package",
        choices=PACKAGE_IDS,
        help="要构建的单个 Skill。每次只生成一个独立发布物。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"输出目录，默认 {DEFAULT_OUTPUT}",
    )
    parser.add_argument("--owner", help="负责人；默认保留已有负责人，首次打包读取 Git user.name")
    args = parser.parse_args()

    readme = ROOT / "README.md"
    source_metadata = parse_frontmatter(PACKAGES_DIR / args.package / "SKILL.md")
    # Validate the table and owner before producing artifacts.
    prepare_readme_update(args.package, source_metadata, args.owner, readme)

    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    directory, archive = build_package(args.package, output)
    print(f"[ok] 目录: {directory}")
    print(f"[ok] ZIP:  {archive}（根目录含 SKILL.md）")

    archive_sha256 = sha256(archive)
    checksum_file = archive.with_suffix(".zip.sha256")
    checksum_file.write_text(f"{archive_sha256}  {archive.name}\n", encoding="utf-8")
    print(f"[ok] 校验: {checksum_file}")

    metadata = parse_frontmatter(directory / "SKILL.md")
    metadata_file = archive.with_suffix(".metadata.json")
    metadata_file.write_text(
        json.dumps(
            {
                "name": metadata["name"],
                "slug": metadata["slug"],
                "displayName": metadata["displayName"],
                "summary": metadata["summary"],
                "version": metadata["version"],
                "auth": metadata["auth"],
                "sha256": archive_sha256,
                "bytes": archive.stat().st_size,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[ok] 索引元数据: {metadata_file}")
    updated_readme = prepare_readme_update(args.package, metadata, args.owner, readme)
    readme.write_text(updated_readme, encoding="utf-8")
    print(f"[ok] README: 已同步 {args.package} 的版本、更新时间和负责人")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
