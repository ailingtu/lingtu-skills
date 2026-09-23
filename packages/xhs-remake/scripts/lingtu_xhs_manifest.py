#!/usr/bin/env python3
"""Build a deterministic technical inventory for Xiaohongshu remake inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import BinaryIO


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif", ".avif"}
IGNORED_DIRS = {".git", ".svn", "__MACOSX", "__pycache__", "node_modules"}
IGNORED_FILES = {".DS_Store", "Thumbs.db"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jpeg_size(stream: BinaryIO) -> tuple[int, int] | None:
    stream.seek(2)
    while True:
        marker_start = stream.read(1)
        if not marker_start:
            return None
        if marker_start != b"\xff":
            continue
        marker = stream.read(1)
        while marker == b"\xff":
            marker = stream.read(1)
        if not marker or marker in {b"\xd8", b"\xd9"}:
            continue
        length_bytes = stream.read(2)
        if len(length_bytes) != 2:
            return None
        length = struct.unpack(">H", length_bytes)[0]
        if length < 2:
            return None
        if marker[0] in {
            0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
        }:
            payload = stream.read(5)
            if len(payload) != 5:
                return None
            height, width = struct.unpack(">HH", payload[1:])
            return width, height
        stream.seek(length - 2, os.SEEK_CUR)


def image_size(path: Path) -> tuple[int, int] | None:
    """Read dimensions for common formats without third-party dependencies."""
    try:
        with path.open("rb") as stream:
            header = stream.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                width, height = struct.unpack(">II", header[16:24])
                return width, height
            if header[:6] in {b"GIF87a", b"GIF89a"} and len(header) >= 10:
                return struct.unpack("<HH", header[6:10])
            if header.startswith(b"\xff\xd8"):
                return _jpeg_size(stream)
            if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
                kind = header[12:16]
                if kind == b"VP8X" and len(header) >= 30:
                    width = 1 + int.from_bytes(header[24:27], "little")
                    height = 1 + int.from_bytes(header[27:30], "little")
                    return width, height
                if kind == b"VP8L" and len(header) >= 25:
                    bits = int.from_bytes(header[21:25], "little")
                    return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    except (OSError, ValueError, struct.error):
        return None
    return None


def iter_images(source: Path):
    if source.is_symlink():
        return
    if source.is_file():
        if source.name not in IGNORED_FILES and source.suffix.lower() in IMAGE_SUFFIXES:
            yield source
        return
    if not source.is_dir():
        return
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix().lower()):
        if any(part in IGNORED_DIRS or part.startswith(".") for part in path.relative_to(source).parts[:-1]):
            continue
        if path.is_symlink() or not path.is_file() or path.name in IGNORED_FILES:
            continue
        if path.suffix.lower() in IMAGE_SUFFIXES:
            yield path


def collect_sources(values: list[str]) -> tuple[list[Path], list[str]]:
    images: list[Path] = []
    warnings: list[str] = []
    seen_paths: set[Path] = set()
    for raw in values:
        source = Path(raw).expanduser()
        if not source.exists():
            warnings.append(f"素材路径不存在：{source}")
            continue
        found = False
        for path in iter_images(source):
            found = True
            resolved = path.resolve()
            if resolved not in seen_paths:
                seen_paths.add(resolved)
                images.append(resolved)
        if not found:
            warnings.append(f"没有在路径中找到支持的图片：{source}")
    return images, warnings


def asset_record(path: Path, digest_owner: dict[str, str]) -> dict[str, object]:
    digest = sha256(path)
    dimensions = image_size(path)
    duplicate_of = digest_owner.get(digest)
    if duplicate_of is None:
        digest_owner[digest] = str(path)
    return {
        "path": str(path),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "bytes": path.stat().st_size,
        "sha256": digest,
        "width": dimensions[0] if dimensions else None,
        "height": dimensions[1] if dimensions else None,
        "duplicateOf": duplicate_of,
        "analysis": {
            "status": "pending_visual_analysis",
            "type": [],
            "subjects": [],
            "usableFor": [],
            "visualStyle": {},
            "textSpace": None,
            "quality": None,
            "constraints": [],
            "summary": None,
        },
    }


def build_manifest(values: list[str]) -> dict[str, object]:
    images, warnings = collect_sources(values)
    digest_owner: dict[str, str] = {}
    assets = [asset_record(path, digest_owner) for path in images]
    return {
        "schemaVersion": 1,
        "sourcePaths": [str(Path(value).expanduser().resolve()) for value in values],
        "assetCount": len(assets),
        "uniqueAssetCount": sum(asset["duplicateOf"] is None for asset in assets),
        "warnings": warnings,
        "assets": assets,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="扫描小红书图文复刻素材并生成技术清单。")
    parser.add_argument(
        "--material",
        action="append",
        required=True,
        help="素材文件或文件夹；可重复传入。文件夹会递归扫描。",
    )
    parser.add_argument("--output", required=True, help="输出 JSON 文件路径。")
    parser.add_argument("--force", action="store_true", help="覆盖已有输出。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output).expanduser()
    if output.exists() and not args.force:
        raise SystemExit(f"文件已存在：{output}。确认覆盖后再加 --force。")
    manifest = build_manifest(args.material)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "savedManifest": str(output.resolve()),
        "assetCount": manifest["assetCount"],
        "uniqueAssetCount": manifest["uniqueAssetCount"],
        "warnings": manifest["warnings"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
