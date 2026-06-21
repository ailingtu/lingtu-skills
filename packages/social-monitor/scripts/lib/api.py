"""HTTP 调用与评论翻页聚合。"""

from __future__ import annotations

import json
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .config import (
    DEFAULT_PLATFORM,
    FETCH_MATERIAL_COMMENTS_PATH,
    FETCH_MATERIAL_PATH,
    FETCH_POSTS_PATH,
    INS_FETCH_MATERIAL_COMMENTS_PATH,
    INS_FETCH_MATERIAL_PATH,
    INS_FETCH_POSTS_PATH,
)
from .utils import (
    base_url,
    cursor_is_empty,
    normalize_platform,
    platform_label,
    require_api_key,
)


def fetch_posts(unique_id: str, count: int, platform: str = DEFAULT_PLATFORM) -> dict[str, Any]:
    platform = normalize_platform(platform)
    api_key = require_api_key()
    query = urllib_parse.urlencode({"uniqueId": unique_id, "count": max(1, count)})
    path = INS_FETCH_POSTS_PATH if platform == "instagram" else FETCH_POSTS_PATH
    url = f"{base_url()}{path}?{query}"
    req = urllib_request.Request(url, method="GET")
    req.add_header("x-api-key", api_key)
    req.add_header("Accept", "application/json")
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        raise SystemExit(f"fetchPosts({platform}) HTTP 错误：{exc.code} {exc.reason}")
    except urllib_error.URLError as exc:
        raise SystemExit(f"fetchPosts({platform}) 网络错误：{exc.reason}")

    code = payload.get("code")
    if code == 0 and isinstance(payload.get("data"), dict):
        return payload["data"]

    message = payload.get("message") or "未知错误"
    if code == -1:
        raise SystemExit(f"未获取到该达人数据：{message}（uniqueId={unique_id}）")
    raise SystemExit(f"fetchPosts({platform}) 调用失败 (code={code})：{message}")


def post_json(path: str, body: dict[str, Any], label: str, timeout: int = 60) -> dict[str, Any]:
    api_key = require_api_key()
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib_request.Request(f"{base_url()}{path}", data=payload, method="POST")
    req.add_header("x-api-key", api_key)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        raise SystemExit(f"{label} HTTP 错误：{exc.code} {exc.reason}")
    except urllib_error.URLError as exc:
        raise SystemExit(f"{label} 网络错误：{exc.reason}")

    code = result.get("code")
    if code == 0 and isinstance(result.get("data"), dict):
        return result

    message = result.get("message") or "未知错误"
    raise SystemExit(f"{label} 调用失败 (code={code})：{message}")


def fetch_material(video_url: str, platform: str = DEFAULT_PLATFORM) -> dict[str, Any]:
    platform = normalize_platform(platform)
    path = INS_FETCH_MATERIAL_PATH if platform == "instagram" else FETCH_MATERIAL_PATH
    return post_json(path, {"videoUrl": video_url}, f"fetch{platform_label(platform)}Material")


def fetch_material_comments_page(
    video_url: str,
    cursor: Any = None,
    platform: str = DEFAULT_PLATFORM,
    sort_order: str = "popular",
) -> dict[str, Any]:
    platform = normalize_platform(platform)
    path = INS_FETCH_MATERIAL_COMMENTS_PATH if platform == "instagram" else FETCH_MATERIAL_COMMENTS_PATH
    body: dict[str, Any] = {"videoUrl": video_url}
    if platform == "instagram":
        body["sortOrder"] = sort_order
    if cursor is not None and cursor != "":
        body["cursor"] = cursor
    return post_json(path, body, f"fetch{platform_label(platform)}MaterialComments")


def extract_comments_cursor(payload: dict[str, Any]) -> Any:
    """IG 返回 dict cursor（cached_comments_cursor / bifilter_token），原样传回；TikTok 是字符串。"""
    data = payload.get("data") or {}
    if data.get("cursor") is not None:
        return data["cursor"]
    return payload.get("cursor")


def has_more_comments(payload: dict[str, Any], next_cursor: Any) -> bool:
    data = payload.get("data") or {}
    if "hasMore" in data:
        return bool(data["hasMore"])
    if "hasMore" in payload:
        return bool(payload["hasMore"])
    return not cursor_is_empty(next_cursor)


def fetch_material_comments(
    video_url: str,
    *,
    platform: str = DEFAULT_PLATFORM,
    sort_order: str = "popular",
    cursor: Any = None,
    max_pages: int | None = None,
    fetch_all: bool = True,
) -> dict[str, Any]:
    comments: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    next_cursor = cursor
    last_payload: dict[str, Any] | None = None
    page_index = 0

    while True:
        payload = fetch_material_comments_page(
            video_url,
            next_cursor,
            platform=platform,
            sort_order=sort_order,
        )
        last_payload = payload
        data = payload.get("data") or {}
        page_comments = data.get("comments") or []
        if not isinstance(page_comments, list):
            page_comments = []
        comments.extend(page_comments)

        returned_cursor = extract_comments_cursor(payload)
        pages.append({
            "cursor": next_cursor,
            "next_cursor": returned_cursor,
            "comment_count": len(page_comments),
        })

        page_index += 1
        if not fetch_all:
            break
        if max_pages is not None and page_index >= max_pages:
            break
        if not has_more_comments(payload, returned_cursor):
            break
        if cursor_is_empty(returned_cursor) or returned_cursor == next_cursor:
            break
        next_cursor = returned_cursor

    if last_payload is None:
        return {"code": 0, "message": "success", "data": {"comments": [], "pages": []}, "timestamp": None}

    aggregated = dict(last_payload)
    data = dict(last_payload.get("data") or {})
    data["comments"] = comments
    data["pages"] = pages
    last_cursor = pages[-1]["next_cursor"] if pages else None
    data["cursor"] = last_cursor
    data["hasMore"] = bool(pages and has_more_comments(last_payload, last_cursor) and not cursor_is_empty(last_cursor))
    aggregated["data"] = data
    return aggregated
