#!/usr/bin/env python3
"""Build one self-contained Lingtu CDN package and root-level ZIP archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = ROOT / "packages"
SHARED_DIR = ROOT / "shared"
DEFAULT_OUTPUT = ROOT / "dist" / "packages"

PACKAGE_IDS = tuple(
    sorted(path.parent.name for path in PACKAGES_DIR.glob("*/SKILL.md"))
)

EXCLUDED_NAMES = {
    ".DS_Store",
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
    required = ("name", "slug", "version", "displayName", "summary", "description", "license")
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise ValueError(f"{skill_md} 缺少分发必填字段: {', '.join(missing)}")

    validate_skill_name(metadata["name"], skill_md)
    validate_skill_name(metadata["slug"], skill_md)
    if metadata["name"] != metadata["slug"]:
        raise ValueError(f"{skill_md} 的 name 与 slug 必须一致")
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", metadata["version"]):
        raise ValueError(f"{skill_md} 的 version 不是合法 semver: {metadata['version']!r}")


def ignore_entry(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in EXCLUDED_NAMES or name in EXCLUDED_DIRS:
            ignored.add(name)
        elif Path(name).suffix in EXCLUDED_SUFFIXES:
            ignored.add(name)
    return ignored


def patch_content_create_artifact(skill_dir: Path) -> None:
    """Keep the viral-remake flow usable without a second installed Skill."""
    video_script = PACKAGES_DIR / "video-understand" / "scripts" / "lingtu_video_understand.py"
    shutil.copy2(video_script, skill_dir / "scripts" / video_script.name)

    replacements = {
        "run `packages/video-understand` first": (
            "run the bundled `scripts/lingtu_video_understand.py` helper first"
        ),
        "analyze via `packages/video-understand` when a URL is given": (
            "analyze via the bundled `scripts/lingtu_video_understand.py` helper when a URL is given"
        ),
        "first run `packages/video-understand` (`scripts/lingtu_video_understand.py replicate --url ...`)": (
            "first run `python3 scripts/lingtu_video_understand.py replicate --url ...`"
        ),
    }

    for relative_path in ("SKILL.md", "references/viral-remake-workflow.md"):
        target = skill_dir / relative_path
        text = target.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        target.write_text(text, encoding="utf-8")

    remaining = []
    for relative_path in ("SKILL.md", "references/viral-remake-workflow.md"):
        target = skill_dir / relative_path
        if "packages/video-understand" in target.read_text(encoding="utf-8"):
            remaining.append(relative_path)
    if remaining:
        raise ValueError(f"content-create 仍包含外部 video-understand 路径: {remaining}")


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
    skill_name = metadata["name"]

    destination = output / skill_name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=ignore_entry)

    if not (destination / "LICENSE").is_file():
        shutil.copy2(ROOT / "LICENSE", destination / "LICENSE")

    # Existing package scripts search their ancestors for shared/scripts. Keeping
    # it inside each Skill makes the uploaded directory independent of this repo.
    # video-remake intentionally contains its complete runtime in its own scripts.
    if package_id != "video-remake":
        shutil.copytree(SHARED_DIR, destination / "shared", ignore=ignore_entry)

    if package_id == "content-create":
        patch_content_create_artifact(destination)
    patch_portable_documentation(destination)

    if not (destination / "SKILL.md").is_file():
        raise ValueError(f"{destination} 构建后缺少根目录 SKILL.md")

    zip_path = output / f"{skill_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    write_root_level_zip(destination, zip_path)
    validate_zip(zip_path)
    return destination, zip_path


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
    args = parser.parse_args()

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
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
