"""HTTP 调用与评论翻页聚合。"""

from __future__ import annotations

from typing import Any

from .config import (
    DEFAULT_PLATFORM,
    FETCH_MATERIAL_PATH,
    FETCH_POSTS_PATH,
    INS_FETCH_MATERIAL_PATH,
    INS_FETCH_POSTS_PATH,
)
from .utils import (  # noqa: I001 — utils inserts shared/scripts onto sys.path
    normalize_platform,
    platform_label,
)
from lingtu_http import LingtuHttpError, raise_system_exit, request_json


def fetch_posts(
    unique_id: str,
    count: int,
    platform: str = DEFAULT_PLATFORM,
    timeout: int = 30,
) -> dict[str, Any]:
    platform = normalize_platform(platform)
    path = INS_FETCH_POSTS_PATH if platform == "instagram" else FETCH_POSTS_PATH
    label = f"fetchPosts({platform})"
    try:
        payload = request_json(
            "GET",
            path,
            query={"uniqueId": unique_id, "count": max(1, count)},
            timeout=timeout,
        )
    except LingtuHttpError as exc:
        raise_system_exit(exc, label)

    if not isinstance(payload, dict):
        raise SystemExit(f"{label} 调用失败：响应不是 JSON 对象")

    code = payload.get("code")
    if code == 0 and isinstance(payload.get("data"), dict):
        return payload["data"]

    message = payload.get("message") or "未知错误"
    if code == -1:
        raise SystemExit(f"未获取到该达人数据：{message}（uniqueId={unique_id}）")
    raise SystemExit(f"{label} 调用失败 (code={code})：{message}")


def post_json(path: str, body: dict[str, Any], label: str, timeout: int = 60) -> dict[str, Any]:
    try:
        result = request_json("POST", path, body=body, timeout=timeout)
    except LingtuHttpError as exc:
        raise_system_exit(exc, label)

    if not isinstance(result, dict):
        raise SystemExit(f"{label} 调用失败：响应不是 JSON 对象")

    code = result.get("code")
    if code == 0 and isinstance(result.get("data"), dict):
        return result

    message = result.get("message") or "未知错误"
    raise SystemExit(f"{label} 调用失败 (code={code})：{message}")


def fetch_material(video_url: str, platform: str = DEFAULT_PLATFORM) -> dict[str, Any]:
    platform = normalize_platform(platform)
    path = INS_FETCH_MATERIAL_PATH if platform == "instagram" else FETCH_MATERIAL_PATH
    return post_json(path, {"videoUrl": video_url}, f"fetch{platform_label(platform)}Material")
