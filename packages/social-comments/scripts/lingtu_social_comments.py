#!/usr/bin/env python3
"""Download social-video comments through Lingtu AI."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_BASE_URL = "https://api.ailingtu.com"
DEFAULT_RETRIES = 2
DEFAULT_RETRY_SLEEP_MS = 1500
DEFAULT_PAGE_SLEEP_MS = 500
ENDPOINTS = {
    "tiktok": "/v1/material/tiktok/fetchComments",
    "instagram": "/v1/material/ins/fetchComments",
    "douyin": "/v1/material/douyin/fetchComments",
    "wechat-channel": "/v1/material/wechatChannel/fetchComments",
    "xiaohongshu": "/v1/material/xhs/fetchComments",
}
PLATFORM_ALIASES = {
    "tiktok": "tiktok",
    "instagram": "instagram",
    "ins": "instagram",
    "douyin": "douyin",
    "wechat-channel": "wechat-channel",
    "wechatchannel": "wechat-channel",
    "wechat_channel": "wechat-channel",
    "channels": "wechat-channel",
    "xiaohongshu": "xiaohongshu",
    "xhs": "xiaohongshu",
    "rednote": "xiaohongshu",
}


def require_api_key() -> str:
    key = os.environ.get("LINGTU_API_KEY", "").strip()
    if not key:
        if platform.system() == "Windows":
            hint = (
                '请在 PowerShell 执行 `$env:LINGTU_API_KEY = "your-api-key"`（当前窗口），'
                '或执行 `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")` '
                "后重新打开终端。"
            )
        else:
            hint = (
                "请在终端执行 `export LINGTU_API_KEY='your-api-key'`。"
                "macOS 如需永久生效，请把该行加入 `~/.zshrc`，再执行 `source ~/.zshrc`。"
            )
        raise SystemExit(f"LINGTU_API_KEY 环境变量未设置。{hint}")
    return key


def base_url() -> str:
    return os.environ.get("LINGTU_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def infer_platform(video_url: str) -> str:
    parsed = urlparse(video_url)
    host = (parsed.hostname or "").lower()
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return "instagram"
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        return "tiktok"
    if host == "douyin.com" or host.endswith(".douyin.com") or host.endswith(".iesdouyin.com"):
        return "douyin"
    if host == "channels.weixin.qq.com" or (
        host == "weixin.qq.com" and parsed.path.startswith("/sph/")
    ):
        return "wechat-channel"
    if (
        host == "xiaohongshu.com"
        or host.endswith(".xiaohongshu.com")
        or host == "xhslink.com"
        or host.endswith(".xhslink.com")
    ):
        return "xiaohongshu"
    raise SystemExit(
        "无法根据链接识别平台，请显式传 --platform "
        "tiktok、instagram、douyin、wechat-channel 或 xiaohongshu。"
    )


def normalize_platform(value: str | None, video_url: str) -> str:
    if value is None:
        return infer_platform(video_url)
    normalized = PLATFORM_ALIASES.get(value.strip().lower())
    if normalized is None:
        supported = "、".join(ENDPOINTS)
        raise SystemExit(f"不支持的平台：{value}。当前支持：{supported}。")
    return normalized


def post_json(
    path: str,
    body: dict[str, Any],
    timeout: int,
    *,
    retries: int,
    retry_sleep_ms: int,
) -> dict[str, Any]:
    url = f"{base_url()}{path}"
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": require_api_key(),
        },
        method="POST",
    )
    raw = ""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            transient = exc.code == 429 or exc.code >= 500
            if not transient or attempt >= retries:
                raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
            wait_seconds = retry_sleep_ms * (2**attempt) / 1000
            sys.stderr.write(
                f"请求暂时失败 (HTTP {exc.code})，{wait_seconds:g} 秒后重试 "
                f"({attempt + 1}/{retries})。\n"
            )
            time.sleep(wait_seconds)
        except urllib.error.URLError as exc:
            if attempt >= retries:
                raise SystemExit(f"请求 {url} 失败：{exc.reason}") from exc
            wait_seconds = retry_sleep_ms * (2**attempt) / 1000
            sys.stderr.write(
                f"网络请求失败，{wait_seconds:g} 秒后重试 "
                f"({attempt + 1}/{retries})：{exc.reason}\n"
            )
            time.sleep(wait_seconds)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"接口返回的不是有效 JSON：{raw[:500]}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("接口响应不是 JSON 对象。")
    if payload.get("code") != 0 or not isinstance(payload.get("data"), dict):
        message = payload.get("message") or "未知错误"
        raise SystemExit(f"评论接口调用失败 (code={payload.get('code')})：{message}")
    return payload


def cursor_is_empty(cursor: Any) -> bool:
    if cursor is None:
        return True
    if isinstance(cursor, str):
        return cursor == ""
    if isinstance(cursor, (dict, list)):
        return not cursor
    return False


def response_cursor(payload: dict[str, Any]) -> Any:
    data = payload.get("data") or {}
    if data.get("cursor") is not None:
        return data["cursor"]
    return payload.get("cursor")


def response_has_more(payload: dict[str, Any], cursor: Any) -> bool:
    data = payload.get("data") or {}
    if "hasMore" in data:
        return bool(data["hasMore"])
    if "hasMore" in payload:
        return bool(payload["hasMore"])
    return not cursor_is_empty(cursor)


def comment_identity(item: dict[str, Any], platform: str) -> str | None:
    keys = {
        "tiktok": ("cid", "comment_id", "id"),
        "instagram": ("pk", "id", "comment_id"),
        "douyin": ("cid", "commentId", "comment_id", "id"),
        "wechat-channel": ("commentId", "comment_id", "id", "cid"),
        "xiaohongshu": ("id", "commentId", "comment_id", "cid"),
    }[platform]
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return f"{platform}:{value}"
    return None


def fetch_comments(
    video_url: str,
    *,
    platform: str,
    sort_order: str,
    cursor: Any,
    max_pages: int | None,
    max_comments: int | None,
    first_page: bool,
    timeout: int,
    retries: int,
    retry_sleep_ms: int,
    sleep_ms: int,
    dedupe: bool,
    progress: bool,
) -> dict[str, Any]:
    comments: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    next_cursor = cursor
    last_payload: dict[str, Any] | None = None
    seen_ids: set[str] = set()
    duplicate_count = 0
    stopped_reason = "no_more"

    while True:
        body: dict[str, Any] = {"videoUrl": video_url}
        if platform == "instagram":
            body["sortOrder"] = sort_order
        if not cursor_is_empty(next_cursor):
            body["cursor"] = next_cursor

        payload = post_json(
            ENDPOINTS[platform],
            body,
            timeout,
            retries=retries,
            retry_sleep_ms=retry_sleep_ms,
        )
        last_payload = payload
        data = payload.get("data") or {}
        page_comments = data.get("comments") or []
        if not isinstance(page_comments, list):
            page_comments = []
        page_items = [item for item in page_comments if isinstance(item, dict)]
        added_count = 0
        page_duplicate_count = 0
        for item in page_items:
            identity = comment_identity(item, platform) if dedupe else None
            if identity is not None and identity in seen_ids:
                duplicate_count += 1
                page_duplicate_count += 1
                continue
            if identity is not None:
                seen_ids.add(identity)
            comments.append(item)
            added_count += 1
        returned_cursor = response_cursor(payload)
        pages.append({
            "cursor": next_cursor,
            "next_cursor": returned_cursor,
            "comment_count": len(page_comments),
            "added_count": added_count,
            "duplicate_count": page_duplicate_count,
        })

        if progress:
            sys.stderr.write(
                f"已获取第 {len(pages)} 页：本页 {len(page_items)} 条，"
                f"累计 {len(comments)} 条。\n"
            )

        if max_comments is not None and len(comments) >= max_comments:
            del comments[max_comments:]
            stopped_reason = "max_comments"
            break
        if not response_has_more(payload, returned_cursor):
            stopped_reason = "no_more"
            break
        if first_page:
            stopped_reason = "first_page"
            break
        if max_pages is not None and len(pages) >= max_pages:
            stopped_reason = "max_pages"
            break
        if cursor_is_empty(returned_cursor):
            stopped_reason = "empty_cursor"
            break
        if returned_cursor == next_cursor:
            stopped_reason = "repeated_cursor"
            break
        next_cursor = returned_cursor
        if sleep_ms:
            time.sleep(sleep_ms / 1000)

    if last_payload is None:
        return {"code": 0, "message": "success", "data": {"comments": [], "pages": []}}
    aggregated = dict(last_payload)
    data = dict(last_payload.get("data") or {})
    data["comments"] = comments
    data["pages"] = pages
    last_cursor = pages[-1]["next_cursor"] if pages else None
    data["cursor"] = last_cursor
    data["hasMore"] = bool(
        pages and response_has_more(last_payload, last_cursor) and not cursor_is_empty(last_cursor)
    )
    data["duplicateCount"] = duplicate_count
    data["stoppedReason"] = stopped_reason
    aggregated["data"] = data
    return aggregated


def to_int(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ""))) if value not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def iso_utc(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError, OverflowError):
        return str(value)


def first_value(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return None


def first_avatar_url(user: dict[str, Any]) -> str:
    direct = first_value(user, "avatar_url", "avatarUrl", "headUrl", "profilePicUrl", "images")
    if direct:
        return str(direct)
    for key in ("avatarThumb", "avatar_thumb"):
        avatar = user.get(key)
        if not isinstance(avatar, dict):
            continue
        urls = avatar.get("urlList") or avatar.get("url_list") or []
        if isinstance(urls, list) and urls:
            return str(urls[0])
    return ""


def normalize_comment(item: dict[str, Any], platform: str) -> dict[str, Any]:
    user = item.get("user") or {}
    if not isinstance(user, dict):
        user = {}
    if platform == "instagram":
        return {
            "platform": "instagram",
            "comment_id": str(first_value(item, "pk", "id", "comment_id") or ""),
            "video_id": "",
            "text": str(item.get("text") or ""),
            "language": None,
            "created_at": iso_utc(item.get("createdAt") or item.get("createdAtUtc")),
            "like_count": to_int(item.get("commentLikeCount")),
            "author_pinned": False,
            "author_liked": bool(item.get("isLikedByMediaOwner")),
            "reply_id": "",
            "reply_comment": item.get("previewChildComments"),
            "hidden": False,
            "child_comment_count": to_int(item.get("childCommentCount")),
            "user": {
                "uid": str(user.get("pk") or ""),
                "unique_id": str(user.get("username") or ""),
                "nickname": str(user.get("fullName") or ""),
                "avatar_url": first_avatar_url(user),
                "tags": None,
            },
        }
    if platform == "tiktok":
        return {
            "platform": platform,
            "comment_id": str(first_value(item, "cid", "comment_id", "id") or ""),
            "video_id": str(item.get("aweme_id") or ""),
            "text": item.get("text") or "",
            "language": item.get("comment_language"),
            "created_at": iso_utc(item.get("create_time")),
            "like_count": to_int(item.get("digg_count")),
            "author_pinned": bool(item.get("author_pin")),
            "author_liked": bool(item.get("is_author_digged")),
            "reply_id": str(item.get("reply_id") or ""),
            "reply_comment": item.get("reply_comment"),
            "hidden": bool(item.get("no_show")),
            "user": {
                "uid": str(user.get("uid") or ""),
                "unique_id": user.get("unique_id") or "",
                "nickname": user.get("nickname") or "",
                "avatar_url": first_avatar_url(user),
                "tags": user.get("user_tags"),
            },
        }
    if platform == "douyin":
        return {
            "platform": platform,
            "comment_id": str(first_value(item, "cid", "commentId", "id") or ""),
            "video_id": str(first_value(item, "awemeId", "aweme_id") or ""),
            "text": str(item.get("text") or ""),
            "language": item.get("commentLanguage"),
            "created_at": iso_utc(first_value(item, "createTime", "create_time")),
            "like_count": to_int(first_value(item, "diggCount", "digg_count")),
            "author_pinned": bool(first_value(item, "isPinned", "authorPin")),
            "author_liked": bool(first_value(item, "isAuthorDigged", "is_author_digged")),
            "reply_id": str(first_value(item, "replyId", "reply_id") or ""),
            "reply_to_reply_id": str(first_value(item, "replyToReplyId", "reply_to_reply_id") or ""),
            "reply_count": to_int(first_value(item, "replyCommentTotal", "reply_count")),
            "hidden": bool(first_value(item, "isFolded", "no_show")),
            "is_hot": bool(item.get("isHot")),
            "ip_region": first_value(item, "ipLabel", "ipRegion"),
            "content_type": item.get("contentType"),
            "image_list": item.get("imageList"),
            "user": {
                "uid": str(first_value(user, "uid", "id") or ""),
                "sec_uid": str(first_value(user, "secUid", "sec_uid") or ""),
                "unique_id": str(first_value(user, "uniqueId", "unique_id") or ""),
                "nickname": str(user.get("nickname") or ""),
                "region": user.get("region"),
                "avatar_url": first_avatar_url(user),
                "tags": user.get("userTags"),
            },
            "raw": item,
        }
    if platform == "wechat-channel":
        return {
            "platform": platform,
            "comment_id": str(first_value(item, "commentId", "comment_id", "id") or ""),
            "video_id": str(first_value(item, "videoId", "objectId") or ""),
            "text": str(first_value(item, "content", "text") or ""),
            "language": None,
            "created_at": iso_utc(first_value(item, "createTime", "create_time")),
            "like_count": to_int(first_value(item, "likeCount", "like_count")),
            "author_pinned": False,
            "author_liked": False,
            "reply_id": "",
            "reply_count": to_int(first_value(item, "replyCount", "reply_count")),
            "hidden": False,
            "ip_region": first_value(item, "ipRegion", "ip_region"),
            "user": {
                "uid": str(first_value(item, "username", "userId") or ""),
                "unique_id": str(first_value(item, "username", "userId") or ""),
                "nickname": str(item.get("nickname") or ""),
                "avatar_url": str(first_value(item, "headUrl", "avatarUrl") or ""),
                "tags": None,
            },
            "raw": item,
        }

    nested_user = user
    return {
        "platform": platform,
        "comment_id": str(first_value(item, "id", "commentId", "comment_id", "cid") or ""),
        "video_id": str(first_value(item, "noteId", "videoId", "awemeId") or ""),
        "text": str(first_value(item, "text", "content", "comment") or ""),
        "language": first_value(item, "language", "commentLanguage"),
        "created_at": iso_utc(first_value(item, "createTime", "create_time", "createdAt", "time")),
        "like_count": to_int(first_value(item, "likeCount", "diggCount", "digg_count", "likes")),
        "author_pinned": bool(first_value(item, "authorPinned", "isPinned")),
        "author_liked": bool(first_value(item, "authorLiked", "isAuthorLiked")),
        "viewer_liked": bool(item.get("liked")),
        "reply_id": str(first_value(item, "replyId", "reply_id") or ""),
        "reply_count": to_int(first_value(item, "replyCount", "replyCommentTotal", "subCommentCount")),
        "hidden": bool(first_value(item, "hidden", "isFolded")),
        "invalid": bool(item.get("invalid")),
        "comment_type": item.get("commentType"),
        "ip_region": first_value(item, "ipRegion", "ipLabel", "ipLocation"),
        "user": {
            "uid": str(first_value(nested_user, "id", "uid", "userId", "userid") or first_value(item, "userId", "userid") or ""),
            "unique_id": str(first_value(nested_user, "username", "uniqueId", "redId") or ""),
            "nickname": str(first_value(nested_user, "nickname", "name", "nickName") or ""),
            "avatar_url": first_avatar_url(nested_user),
            "tags": first_value(nested_user, "tags", "userTags"),
        },
        "raw": item,
    }


def normalize_response(payload: dict[str, Any], platform: str, video_url: str) -> dict[str, Any]:
    data = payload.get("data") or {}
    comments = [normalize_comment(item, platform) for item in data.get("comments") or []]
    languages = Counter(item.get("language") or "unknown" for item in comments)
    pages = data.get("pages") or []
    return {
        "platform": platform,
        "video_url": video_url,
        "comments": comments,
        "summary": {
            "comment_count": len(comments),
            "page_count": len(pages) if isinstance(pages, list) else 0,
            "next_cursor": data.get("cursor"),
            "has_more": bool(data.get("hasMore")),
            "duplicate_count": to_int(data.get("duplicateCount")),
            "stopped_reason": data.get("stoppedReason"),
            "top_languages": [
                {"language": language, "count": count}
                for language, count in languages.most_common(5)
            ],
            "top_liked_comments": sorted(
                comments, key=lambda item: item["like_count"], reverse=True
            )[:5],
        },
        "timestamp": payload.get("timestamp"),
    }


def parse_cursor(value: str | None) -> Any:
    # Cursor is opaque for every platform: return exactly what the caller
    # supplied. In particular, do not JSON-decode or escape Instagram cursors.
    return value or None


def emit_json(payload: dict[str, Any], output: str | None, force: bool) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if not output:
        sys.stdout.write(text)
        return
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if force:
        path.write_text(text, encoding="utf-8")
    else:
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(text)
        except FileExistsError as exc:
            raise SystemExit(f"输出文件已存在：{path}。确认覆盖后传 --force。") from exc
    summary = payload.get("summary") or {}
    sys.stderr.write(
        f"已保存 {summary.get('comment_count', '未知')} 条评论到 {path}\n"
    )


def command_download(args: argparse.Namespace) -> None:
    if args.max_pages is not None and args.max_pages < 1:
        raise SystemExit("--max-pages 必须大于等于 1。")
    if args.max_comments is not None and args.max_comments < 1:
        raise SystemExit("--max-comments 必须大于等于 1。")
    if args.timeout < 1:
        raise SystemExit("--timeout 必须大于等于 1。")
    if args.retries < 0:
        raise SystemExit("--retries 必须大于等于 0。")
    if args.retry_sleep_ms < 0 or args.sleep_ms < 0:
        raise SystemExit("--retry-sleep-ms 和 --sleep-ms 必须大于等于 0。")
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        if output_path.exists() and not args.force:
            raise SystemExit(f"输出文件已存在：{output_path}。确认覆盖后传 --force。")
    platform = normalize_platform(args.platform, args.video_url)
    raw = fetch_comments(
        args.video_url,
        platform=platform,
        sort_order=args.sort_order,
        cursor=parse_cursor(args.cursor),
        max_pages=args.max_pages,
        max_comments=args.max_comments,
        first_page=args.first_page,
        timeout=args.timeout,
        retries=args.retries,
        retry_sleep_ms=args.retry_sleep_ms,
        sleep_ms=args.sleep_ms,
        dedupe=not args.no_dedupe,
        progress=not args.no_progress,
    )
    result = raw if args.raw else normalize_response(raw, platform, args.video_url)
    emit_json(result, args.output, args.force)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download TikTok, Instagram, Douyin, WeChat Channels, or Xiaohongshu comments."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    download = subparsers.add_parser("download", help="Download comments from one video URL.")
    download.add_argument("--video-url", required=True, help="Public social-video URL.")
    download.add_argument("--platform", default=None, help="tiktok, instagram, douyin, wechat-channel, or xiaohongshu; inferred from URL when omitted.")
    download.add_argument("--sort-order", choices=("popular", "newest"), default="popular", help="Instagram comment order; used only for Instagram.")
    download.add_argument("--cursor", default=None, help="Opaque resume cursor; pass it back exactly as returned.")
    download.add_argument("--first-page", action="store_true", help="Download only the first page.")
    download.add_argument("--max-pages", type=int, default=None, help="Maximum number of pages to download.")
    download.add_argument("--max-comments", type=int, default=None, help="Stop after collecting this many unique comments.")
    download.add_argument("--raw", action="store_true", help="Keep the aggregated API response instead of normalized JSON.")
    download.add_argument("--output", default=None, help="Write JSON to this file instead of stdout.")
    download.add_argument("--force", action="store_true", help="Overwrite an existing output file.")
    download.add_argument("--timeout", type=int, default=60, help="Per-request timeout in seconds.")
    download.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Retries for HTTP 429, 5xx, and network errors.")
    download.add_argument("--retry-sleep-ms", type=int, default=DEFAULT_RETRY_SLEEP_MS, help="Initial retry delay in milliseconds; doubles after each failure.")
    download.add_argument("--sleep-ms", type=int, default=DEFAULT_PAGE_SLEEP_MS, help="Delay between successful page requests in milliseconds.")
    download.add_argument("--no-dedupe", action="store_true", help="Keep duplicate comment IDs across pages.")
    download.add_argument("--no-progress", action="store_true", help="Suppress page progress messages on stderr.")
    download.set_defaults(func=command_download)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
