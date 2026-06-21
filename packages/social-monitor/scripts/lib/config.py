"""常量与平台元数据。"""

from __future__ import annotations

import re
from pathlib import Path


DEFAULT_STORE = Path.home() / ".lingtu" / "social-monitor" / "monitors.json"
DEFAULT_SNAPSHOTS = Path.home() / ".lingtu" / "social-monitor" / "snapshots"
DEFAULT_BASE_URL = "https://api.ailingtu.com"

FETCH_POSTS_PATH = "/v1/influencer/fetchPosts"
FETCH_MATERIAL_PATH = "/v1/material/tiktok/fetch"
FETCH_MATERIAL_COMMENTS_PATH = "/v1/material/tiktok/fetchComments"
INS_FETCH_POSTS_PATH = "/v1/influencer/ins/fetchPosts"
INS_FETCH_MATERIAL_PATH = "/v1/material/ins/fetch"
INS_FETCH_MATERIAL_COMMENTS_PATH = "/v1/material/ins/fetchComments"

DEFAULT_PLATFORM = "tiktok"
SUPPORTED_PLATFORMS = ("tiktok", "instagram")
PLATFORM_LABELS = {
    "tiktok": "TikTok",
    "instagram": "Instagram",
}

HASHTAG_PATTERN = re.compile(r"[#＃]([\w一-鿿]+)")
STALL_DAYS = 7
SURGE_WEEK_THRESHOLD = 3

INSTAGRAM_RESERVED_PATHS = frozenset({
    "p", "reel", "reels", "tv", "stories", "explore", "accounts",
    "directory", "developer", "about", "legal", "web", "ajax", "api",
    "session", "challenge", "privacy", "terms",
})

FOCUS_CHOICES = ("overall", "posting", "content")
FOCUS_LABELS = {
    "overall": "综合画像",
    "posting": "发布策略",
    "content": "内容形式",
}

WEEKDAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")

HOOK_PATTERNS = (
    ("疑问句", lambda text: bool(re.search(r"[?？]", text))),
    ("数字开头", lambda text: bool(re.match(r"\s*\d", text))),
    ("强指令", lambda text: any(
        kw in text.lower() for kw in (
            "stop ", "try ", "don't ", "do not ", "watch ", "save this",
            "停下", "别再", "试试", "记得", "一定要",
        ))),
    ("痛点陈述", lambda text: any(
        kw in text.lower() for kw in (
            "pain", "hurt", "sore", "tired", "struggle",
            "痛", "疼", "酸", "累", "烦",
        ))),
    ("故事钩子", lambda text: any(
        kw in text.lower() for kw in (
            "i tried", "i tested", "my ", "we ",
            "我试", "我测", "我的", "亲测",
        ))),
    ("直接展示", lambda text: any(
        kw in text.lower() for kw in (
            "before", "after", "result", "demo",
            "前后", "对比", "效果", "演示",
        ))),
)


THEME_RULES = {
    "痛点解决类": (
        "pain", "hurt", "sore", "knees", "knee", "recovery", "no pain", "support",
        "痛", "疼", "酸", "缓解", "修复",
    ),
    "使用教程类": (
        "how to", "try this", "before your next", "steps", "demo", "use",
        "教程", "教你", "步骤", "怎么用", "演示", "教学",
    ),
    "产品展示类": (
        "support", "tape", "brace", "sleeve", "product", "gear",
        "新品", "产品", "上新", "开箱",
    ),
    "运动场景类": (
        "running", "run", "workout", "fitness", "training", "gym",
        "跑步", "健身", "训练", "运动",
    ),
    "测评推荐类": (
        "review", "recommend", "tested", "why i use",
        "测评", "推荐", "实测", "亲测",
    ),
    "前后对比类": (
        "before", "after", "result", "better",
        "前后", "对比", "效果",
    ),
    "促销转化类": (
        "discount", "deal", "shop", "link", "buy",
        "折扣", "优惠", "下单", "链接", "购买", "直播",
    ),
}
