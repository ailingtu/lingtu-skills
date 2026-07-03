"""常量与平台元数据。"""

from __future__ import annotations

from pathlib import Path

DEFAULT_BASE_URL = "https://api.ailingtu.com"
DEFAULT_DESKTOP = Path.home() / "Desktop"

UPLOAD_PATH = "/v1/file/upload"
FILE_PRESIGN_PATH = "/v1/file/presign"
FILE_CONFIRM_PATH = "/v1/file/confirm"
CREATOR_PAGE_LIST_PATH = "/v1/creatorAccount/pageList"
POST_CREATE_PATH = "/v1/creator/post/create"
PRODUCT_SHOP_LIST_PATH = "/v1/creator/tiktokshop/product/listByShop"
PRODUCT_SHOWCASE_LIST_PATH = "/v1/creator/tiktokshop/product/listByShowcase"

SUPPORTED_PLATFORMS = ("tiktok_shop", "tiktok")
PLATFORM_LABELS = {"tiktok_shop": "TikTok Shop (带货)", "tiktok": "TikTok (养号)"}

PLATFORM_API_MAP = {"tiktok_shop": "TIKTOK_SHOP", "tiktok": "TIKTOK"}
AUTH_SOURCE_MAP = {"tiktok_shop": "TIKTOK_SHOP_CREATOR", "tiktok": "TIKTOK_LOGIN_KIT"}

TIMEZONE_MAP: dict[str, str] = {
    "EST": "America/New_York",
    "PST": "America/Los_Angeles",
    "GB": "Europe/London",
    "CN": "Asia/Shanghai",
    "JP": "Asia/Tokyo",
    "KR": "Asia/Seoul",
    "SG": "Asia/Singapore",
    "MY": "Asia/Kuala_Lumpur",
    "ID": "Asia/Jakarta",
    "TH": "Asia/Bangkok",
    "VN": "Asia/Ho_Chi_Minh",
    "PH": "Asia/Manila",
    "MX": "America/Mexico_City",
    "BR": "America/Sao_Paulo",
    "SA": "Asia/Riyadh",
    "AE": "Asia/Dubai",
    "AU": "Australia/Sydney",
    "CA": "America/Toronto",
}

REGION_TIMEZONE_MAP: dict[str, str] = {
    "US": "America/Los_Angeles",
    "USA": "America/Los_Angeles",
    "UNITED_STATES": "America/Los_Angeles",
    "UNITED STATES": "America/Los_Angeles",
    "CA": "America/Toronto",
    "CAN": "America/Toronto",
    "MX": "America/Mexico_City",
    "MEX": "America/Mexico_City",
    "BR": "America/Sao_Paulo",
    "BRA": "America/Sao_Paulo",
    "GB": "Europe/London",
    "UK": "Europe/London",
    "JP": "Asia/Tokyo",
    "JPN": "Asia/Tokyo",
    "KR": "Asia/Seoul",
    "KOR": "Asia/Seoul",
    "SG": "Asia/Singapore",
    "SGP": "Asia/Singapore",
    "MY": "Asia/Kuala_Lumpur",
    "MYS": "Asia/Kuala_Lumpur",
    "ID": "Asia/Jakarta",
    "IDN": "Asia/Jakarta",
    "TH": "Asia/Bangkok",
    "THA": "Asia/Bangkok",
    "VN": "Asia/Ho_Chi_Minh",
    "VNM": "Asia/Ho_Chi_Minh",
    "PH": "Asia/Manila",
    "PHL": "Asia/Manila",
    "CN": "Asia/Shanghai",
    "CHN": "Asia/Shanghai",
    "SA": "Asia/Riyadh",
    "SAU": "Asia/Riyadh",
    "AE": "Asia/Dubai",
    "ARE": "Asia/Dubai",
    "AU": "Australia/Sydney",
    "AUS": "Australia/Sydney",
}

TIMEZONE_DROPDOWN_OPTIONS = [
    "America/New_York (EST)",
    "America/Los_Angeles (PST)",
    "America/Toronto (CA)",
    "America/Mexico_City (MX)",
    "America/Sao_Paulo (BR)",
    "Europe/London (GB)",
    "Asia/Shanghai (CN)",
    "Asia/Tokyo (JP)",
    "Asia/Seoul (KR)",
    "Asia/Singapore (SG)",
    "Asia/Kuala_Lumpur (MY)",
    "Asia/Jakarta (ID)",
    "Asia/Bangkok (TH)",
    "Asia/Ho_Chi_Minh (VN)",
    "Asia/Manila (PH)",
    "Asia/Riyadh (SA)",
    "Asia/Dubai (AE)",
    "Australia/Sydney (AU)",
]

DEFAULT_SCHEDULE_TIMES = (9, 14, 19)

CSV_REQUIRED_COLUMNS = ("creator_username", "platform", "title", "video_file")
CSV_ALL_COLUMNS = (
    "creator_username", "platform",
    "product_id", "product_title",
    "product_source", "title",
    "timezone", "scheduled_at",
    "video_file",
)

COLUMN_LABELS: dict[str, str] = {
    "creator_username": "达人用户名",
    "platform": "平台",
    "product_id": "产品ID",
    "product_title": "购物车标题",
    "product_source": "商品来源",
    "title": "视频文案内容",
    "timezone": "时区",
    "scheduled_at": "发布时间",
    "video_file": "视频文件名",
}

COLUMN_LABEL_TO_KEY: dict[str, str] = {v: k for k, v in COLUMN_LABELS.items()}

PRODUCT_SOURCE_OPTIONS = ("SHOP", "SHOWCASE")

PRODUCT_TITLE_MAX_LENGTH = 30
POST_TITLE_MAX_LENGTH = 4000
PUBLISH_RECORDS_URL = "https://app.ailingtu.com/video-center?tab=records"

UPLOAD_TIMEOUT = 600
API_TIMEOUT = 60
