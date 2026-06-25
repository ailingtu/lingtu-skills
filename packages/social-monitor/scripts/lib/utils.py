"""通用工具函数：环境、时间、格式化、handle 解析。"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

from lingtu_auth import require_api_key as shared_require_api_key

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_PLATFORM,
    DEFAULT_SNAPSHOTS,
    DEFAULT_STORE,
    HASHTAG_PATTERN,
    INSTAGRAM_RESERVED_PATHS,
    PLATFORM_LABELS,
    SUPPORTED_PLATFORMS,
)


def require_api_key() -> str:
    try:
        return shared_require_api_key()
    except SystemExit as exc:
        raise SystemExit(f"{exc}\n请先绑定单用户管理员，或在多用户模式下传入 --channel 和 --user-id。") from exc


def base_url() -> str:
    return os.environ.get("LINGTU_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def store_path() -> Path:
    return Path(
        os.environ.get("LINGTU_SOCIAL_MONITOR_STORE") or str(DEFAULT_STORE)
    ).expanduser()


def snapshots_dir() -> Path:
    return Path(
        os.environ.get("LINGTU_SOCIAL_MONITOR_SNAPSHOTS") or str(DEFAULT_SNAPSHOTS)
    ).expanduser()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_str(value: str | None = None) -> str:
    if value:
        return value
    return now_utc().strftime("%Y-%m-%d")


def normalize_platform(value: str | None) -> str:
    platform = (value or DEFAULT_PLATFORM).strip().lower()
    aliases = {
        "tt": "tiktok",
        "tik tok": "tiktok",
        "ig": "instagram",
        "ins": "instagram",
        "insta": "instagram",
    }
    platform = aliases.get(platform, platform)
    if platform not in SUPPORTED_PLATFORMS:
        raise SystemExit(f"不支持的平台：{value}。可选：{', '.join(SUPPORTED_PLATFORMS)}。")
    return platform


def platform_label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform, platform)


def slugify_handle(value: str) -> str:
    trimmed = re.sub(r"^[^A-Za-z0-9._-]+|[^A-Za-z0-9._-]+$", "", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", trimmed)
    return normalized.lower() or "unknown_creator"


def parse_creator_handle(raw: str, platform: str = DEFAULT_PLATFORM) -> str:
    value = raw.strip()
    if not value:
        raise SystemExit("达人输入不能为空。")

    if platform == "tiktok" and "tiktok.com" in value:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        match = re.search(r"/@([^/?#]+)", parsed.path)
        if match:
            return slugify_handle(match.group(1))
    if platform == "instagram" and "instagram.com" in value:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        parts = [part for part in parsed.path.split("/") if part]
        if parts and parts[0] not in INSTAGRAM_RESERVED_PATHS:
            return slugify_handle(parts[0])
        raise SystemExit(f"无法从 Instagram 链接中识别用户名：{raw}。请直接传 @username 或主页链接。")

    mention = re.search(r"@([A-Za-z0-9._-]+)", value)
    if mention:
        return slugify_handle(mention.group(1))

    return slugify_handle(value)


def stable_id(prefix: str, value: str, length: int = 12) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def iso_utc_from_epoch_seconds(value: int | float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_number(value: int | float | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.2f}"
    return f"{int(value):,}"


def format_delta(value: int | None) -> str:
    if value is None:
        return "-"
    if value > 0:
        return f"+{format_number(value)}"
    if value < 0:
        return f"-{format_number(abs(value))}"
    return "0"


def extract_hashtags(text: str) -> list[str]:
    if not text:
        return []
    return [m.lower() for m in HASHTAG_PATTERN.findall(text)]


def to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        if isinstance(value, str):
            value = value.replace(",", "")
        return int(float(value))
    except (TypeError, ValueError):
        return default


def seconds_from_duration(value: Any) -> float:
    """毫秒（TikTok）或秒（Instagram）→ 秒。>1000 视为毫秒。"""
    if value is None or value == "":
        return 0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if numeric > 1000:
        numeric = numeric / 1000
    return round(numeric, 2)


def cursor_is_empty(cursor: Any) -> bool:
    if cursor is None:
        return True
    if isinstance(cursor, str):
        return cursor == ""
    if isinstance(cursor, (dict, list)):
        return not cursor
    return False
