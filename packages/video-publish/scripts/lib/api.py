"""HTTP 调用：上传、创建发布、达人查询、产品搜索。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

def _shared_scripts_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "shared" / "scripts"
        if candidate.exists():
            return candidate
    raise RuntimeError("未找到 shared/scripts 目录。请确认 skill 安装完整。")


sys.path.insert(0, str(_shared_scripts_dir()))
from lingtu_auth import require_api_key as shared_require_api_key

from .config import (
    API_TIMEOUT,
    CREATOR_PAGE_LIST_PATH,
    DEFAULT_BASE_URL,
    FILE_CONFIRM_PATH,
    FILE_PRESIGN_PATH,
    POST_CREATE_PATH,
    PRODUCT_SHOP_LIST_PATH,
    PRODUCT_SHOWCASE_LIST_PATH,
    UPLOAD_TIMEOUT,
)


def require_api_key() -> str:
    try:
        return shared_require_api_key()
    except SystemExit as exc:
        raise SystemExit(
            f"{exc}\n请先设置 LINGTU_API_KEY 环境变量，或运行 python3 shared/scripts/user_keys.py single bind 生成绑定链接。"
        ) from exc


def base_url() -> str:
    return os.environ.get("LINGTU_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _request_json(
    method: str,
    path: str,
    query_params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = API_TIMEOUT,
) -> dict[str, Any]:
    """统一的 JSON API 请求，自动处理 envelope (code==0) 和错误。"""
    api_key = require_api_key()
    url = f"{base_url()}{path}"
    if query_params:
        url = f"{url}?{urllib_parse.urlencode(query_params, doseq=True)}"

    req = urllib_request.Request(url, method=method)
    req.add_header("x-api-key", api_key)
    req.add_header("Accept", "application/json")

    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req.data = payload
        req.add_header("Content-Type", "application/json")

    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
            message = detail.get("message") or exc.reason
        except Exception:
            message = exc.reason
        raise SystemExit(f"{path} HTTP 错误：{exc.code} {message}")
    except urllib_error.URLError as exc:
        raise SystemExit(f"{path} 网络错误：{exc.reason}")

    code = result.get("code")
    if code == 0:
        return result

    message = result.get("message") or "未知错误"
    raise SystemExit(f"{path} 调用失败 (code={code})：{message}")


def _compute_file_hash(file_path: Path) -> str:
    """计算文件 SHA-256 hash（与后端 Java 一致：raw bytes → hex → SHA-256）。"""
    import hashlib
    raw = file_path.read_bytes()
    hex_str = raw.hex()
    return hashlib.sha256(hex_str.encode("utf-8")).hexdigest()


def upload_file(file_path: str) -> dict[str, Any]:
    """通过 presigned URL 上传视频文件，返回 {id, url}。

    Flow: presign → PUT to uploadUrl (if new) → confirm → return {id, url}
    """
    import http.client
    import mimetypes

    p = Path(file_path).expanduser()
    if not p.exists():
        raise SystemExit(f"视频文件不存在：{p}")
    if not p.is_file():
        raise SystemExit(f"路径不是文件：{p}")

    file_size = p.stat().st_size
    file_name = p.name
    content_type = mimetypes.guess_type(file_name)[0] or "video/mp4"
    file_hash = _compute_file_hash(p)

    # Step 1: presign
    presign_body = {
        "fileName": file_name,
        "contentType": content_type,
        "size": file_size,
        "hash": file_hash,
    }
    result = _request_json("POST", FILE_PRESIGN_PATH, body=presign_body, timeout=UPLOAD_TIMEOUT)
    data = result.get("data") or {}
    file_id = data.get("fileId") or data.get("id") or ""
    upload_url = data.get("uploadUrl") or ""
    raw_is_new = data.get("isNew")
    is_new = raw_is_new is True or raw_is_new == "true" or raw_is_new == "1" or raw_is_new == 1
    final_url = data.get("url") or ""

    # Step 2/3: only newly uploaded files need PUT + confirm.
    # When isNew=false the backend has already matched an existing file by hash.
    should_upload = is_new or (raw_is_new is None and bool(upload_url))
    if should_upload and upload_url:
        _put_file(upload_url, p.read_bytes(), content_type)
        _request_json("POST", FILE_CONFIRM_PATH, body={"fileId": file_id}, timeout=API_TIMEOUT)

    return {"id": str(file_id), "url": final_url}


def _put_file(url: str, data: bytes, content_type: str) -> None:
    """HTTP PUT 文件到 presigned URL。"""
    import http.client

    parsed = urllib_parse.urlparse(url)
    conn: http.client.HTTPSConnection | http.client.HTTPConnection
    try:
        if parsed.scheme == "https":
            conn = http.client.HTTPSConnection(parsed.hostname or "", timeout=UPLOAD_TIMEOUT)
        else:
            conn = http.client.HTTPConnection(parsed.hostname or "", timeout=UPLOAD_TIMEOUT)
        conn.request("PUT", parsed.path + ("?" + parsed.query if parsed.query else ""),
                     body=data,
                     headers={"Content-Type": content_type})
        resp = conn.getresponse()
        resp.read()  # consume response
        if resp.status >= 400:
            raise SystemExit(f"文件上传失败：HTTP {resp.status} {resp.reason}")
    except http.client.HTTPException as exc:
        raise SystemExit(f"文件上传网络错误：{exc}")
    finally:
        conn.close()


def list_creator_accounts(
    page_size: int = 200,
    page_number: int = 1,
    valid: bool = True,
    usernames: list[str] | None = None,
    platform: str | None = None,
    selection_region: str | None = None,
) -> dict[str, Any]:
    """获取已授权达人列表。"""
    params: dict[str, Any] = {
        "pageSize": page_size,
        "pageNumber": page_number,
        "valid": valid,
    }
    if usernames:
        params["usernames"] = usernames
    if platform:
        from .config import AUTH_SOURCE_MAP
        auth_source = AUTH_SOURCE_MAP.get(platform)
        if auth_source:
            params["authSource"] = auth_source
    if selection_region:
        params["selectionRegion"] = selection_region

    return _request_json("GET", CREATOR_PAGE_LIST_PATH, query_params=params)


def resolve_creator_id(username: str, platform: str | None = None) -> dict[str, Any] | None:
    """根据 username 查找达人，返回 {creatorId, oauthRegion, ...}。"""
    raw_username = username.lstrip("@").strip()
    result = list_creator_accounts(usernames=[raw_username], platform=platform)
    data = result.get("data") or {}
    items = data.get("list") or []
    for item in items:
        if item.get("username", "").lower() == raw_username.lower():
            return {
                "creatorId": item.get("creatorId") or "",
                "username": item.get("username") or raw_username,
                "targetRegion": item.get("targetRegion") or "",
                "targetMarket": item.get("targetMarket") or "",
                "marketRegion": item.get("marketRegion") or "",
                "shopRegion": item.get("shopRegion") or "",
                "selectionRegion": item.get("selectionRegion") or "",
                "oauthRegion": item.get("oauthRegion") or "",
                "registerRegion": item.get("registerRegion") or "",
            }
    return None


def resolve_creator_batch(
    usernames: list[str], platform: str | None = None
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """批量解析达人 username → {creatorId, oauthRegion, ...}。"""
    cleaned = [u.lstrip("@").strip() for u in usernames if u.strip()]
    if not cleaned:
        return {}, []

    result = list_creator_accounts(usernames=cleaned, platform=platform)
    data = result.get("data") or {}
    items = data.get("list") or []

    found: dict[str, dict[str, Any]] = {}
    for item in items:
        uname = item.get("username", "").lower()
        found[uname] = {
            "creatorId": item.get("creatorId") or "",
            "username": item.get("username") or uname,
            "targetRegion": item.get("targetRegion") or "",
            "targetMarket": item.get("targetMarket") or "",
            "marketRegion": item.get("marketRegion") or "",
            "shopRegion": item.get("shopRegion") or "",
            "selectionRegion": item.get("selectionRegion") or "",
            "oauthRegion": item.get("oauthRegion") or "",
            "registerRegion": item.get("registerRegion") or "",
        }

    not_found = [u for u in cleaned if u.lower() not in found]
    return found, not_found


def create_post(
    *,
    creator_id: str,
    title: str,
    business_id: str,
    business_type: str = "FILE",
    platform: str,
    scheduled_at: int | None = None,
    scheduled_tz: str | None = None,
    oauth_region: str | None = None,
    product_id: str | None = None,
    product_title: str | None = None,
    product_source: str | None = None,
) -> dict[str, Any]:
    """创建发布任务。"""
    from .config import PLATFORM_API_MAP

    api_platform = PLATFORM_API_MAP.get(platform, "TIKTOK")
    body: dict[str, Any] = {
        "businessId": business_id,
        "businessType": business_type,
        "creatorId": creator_id,
        "title": title,
        "platform": api_platform,
    }

    if scheduled_at is not None:
        body["scheduledAt"] = scheduled_at
    if scheduled_tz:
        body["scheduledTz"] = scheduled_tz
    if oauth_region:
        body["oauthRegion"] = oauth_region

    if platform == "tiktok_shop":
        tiktok_shop: dict[str, Any] = {}
        if product_id and product_source:
            tiktok_shop["productInfo"] = {
                "productId": product_id,
                "title": product_title or "",
                "source": product_source,
            }
        if tiktok_shop:
            body["tiktokShop"] = tiktok_shop
    elif platform == "tiktok":
        body["tiktok"] = {
            "privacyLevel": "PUBLIC_TO_EVERYONE",
            "disableComment": False,
            "disableDuet": False,
            "disableStitch": False,
            "brandContentToggle": False,
            "brandOrganicToggle": False,
        }

    result = _request_json("POST", POST_CREATE_PATH, body=body)
    return result.get("data") or {}


def list_shop_products(
    creator_id: str,
    origin: str = "TIKTOK",
    page_size: int = 20,
    page_token: str | None = None,
    title_keyword: str | None = None,
) -> dict[str, Any]:
    """搜索店铺商品。"""
    params: dict[str, Any] = {
        "id": creator_id,
        "origin": origin,
        "pageSize": page_size,
    }
    if page_token:
        params["pageToken"] = page_token
    if title_keyword:
        params["titleKeyword"] = title_keyword

    return _request_json("GET", PRODUCT_SHOP_LIST_PATH, query_params=params)


def list_showcase_products(
    creator_id: str,
    page_size: int = 20,
    page_token: str | None = None,
) -> dict[str, Any]:
    """搜索橱窗商品。"""
    params: dict[str, Any] = {
        "id": creator_id,
        "origin": "TIKTOK",
        "pageSize": page_size,
    }
    if page_token:
        params["pageToken"] = page_token

    return _request_json("GET", PRODUCT_SHOWCASE_LIST_PATH, query_params=params)
