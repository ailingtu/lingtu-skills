"""带货图文图片约束：张数、格式、大小、宽高比。"""

from __future__ import annotations

import struct
from pathlib import Path

from .config import (
    IMAGE_EXTENSIONS,
    PHOTO_ASPECT_RATIO_MAX,
    PHOTO_ASPECT_RATIO_MIN,
    PHOTO_MAX_FILE_BYTES,
    PHOTO_MAX_IMAGES,
    PHOTO_MIN_IMAGES,
)

_FORMAT_LABELS = "JPG, JPEG, PNG, WEBP, HEIC, BMP"


def validate_photo_files(paths: list[Path]) -> list[str]:
    """校验图文图片列表，返回错误文案（空列表=通过）。"""
    errors: list[str] = []
    count = len(paths)
    if count < PHOTO_MIN_IMAGES:
        errors.append(f"带货图文至少需要 {PHOTO_MIN_IMAGES} 张图，当前 {count} 张")
        return errors
    if count > PHOTO_MAX_IMAGES:
        errors.append(f"带货图文最多 {PHOTO_MAX_IMAGES} 张图，当前 {count} 张")
        return errors

    for path in paths:
        errors.extend(_validate_one_photo(path))
    return errors


def _validate_one_photo(path: Path) -> list[str]:
    errors: list[str] = []
    name = path.name
    ext = path.suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        errors.append(
            f"{name} 格式不支持（{ext or '无扩展名'}）；支持：{_FORMAT_LABELS}"
        )
        return errors

    try:
        size = path.stat().st_size
    except OSError as exc:
        errors.append(f"{name} 无法读取文件：{exc}")
        return errors

    if size <= 0:
        errors.append(f"{name} 文件为空")
        return errors
    if size > PHOTO_MAX_FILE_BYTES:
        mb = size / (1024 * 1024)
        errors.append(f"{name} 超过 10MB 限制（当前 {mb:.1f}MB）")

    dims = read_image_dimensions(path)
    if dims is None:
        errors.append(
            f"{name} 无法读取宽高（文件可能损坏；HEIC 需安装 Pillow 才能校验比例）"
        )
        return errors

    width, height = dims
    if width <= 0 or height <= 0:
        errors.append(f"{name} 无效尺寸：{width}x{height}")
        return errors

    ratio = width / height
    if ratio < PHOTO_ASPECT_RATIO_MIN or ratio > PHOTO_ASPECT_RATIO_MAX:
        errors.append(
            f"{name} 宽高比 {width}:{height}（{ratio:.3f}）超出允许范围 "
            f"9:16～16:9（{PHOTO_ASPECT_RATIO_MIN:.3f}～{PHOTO_ASPECT_RATIO_MAX:.3f}）"
        )
    return errors


def read_image_dimensions(path: Path) -> tuple[int, int] | None:
    """读取图片宽高。优先 stdlib 解析常见格式；HEIC 等回退 Pillow。"""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 12:
        return None

    ext = path.suffix.lower()
    dims: tuple[int, int] | None = None

    if data[:8] == b"\x89PNG\r\n\x1a\n":
        dims = _png_size(data)
    elif data[:2] == b"\xff\xd8":
        dims = _jpeg_size(data)
    elif data[:2] == b"BM":
        dims = _bmp_size(data)
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        dims = _webp_size(data)
    elif ext in (".heic",) or _looks_like_heic(data):
        dims = _pillow_size(path)

    if dims is None and ext in IMAGE_EXTENSIONS:
        dims = _pillow_size(path)
    return dims


def _png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24:
        return None
    # IHDR: 8 sig + 4 len + 4 type + 4 width + 4 height
    if data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    i = 2
    n = len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        # standalone markers
        if marker in (0xD8, 0xD9) or (0xD0 <= marker <= 0xD7):
            continue
        if i + 2 > n:
            break
        seg_len = struct.unpack(">H", data[i : i + 2])[0]
        if seg_len < 2:
            break
        # SOF0..SOF3, SOF5..SOF7, SOF9..SOF11, SOF13..SOF15 (not DHT etc.)
        if marker in (
            0xC0, 0xC1, 0xC2, 0xC3,
            0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB,
            0xCD, 0xCE, 0xCF,
        ):
            if i + 7 > n:
                return None
            height, width = struct.unpack(">HH", data[i + 3 : i + 7])
            return int(width), int(height)
        i += seg_len
    return None


def _bmp_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 26:
        return None
    # BITMAPINFOHEADER starts at offset 14; width/height at 18/22 (signed)
    width, height = struct.unpack("<ii", data[18:26])
    return int(abs(width)), int(abs(height))


def _webp_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30:
        return None
    chunk = data[12:16]
    if chunk == b"VP8X" and len(data) >= 30:
        # canvas size: 24-bit little-endian minus 1
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return w, h
    if chunk == b"VP8 " and len(data) >= 30:
        # lossy: start code 0x9d 0x01 0x2a then 16-bit width/height
        if data[23:26] == b"\x9d\x01\x2a":
            w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return int(w), int(h)
    if chunk == b"VP8L" and len(data) >= 25:
        # lossless: signature 0x2f then 14-bit w-1 / h-1 packed
        if data[20] != 0x2F:
            return None
        bits = struct.unpack("<I", data[21:25])[0]
        w = (bits & 0x3FFF) + 1
        h = ((bits >> 14) & 0x3FFF) + 1
        return int(w), int(h)
    return None


def _looks_like_heic(data: bytes) -> bool:
    # ftyp box at offset 4
    return len(data) >= 12 and data[4:8] == b"ftyp" and (
        b"heic" in data[8:20] or b"mif1" in data[8:20] or b"msf1" in data[8:20]
    )


def _pillow_size(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return None
    try:
        with Image.open(path) as img:
            w, h = img.size
            return int(w), int(h)
    except Exception:
        return None


def format_photo_constraints_help() -> str:
    """给人看的图文图片约束说明。"""
    return (
        f"带货图文图片要求：{PHOTO_MIN_IMAGES}～{PHOTO_MAX_IMAGES} 张；"
        f"单张 ≤10MB；格式 {_FORMAT_LABELS}；宽高比 9:16～16:9"
    )
