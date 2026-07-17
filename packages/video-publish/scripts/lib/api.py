"""HTTP 调用：上传、创建发布、达人查询、产品搜索。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _shared_scripts_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "shared" / "scripts"
        if candidate.is_dir():
            return candidate
    raise RuntimeError("未找到 shared/scripts 目录。请确认 skill 安装完整。")


sys.path.insert(0, str(_shared_scripts_dir()))
from lingtu_auth import require_api_key as shared_require_api_key
from lingtu_http import LingtuHttpError, base_url as shared_base_url, raise_system_exit, request_json
from lingtu_upload import compute_content_hash, put_file

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
    return shared_base_url(DEFAULT_BASE_URL)


def _request_json(
    method: str,
    path: str,
    query_params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = API_TIMEOUT,
) -> dict[str, Any]:
    """统一的 JSON API 请求，自动处理 envelope (code==0) 和错误。"""
    try:
        result = request_json(
            method,
            path,
            body=body,
            query=query_params,
            timeout=timeout,
            expect_envelope=True,
        )
    except LingtuHttpError as exc:
        if exc.status is not None:
            message = exc.reason or str(exc)
            # Prefer server message body when present.
            if exc.body:
                try:
                    import json

                    detail = json.loads(exc.body)
                    message = detail.get("message") or message
                except Exception:
                    pass
            raise SystemExit(f"{path} HTTP 错误：{exc.status} {message}") from exc
        raise SystemExit(f"{path} 网络错误：{exc.reason or exc}") from exc
    if not isinstance(result, dict):
        raise SystemExit(f"{path} 调用失败：响应不是 JSON 对象")
    return result


def _compute_file_hash(file_path: Path) -> str:
    """计算文件 SHA-256 hash（与后端 Java 一致：raw bytes → hex → SHA-256）。"""
    return compute_content_hash(file_path)


def _put_file(url: str, data: bytes, content_type: str) -> None:
    """HTTP PUT 文件到 presigned URL。"""
    try:
        put_file(url, data, content_type, timeout=UPLOAD_TIMEOUT)
    except LingtuHttpError as exc:
        raise_system_exit(exc)


def upload_file(file_path: str, *, default_content_type: str = "video/mp4") -> dict[str, Any]:
    """通过 presigned URL 上传媒体文件，返回 {id, url}。

    Flow: presign → PUT to uploadUrl (if new) → confirm → return {id, url}
    Kept as a thin wrapper so tests can patch `_request_json` / `_put_file`.
    """
    p = Path(file_path).expanduser()
    if not p.exists():
        raise SystemExit(f"文件不存在：{p}")
    if not p.is_file():
        raise SystemExit(f"路径不是文件：{p}")

    import mimetypes

    file_size = p.stat().st_size
    file_name = p.name
    content_type = mimetypes.guess_type(file_name)[0] or default_content_type
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
    should_upload = is_new or (raw_is_new is None and bool(upload_url))
    if should_upload and upload_url:
        _put_file(upload_url, p.read_bytes(), content_type)
        _request_json("POST", FILE_CONFIRM_PATH, body={"fileId": file_id}, timeout=API_TIMEOUT)

    return {"id": str(file_id), "url": final_url}


def list_creator_accounts(
    page_size: int = 200,
    page_number: int = 1,
    valid: bool = True,
    usernames: list[str] | None = None,
    platform: str | None = None,
    selection_region: str | None = None,
    has_photo_permission: bool | None = None,
) -> dict[str, Any]:
    """获取已授权达人列表。

    has_photo_permission:
      可选。传 True 时带查询参数 hasPhotoPermission=true，
      仅返回具备图文带货权限的账号。
    """
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
    if has_photo_permission is not None:
        # 后端期望 true/false 小写；Python urlencode(True) 会变成 "True"
        params["hasPhotoPermission"] = "true" if has_photo_permission else "false"

    return _request_json("GET", CREATOR_PAGE_LIST_PATH, query_params=params)


def _creator_summary(item: dict[str, Any], fallback_username: str = "") -> dict[str, Any]:
    """从 pageList item 抽取发布所需字段（含 authSource / permissions）。"""
    # id: 创作者账号表主键（整数），商品 listByShop/listByShowcase 的 query id 必须用它
    # creatorId: 业务侧创作者 gid（字符串），发布 create_post 用它
    account_id = item.get("id")
    if account_id is None or account_id == "":
        account_id = item.get("accountId") or item.get("creatorAccountId") or ""
    return {
        "id": str(account_id) if account_id != "" and account_id is not None else "",
        "creatorId": item.get("creatorId") or "",
        "username": item.get("username") or fallback_username,
        "authSource": item.get("authSource") or item.get("auth_source") or "",
        "permissions": extract_permissions(item),
        "targetRegion": item.get("targetRegion") or "",
        "targetMarket": item.get("targetMarket") or "",
        "marketRegion": item.get("marketRegion") or "",
        "shopRegion": item.get("shopRegion") or "",
        "selectionRegion": item.get("selectionRegion") or "",
        "oauthRegion": item.get("oauthRegion") or "",
        "registerRegion": item.get("registerRegion") or "",
    }


def extract_permissions(item: dict[str, Any]) -> list[str]:
    """从达人账号对象中解析 permissions 列表。"""
    raw = (
        item.get("permissions")
        if item.get("permissions") is not None
        else item.get("permissionList")
        if item.get("permissionList") is not None
        else item.get("permissionCodes")
        if item.get("permissionCodes") is not None
        else item.get("permission")
    )
    return normalize_permission_list(raw)


def normalize_permission_list(raw: Any) -> list[str]:
    """permissions 可能是 string / list[str] / list[dict]。"""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    if isinstance(raw, (list, tuple, set)):
        out: list[str] = []
        for entry in raw:
            if isinstance(entry, str) and entry.strip():
                out.append(entry.strip())
            elif isinstance(entry, dict):
                for key in ("permission", "permissionCode", "permissionName", "code", "name", "value"):
                    val = entry.get(key)
                    if val is not None and str(val).strip():
                        out.append(str(val).strip())
                        break
        return out
    return []


def is_tiktok_shop_auth_source(auth_source: str | None) -> bool:
    """账号是否来自 TikTok Shop 授权（非 Login Kit 养号）。"""
    value = (auth_source or "").strip().upper().replace("-", "_")
    return "TIKTOK_SHOP" in value


def creator_can_publish_photo(creator_info: dict[str, Any] | None) -> tuple[bool, str]:
    """带货图文资格：TikTok Shop 来源 + PHOTO_SHOPPABLE_PERMISSION_PRODUCT。"""
    from .config import PHOTO_SHOPPABLE_PERMISSION

    if not creator_info:
        return False, "未找到达人账号"
    username = creator_info.get("username") or creator_info.get("creatorId") or "?"
    if not is_tiktok_shop_auth_source(str(creator_info.get("authSource") or "")):
        return (
            False,
            f"@{username} 不是 TikTok Shop 授权账号，无法发带货图文（需 authSource 来自 TikTok Shop）",
        )
    perms = creator_info.get("permissions")
    if not isinstance(perms, list):
        perms = normalize_permission_list(perms)
    perm_set = {str(p).strip().upper() for p in perms if str(p).strip()}
    if PHOTO_SHOPPABLE_PERMISSION.upper() not in perm_set:
        return (
            False,
            f"@{username} 缺少权限 {PHOTO_SHOPPABLE_PERMISSION}，无法发带货图文",
        )
    return True, ""


def resolve_creator_id(
    username: str,
    platform: str | None = None,
    has_photo_permission: bool | None = None,
) -> dict[str, Any] | None:
    """根据 username 查找达人，返回 {creatorId, oauthRegion, authSource, permissions, ...}。"""
    raw_username = username.lstrip("@").strip()
    result = list_creator_accounts(
        usernames=[raw_username],
        platform=platform,
        has_photo_permission=has_photo_permission,
    )
    data = result.get("data") or {}
    items = data.get("list") or []
    for item in items:
        if item.get("username", "").lower() == raw_username.lower():
            return _creator_summary(item, fallback_username=raw_username)
    return None


def resolve_creator_batch(
    usernames: list[str],
    platform: str | None = None,
    has_photo_permission: bool | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """批量解析达人 username → {creatorId, oauthRegion, authSource, permissions, ...}。"""
    cleaned = [u.lstrip("@").strip() for u in usernames if u.strip()]
    if not cleaned:
        return {}, []

    result = list_creator_accounts(
        usernames=cleaned,
        platform=platform,
        has_photo_permission=has_photo_permission,
    )
    data = result.get("data") or {}
    items = data.get("list") or []

    found: dict[str, dict[str, Any]] = {}
    for item in items:
        uname = item.get("username", "").lower()
        found[uname] = _creator_summary(item, fallback_username=uname)

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
    media_type: str | None = None,
    business_ids: list[str] | None = None,
    photo_post_type: str = "MULTI_PHOTO_ONE_ANCHOR",
    product_links: list[dict[str, str]] | None = None,
    music_info: dict[str, str] | None = None,
) -> dict[str, Any]:
    """创建发布任务。

    media_type:
      - 省略 / "VIDEO"：视频发布（默认，请求体固定传 mediaType=VIDEO）
      - "PHOTO"：TikTok Shop 带货图文，使用 tiktokShopPhoto

    带货图文约定：
      - businessId = 首图 fileId
      - tiktokShopPhoto.businessIds = 全部图片 fileId，顺序=用户上传/CSV 填写顺序
      - productLinks 固定 1 个产品（多图单锚点 MULTI_PHOTO_ONE_ANCHOR）
    """
    from .config import PLATFORM_API_MAP

    api_platform = PLATFORM_API_MAP.get(platform, "TIKTOK")
    normalized_media = (media_type or "VIDEO").strip().upper()
    if normalized_media not in ("VIDEO", "PHOTO"):
        raise SystemExit(f"无效 mediaType：{media_type}（可选：VIDEO / PHOTO）")
    is_photo = normalized_media == "PHOTO"

    body: dict[str, Any] = {
        "businessId": business_id,
        "businessType": business_type,
        "creatorId": creator_id,
        "title": title,
        "platform": api_platform,
        "mediaType": "PHOTO" if is_photo else "VIDEO",
    }

    if scheduled_at is not None:
        body["scheduledAt"] = scheduled_at
    if scheduled_tz:
        body["scheduledTz"] = scheduled_tz
    if oauth_region:
        body["oauthRegion"] = oauth_region

    if is_photo:
        if platform != "tiktok_shop":
            raise SystemExit("带货图文 (mediaType=PHOTO) 仅支持 platform=tiktok_shop")
        # 顺序必须保持用户上传顺序；首图作 businessId
        ids = [str(i).strip() for i in (business_ids or [business_id]) if str(i).strip()]
        if not ids:
            raise SystemExit("带货图文需要至少一张图片 fileId（businessIds）")
        body["businessId"] = ids[0]

        # 多图挂车：productLinks 仅允许 1 个产品
        if product_links:
            if len(product_links) != 1:
                raise SystemExit(
                    f"带货图文 productLinks 只能有 1 个产品，当前 {len(product_links)} 个"
                )
            link = product_links[0]
            links = [{
                "productId": str(link.get("productId") or "").strip(),
                "title": str(link.get("title") or ""),
                "source": str(link.get("source") or product_source or "SHOP").strip() or "SHOP",
            }]
            if not links[0]["productId"]:
                raise SystemExit("带货图文 productLinks[0].productId 不能为空")
        elif product_id and product_source:
            links = [{
                "productId": product_id,
                "title": product_title or "",
                "source": product_source,
            }]
        else:
            raise SystemExit("带货图文必须提供 1 个挂车产品（product_id + product_source）")

        photo: dict[str, Any] = {
            "postType": photo_post_type or "MULTI_PHOTO_ONE_ANCHOR",
            "businessIds": ids,
            "productLinks": links,
        }
        if music_info and music_info.get("id"):
            photo["musicInfo"] = {
                "id": str(music_info["id"]),
                "title": str(music_info.get("title") or ""),
                "author": str(music_info.get("author") or ""),
                "duration": str(music_info.get("duration") or ""),
            }
        body["tiktokShopPhoto"] = photo
    elif platform == "tiktok_shop":
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
