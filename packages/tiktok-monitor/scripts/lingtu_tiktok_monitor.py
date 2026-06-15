#!/usr/bin/env python3
"""TikTok 达人监控与每日内容情报报告。

后端依赖灵途 `/v1/influencer/fetchPosts` 接口。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import date as date_cls
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.parse import urlparse


DEFAULT_STORE = Path.home() / ".lingtu" / "tiktok-monitor" / "monitors.json"
DEFAULT_SNAPSHOTS = Path.home() / ".lingtu" / "tiktok-monitor" / "snapshots"
DEFAULT_BASE_URL = "https://api.ailingtu.com"
FETCH_POSTS_PATH = "/v1/influencer/fetchPosts"
PLATFORM = "tiktok"
HASHTAG_PATTERN = re.compile(r"[#＃]([\w一-鿿]+)")
STALL_DAYS = 7
SURGE_WEEK_THRESHOLD = 3

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


# -------------------- 通用工具 --------------------

def require_api_key() -> str:
    key = os.environ.get("LINGTU_API_KEY")
    if not key:
        raise SystemExit("缺少环境变量 LINGTU_API_KEY，请先配置后再使用本技能。")
    return key


def base_url() -> str:
    return os.environ.get("LINGTU_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def store_path() -> Path:
    return Path(os.environ.get("LINGTU_TIKTOK_MONITOR_STORE", str(DEFAULT_STORE))).expanduser()


def snapshots_dir() -> Path:
    return Path(os.environ.get("LINGTU_TIKTOK_MONITOR_SNAPSHOTS", str(DEFAULT_SNAPSHOTS))).expanduser()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_str(value: str | None = None) -> str:
    if value:
        return value
    return now_utc().strftime("%Y-%m-%d")


def slugify_handle(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._-")
    return normalized.lower() or "unknown_creator"


def parse_unique_id(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise SystemExit("达人输入不能为空。")

    if "tiktok.com" in value:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        match = re.search(r"/@([^/?#]+)", parsed.path)
        if match:
            return slugify_handle(match.group(1))

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
        return str(value)
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


# -------------------- 接口调用 --------------------

def fetch_posts(unique_id: str, count: int) -> dict[str, Any]:
    api_key = require_api_key()
    query = urllib_parse.urlencode({"uniqueId": unique_id, "count": max(1, count)})
    url = f"{base_url()}{FETCH_POSTS_PATH}?{query}"
    req = urllib_request.Request(url, method="GET")
    req.add_header("x-api-key", api_key)
    req.add_header("Accept", "application/json")
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        raise SystemExit(f"fetchPosts HTTP 错误：{exc.code} {exc.reason}")
    except urllib_error.URLError as exc:
        raise SystemExit(f"fetchPosts 网络错误：{exc.reason}")

    code = payload.get("code")
    if code == 0 and isinstance(payload.get("data"), dict):
        return payload["data"]

    message = payload.get("message") or "未知错误"
    if code == -1:
        raise SystemExit(f"未获取到该达人数据：{message}（uniqueId={unique_id}）")
    raise SystemExit(f"fetchPosts 调用失败 (code={code})：{message}")


def normalize_response(data: dict[str, Any]) -> dict[str, Any]:
    author = data.get("authorInfo") or {}
    unique_id = author.get("uniqueId") or ""
    creator = {
        "platform": PLATFORM,
        "creator_id": str(author.get("id") or ""),
        "username": unique_id,
        "nickname": author.get("nickname") or unique_id,
        "profile_url": f"https://www.tiktok.com/@{unique_id}" if unique_id else "",
        "signature": author.get("signature") or "",
        "follower_count": author.get("followerCount"),
        "following_count": author.get("followingCount"),
        "aweme_count": author.get("awemeCount"),
        "total_favorited": author.get("totalFavorited"),
    }

    videos = []
    for post in data.get("posts") or []:
        stats = post.get("stats") or {}
        video_id = str(post.get("videoId") or "")
        caption = post.get("desc") or ""
        videos.append({
            "video_id": video_id,
            "video_url": f"https://www.tiktok.com/@{unique_id}/video/{video_id}" if unique_id and video_id else "",
            "caption": caption,
            "publish_time": iso_utc_from_epoch_seconds(post.get("createTime")),
            "duration": round((post.get("duration") or 0) / 1000, 2),
            "is_ad": bool(post.get("isAd")),
            "views": int(stats.get("playCount") or 0),
            "likes": int(stats.get("diggCount") or 0),
            "comments": int(stats.get("commentCount") or 0),
            "shares": int(stats.get("shareCount") or 0),
            "saves": int(stats.get("collectCount") or 0),
            "reposts": int(stats.get("repostCount") or 0),
            "cover_url": post.get("cover") or "",
            "play_url": post.get("playAddr") or "",
            "hashtags": extract_hashtags(caption),
        })

    return {
        "creator": creator,
        "videos": videos,
        "cursor": data.get("cursor"),
        "has_more": bool(data.get("hasMore")),
    }


# -------------------- monitors 存储 --------------------

def load_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"monitors": []}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("monitors"), list):
        raise SystemExit(f"监控存储结构异常：{path}")
    return data


def save_store(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp.replace(path)


def find_monitor(monitors: list[dict[str, Any]], group_id: str, username: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in monitors
            if item.get("group_id") == group_id
            and item.get("creator", {}).get("platform") == PLATFORM
            and item.get("creator", {}).get("username") == username
        ),
        None,
    )


def upsert_monitor(creator: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    path = store_path()
    data = load_store(path)
    monitors = data["monitors"]
    username = creator.get("username") or ""
    creator_id = creator.get("creator_id") or stable_id("creator", username)
    timestamp = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")

    existing = find_monitor(monitors, args.group_id, username)
    if existing:
        existing["remark"] = args.remark or existing.get("remark", "")
        existing["updated_at"] = timestamp
        existing["creator"] = creator
        if "daily_enabled" not in existing:
            existing["daily_enabled"] = False
        monitor = existing
    else:
        monitor = {
            "monitor_id": stable_id("monitor", f"{args.group_id}:{creator_id or username}", 10),
            "source": args.source,
            "group_id": args.group_id,
            "team_id": args.team_id,
            "operator_id": args.operator_id,
            "remark": args.remark,
            "added_at": timestamp,
            "updated_at": timestamp,
            "daily_enabled": False,
            "creator": creator,
        }
        monitors.append(monitor)
    save_store(path, data)
    return monitor


def update_monitor(group_id: str, username: str, **changes: Any) -> dict[str, Any]:
    path = store_path()
    data = load_store(path)
    monitor = find_monitor(data["monitors"], group_id, username)
    if not monitor:
        raise SystemExit(f"未找到监控记录（group_id={group_id}, username={username}）。")
    monitor.update(changes)
    monitor["updated_at"] = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    save_store(path, data)
    return monitor


def remove_monitor(group_id: str, username: str) -> dict[str, Any]:
    path = store_path()
    data = load_store(path)
    monitor = find_monitor(data["monitors"], group_id, username)
    if not monitor:
        raise SystemExit(f"未找到监控记录（group_id={group_id}, username={username}）。")
    data["monitors"] = [m for m in data["monitors"] if m is not monitor]
    save_store(path, data)
    return monitor


def list_monitors(group_id: str | None = None, daily_only: bool = False) -> list[dict[str, Any]]:
    data = load_store(store_path())
    items = data["monitors"]
    if group_id is not None:
        items = [m for m in items if m.get("group_id") == group_id]
    if daily_only:
        items = [m for m in items if m.get("daily_enabled")]
    return items


# -------------------- snapshot 存储 --------------------

def snapshot_path(group_id: str, creator_id: str, day: str) -> Path:
    safe_group = slugify_handle(group_id) or "default"
    safe_creator = slugify_handle(creator_id) or "unknown"
    return snapshots_dir() / safe_group / safe_creator / f"{day}.json"


def save_snapshot(group_id: str, normalized: dict[str, Any], day: str) -> Path:
    creator = normalized.get("creator") or {}
    creator_id = creator.get("creator_id") or creator.get("username") or "unknown"
    path = snapshot_path(group_id, creator_id, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "captured_at": now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "date": day,
        "group_id": group_id,
        "creator": creator,
        "videos": normalized.get("videos") or [],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp.replace(path)
    return path


def load_snapshot(group_id: str, creator_id: str, day: str) -> dict[str, Any] | None:
    path = snapshot_path(group_id, creator_id, day)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


# -------------------- 单账号分析 --------------------

def rate(video: dict[str, Any], key: str) -> float:
    views = max(int(video.get("views", 0)), 1)
    return int(video.get(key, 0)) / views


def combined_text(video: dict[str, Any]) -> str:
    parts = [
        str(video.get("caption", "")),
        " ".join(video.get("hashtags", []) or []),
    ]
    return " ".join(parts).lower()


def classify_video(video: dict[str, Any]) -> list[str]:
    text = combined_text(video)
    matched = []
    for theme, keywords in THEME_RULES.items():
        if any(keyword in text for keyword in keywords):
            matched.append(theme)
    return matched or ["生活方式类"]


def top_items(videos: list[dict[str, Any]], key: str, limit: int = 5) -> list[dict[str, Any]]:
    if key == "views":
        return sorted(videos, key=lambda item: int(item.get("views", 0)), reverse=True)[:limit]
    return sorted(videos, key=lambda item: rate(item, key), reverse=True)[:limit]


def coerce_normalized(data: dict[str, Any]) -> dict[str, Any]:
    if "videos" in data and "creator" in data:
        return data
    if "posts" in data and "authorInfo" in data:
        return normalize_response(data)
    if isinstance(data.get("data"), dict) and "posts" in data["data"]:
        return normalize_response(data["data"])
    raise SystemExit("无法识别的输入 JSON：需要 fetchPosts 响应或 normalize 后的结构。")


def summarize_videos(videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "video_id": v.get("video_id"),
            "video_url": v.get("video_url"),
            "caption": v.get("caption"),
            "views": v.get("views"),
            "like_rate": round(rate(v, "likes"), 4),
            "comment_rate": round(rate(v, "comments"), 4),
            "share_rate": round(rate(v, "shares"), 4),
            "save_rate": round(rate(v, "saves"), 4),
        }
        for v in videos
    ]


def hashtag_signal(counter: Counter[str]) -> str:
    if not counter:
        return "近期视频未发现稳定 hashtag，建议观察文案后续走向。"
    tag, count = counter.most_common(1)[0]
    if count >= 6:
        return f"近期视频中 #{tag} 出现 {count} 次，可能是该账号当前主推方向。"
    return f"出现频率最高的 hashtag 是 #{tag}，建议继续观察是否形成稳定标签。"


def account_value(last_7: int, viral_count: int, themes: list[str], hashtags: Counter[str]) -> str:
    relevant = any(t in themes for t in ("痛点解决类", "使用教程类", "运动场景类", "产品展示类"))
    if last_7 >= 4 and viral_count >= 2 and relevant and hashtags:
        return "适合持续监控。原因：发布稳定且近期有多条高播放内容，方向与产品/场景类高度相关。"
    if viral_count >= 2:
        return "值得阶段性监控。原因：存在爆款内容，但仍需观察发布稳定性和方向相关度。"
    return "建议低频观察。原因：当前爆款密度一般，需等待更多近期内容验证。"


def analyze_video_response(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = coerce_normalized(payload)
    creator = normalized.get("creator") or {}
    videos = normalized.get("videos") or []
    if not videos:
        raise SystemExit("没有可分析的视频。")

    current = now_utc()
    publish_times = [pt for pt in (parse_time(v.get("publish_time")) for v in videos) if pt]
    last_7 = sum(1 for item in publish_times if current - item <= timedelta(days=7))
    last_30 = sum(1 for item in publish_times if current - item <= timedelta(days=30))
    sorted_times = sorted(publish_times)
    if len(sorted_times) > 1:
        span_days = max((sorted_times[-1] - sorted_times[0]).total_seconds() / 86400, 1)
        avg_days = round(span_days / (len(sorted_times) - 1), 1)
    else:
        avg_days = None

    theme_counter: Counter[str] = Counter()
    hashtag_counter: Counter[str] = Counter()
    pain_counter: Counter[str] = Counter()
    scene_counter: Counter[str] = Counter()
    for v in videos:
        theme_counter.update(classify_video(v))
        hashtag_counter.update(v.get("hashtags", []) or [])
        text = combined_text(v)
        for word in ("knee pain", "sore knees", "hurt", "pain", "recovery", "support",
                     "痛", "疼", "酸", "缓解"):
            if word in text:
                pain_counter[word] += 1
        for word in ("running", "workout", "gym", "leg day", "training",
                     "跑步", "健身", "训练", "运动"):
            if word in text:
                scene_counter[word] += 1

    top_by_views = top_items(videos, "views")
    max_views = int(top_by_views[0].get("views", 0)) if top_by_views else 0
    viral_count = sum(1 for v in videos if max_views and int(v.get("views", 0)) >= max_views * 0.55)
    hook_examples = [v.get("caption", "") for v in top_by_views[:3]]
    top_themes = [t for t, _c in theme_counter.most_common(3)]
    top_hashtags = [t for t, _c in hashtag_counter.most_common(5)]
    if last_7 == 0:
        frequency_signal = "最近 7 天未发布，存在停更信号"
    elif last_7 >= 5:
        frequency_signal = "发布频率明显提升，疑似正在测试新品或活动内容"
    else:
        frequency_signal = "发布节奏相对稳定"

    return {
        "creator": creator,
        "creator_id": creator.get("creator_id"),
        "username": creator.get("username"),
        "video_count": len(videos),
        "frequency": {
            "last_7_days": last_7,
            "last_30_days": last_30,
            "avg_days_per_video": avg_days,
            "signal": frequency_signal,
        },
        "viral": {
            "max_views": max_views,
            "viral_count": viral_count,
            "top_views": summarize_videos(top_by_views),
            "top_like_rate": summarize_videos(top_items(videos, "likes")),
            "top_share_rate": summarize_videos(top_items(videos, "shares")),
            "top_comment_rate": summarize_videos(top_items(videos, "comments")),
            "top_save_rate": summarize_videos(top_items(videos, "saves")),
        },
        "themes": theme_counter.most_common(),
        "top_themes": top_themes,
        "hooks": {
            "examples": hook_examples,
            "patterns": ["痛点句", "疑问句", "强指令", "直接展示结果"],
        },
        "tag_signals": {
            "top_hashtags": top_hashtags,
            "signal": hashtag_signal(hashtag_counter),
        },
        "keywords": {
            "hashtags": hashtag_counter.most_common(10),
            "pain_words": pain_counter.most_common(10),
            "scene_words": scene_counter.most_common(10),
        },
        "structure": "痛点开头 -> 展示使用场景 -> 产品解决方案 -> 使用演示 -> 结果展示 -> 引导评论/购买",
        "account_value": account_value(last_7, viral_count, top_themes, hashtag_counter),
    }


def build_profile_line(creator: dict[str, Any]) -> str:
    follower = creator.get("follower_count")
    aweme = creator.get("aweme_count")
    parts: list[str] = []
    if follower is not None:
        parts.append(f"粉丝 {format_number(follower)}")
    if aweme is not None:
        parts.append(f"作品 {format_number(aweme)}")
    return "（" + "，".join(parts) + "）" if parts else ""


def build_header(creator: dict[str, Any], remark: str, focus: str, video_count: int) -> str:
    label = FOCUS_LABELS.get(focus, focus)
    return (
        f"已加入监控：@{creator.get('username','')} {creator.get('nickname','')}{build_profile_line(creator)}\n"
        f"备注：{remark or '无'}\n"
        f"分析方向：{label}（最近 {video_count} 条视频）\n"
    )


def build_footer(creator: dict[str, Any]) -> str:
    return f"\n建议：是否要把该账号加入每日监控？回复\"加入每日监控 @{creator.get('username','')}\"即可。"


def build_overall_report(creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    frequency = analysis["frequency"]
    viral = analysis["viral"]
    themes = "、".join(analysis["top_themes"]) or "暂未归类"
    hashtags = "、".join(f"#{t}" for t in analysis["tag_signals"]["top_hashtags"]) or "暂无明显 hashtag"
    hook = analysis["hooks"]["examples"][0] if analysis["hooks"]["examples"] else "暂无样例"
    top_videos = analysis["viral"]["top_views"][:3]
    top_lines = "\n".join(
        f"   - {v['video_id']}：{format_number(v['views'])} 播放，{v['caption']}"
        for v in top_videos
    )

    body = (
        f"\n1. 发布频率：\n"
        f"最近 7 天发布 {frequency['last_7_days']} 条，最近 30 天发布 {frequency['last_30_days']} 条，"
        f"平均 {format_number(frequency['avg_days_per_video'])} 天一条。{frequency['signal']}。\n\n"
        f"2. 爆款表现：\n"
        f"最高播放 {format_number(viral['max_views'])}，有 {viral['viral_count']} 条明显跑出。Top 3：\n"
        f"{top_lines}\n\n"
        f"3. 内容方向：\n"
        f"主要内容为 {themes}。\n\n"
        f"4. 爆款开头：\n"
        f"高播放视频常用痛点/疑问/强指令开头，例如：\"{hook}\"。\n\n"
        f"5. 标签线索：\n"
        f"高频 hashtag：{hashtags}。{analysis['tag_signals']['signal']}\n\n"
        f"6. 内容结构：\n"
        f"{analysis['structure']}。\n\n"
        f"7. 账号价值判断：\n"
        f"{analysis['account_value']}"
    )
    return (
        build_header(creator, remark, "overall", analysis["video_count"])
        + body
        + build_footer(creator)
    )


def build_posting_report(creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    posting = analysis.get("posting") or {}
    frequency = analysis["frequency"]
    slots = posting.get("top_slots") or []
    cadence = posting.get("weekly_trend") or []
    durations = posting.get("duration_buckets") or []
    viral_window = posting.get("viral_window") or {}

    if slots:
        slot_lines = "\n".join(
            f"   - {item['weekday']} {item['hour']:02d}:00 — {item['count']} 条，平均播放 {format_number(item['avg_views'])}"
            for item in slots
        )
    else:
        slot_lines = "   - 暂无足够样本判断时段。"

    if cadence:
        cadence_lines = "\n".join(
            f"   - {item['week']}：发布 {item['count']} 条"
            for item in cadence
        )
    else:
        cadence_lines = "   - 暂无足够样本。"

    if durations:
        duration_lines = "\n".join(
            f"   - {item['label']}：{item['count']} 条，平均播放 {format_number(item['avg_views'])}"
            for item in durations
        )
    else:
        duration_lines = "   - 暂无时长数据。"

    viral_summary = viral_window.get("summary") or "样本不足，无法判断爆款是否集中在固定时段。"

    body = (
        f"\n1. 发布节奏：\n"
        f"最近 7 天 {frequency['last_7_days']} 条，最近 30 天 {frequency['last_30_days']} 条，"
        f"平均 {format_number(frequency['avg_days_per_video'])} 天一条。{frequency['signal']}。\n\n"
        f"2. 发布时段画像（Top 3 时段）：\n{slot_lines}\n\n"
        f"3. 周度发布趋势（最近 4 周）：\n{cadence_lines}\n\n"
        f"4. 时长策略：\n{duration_lines}\n\n"
        f"5. 爆款时间窗：\n   {viral_summary}\n\n"
        f"6. 策略判断：\n   {posting.get('verdict','暂无判断')}"
    )
    return (
        build_header(creator, remark, "posting", analysis["video_count"])
        + body
        + build_footer(creator)
    )


def build_content_report(creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    content = analysis.get("content") or {}
    themes = "、".join(analysis["top_themes"]) or "暂未归类"
    hashtags = "、".join(f"#{t}" for t in analysis["tag_signals"]["top_hashtags"]) or "暂无明显 hashtag"
    hooks = content.get("hook_distribution") or []
    sample_hooks = content.get("hook_examples") or analysis["hooks"]["examples"][:3]
    durations = content.get("duration_engagement") or []
    engagement = content.get("engagement_profile") or {}
    caption_style = content.get("caption_style") or {}

    if hooks:
        hook_lines = "\n".join(
            f"   - {item['pattern']}：{item['count']} / {item['total']} 条（{item['ratio']*100:.0f}%）"
            for item in hooks
        )
    else:
        hook_lines = "   - 暂未匹配到显著钩子句式。"

    if sample_hooks:
        hook_examples = "\n".join(f"   - \"{c}\"" for c in sample_hooks)
    else:
        hook_examples = "   - 暂无样例。"

    if durations:
        duration_lines = "\n".join(
            f"   - {item['label']}：{item['count']} 条，平均播放 {format_number(item['avg_views'])}，"
            f"平均互动率 {item['avg_engagement']*100:.2f}%"
            for item in durations
        )
    else:
        duration_lines = "   - 暂无时长数据。"

    engagement_strong = engagement.get("strongest", "暂无")
    engagement_line = (
        f"点赞率 {engagement.get('like_rate',0)*100:.2f}%，"
        f"评论率 {engagement.get('comment_rate',0)*100:.2f}%，"
        f"分享率 {engagement.get('share_rate',0)*100:.2f}%，"
        f"收藏率 {engagement.get('save_rate',0)*100:.2f}%"
    )

    body = (
        f"\n1. 内容方向：\n   {themes}\n\n"
        f"2. 开头钩子分布：\n{hook_lines}\n\n"
        f"3. 爆款开头样例：\n{hook_examples}\n\n"
        f"4. 时长 × 互动：\n{duration_lines}\n\n"
        f"5. 互动率画像：\n   {engagement_line}。该账号最强项是「{engagement_strong}」。\n\n"
        f"6. 文案风格：\n   平均字数 {caption_style.get('avg_length',0)}，标准差 {caption_style.get('stddev',0)}。"
        f"风格倾向：{caption_style.get('verdict','暂无判断')}\n\n"
        f"7. 标签线索：\n   {hashtags}。{analysis['tag_signals']['signal']}"
    )
    return (
        build_header(creator, remark, "content", analysis["video_count"])
        + body
        + build_footer(creator)
    )


def build_report_text(focus: str, creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    if focus == "posting":
        return build_posting_report(creator, remark, analysis)
    if focus == "content":
        return build_content_report(creator, remark, analysis)
    return build_overall_report(creator, remark, analysis)


# 兼容旧调用
def build_reply_text(creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    return build_overall_report(creator, remark, analysis)


# -------------------- focus 专属分析器 --------------------

def compute_posting(normalized: dict[str, Any]) -> dict[str, Any]:
    videos = normalized.get("videos") or []
    publish_pairs = []
    for v in videos:
        pt = parse_time(v.get("publish_time"))
        if pt:
            publish_pairs.append((pt, v))

    slot_aggregator: dict[tuple[int, int], dict[str, Any]] = {}
    for pt, v in publish_pairs:
        key = (pt.weekday(), pt.hour)
        bucket = slot_aggregator.setdefault(key, {"count": 0, "views_sum": 0})
        bucket["count"] += 1
        bucket["views_sum"] += int(v.get("views") or 0)

    top_slots = sorted(
        (
            {
                "weekday": WEEKDAY_NAMES[k[0]],
                "hour": k[1],
                "count": b["count"],
                "avg_views": b["views_sum"] // b["count"] if b["count"] else 0,
            }
            for k, b in slot_aggregator.items()
        ),
        key=lambda item: (item["count"], item["avg_views"]),
        reverse=True,
    )[:3]

    weekly_buckets: dict[str, int] = {}
    if publish_pairs:
        latest = max(pt for pt, _ in publish_pairs)
        anchor = latest.replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(4):
            start = anchor - timedelta(days=(i + 1) * 7 - 1)
            end = anchor - timedelta(days=i * 7)
            label = f"第 {4 - i} 周（{start.strftime('%m-%d')} ~ {end.strftime('%m-%d')}）"
            count = sum(1 for pt, _ in publish_pairs if start <= pt <= end + timedelta(days=1) - timedelta(seconds=1))
            weekly_buckets[label] = count
    weekly_trend = [{"week": k, "count": v} for k, v in weekly_buckets.items()]

    duration_buckets = compute_duration_buckets(videos, include_engagement=False)

    viral_top = sorted(videos, key=lambda v: int(v.get("views") or 0), reverse=True)[:5]
    viral_pairs = []
    for v in viral_top:
        pt = parse_time(v.get("publish_time"))
        if pt:
            viral_pairs.append((pt, v))
    viral_window: dict[str, Any] = {}
    if viral_pairs:
        weekday_counter = Counter(WEEKDAY_NAMES[pt.weekday()] for pt, _ in viral_pairs)
        hour_counter = Counter(pt.hour for pt, _ in viral_pairs)
        top_weekday, top_weekday_count = weekday_counter.most_common(1)[0]
        top_hour, top_hour_count = hour_counter.most_common(1)[0]
        if top_weekday_count >= 3:
            summary = f"Top5 爆款中 {top_weekday_count} 条出现在 {top_weekday}，集中度较高。"
        elif top_hour_count >= 3:
            summary = f"Top5 爆款中 {top_hour_count} 条出现在 {top_hour:02d}:00 前后，时段集中。"
        else:
            summary = "Top5 爆款时段分散，未观察到明显的爆款时间窗。"
        viral_window = {
            "summary": summary,
            "weekday_distribution": weekday_counter.most_common(),
            "hour_distribution": hour_counter.most_common(),
        }

    cadence_total = sum(b["count"] for b in weekly_trend) if weekly_trend else 0
    if not publish_pairs:
        verdict = "样本不足，无法判断发布策略。"
    elif cadence_total >= 12:
        verdict = "发布频率高且稳定，适合密集监控。"
    elif cadence_total <= 4:
        verdict = "发布频率较低，更新窗口稀疏，建议低频观察。"
    else:
        verdict = "发布节奏处于中等水平，建议保留监控并关注是否有节奏拐点。"

    return {
        "top_slots": top_slots,
        "weekly_trend": weekly_trend,
        "duration_buckets": duration_buckets,
        "viral_window": viral_window,
        "verdict": verdict,
    }


def compute_duration_buckets(videos: list[dict[str, Any]], include_engagement: bool) -> list[dict[str, Any]]:
    bucket_def = (
        ("短视频 (<15s)", lambda d: d < 15),
        ("中视频 (15-60s)", lambda d: 15 <= d <= 60),
        ("长视频 (>60s)", lambda d: d > 60),
    )
    rows: list[dict[str, Any]] = []
    for label, predicate in bucket_def:
        bucket_videos = [v for v in videos if predicate(float(v.get("duration") or 0))]
        if not bucket_videos:
            continue
        avg_views = sum(int(v.get("views") or 0) for v in bucket_videos) // len(bucket_videos)
        row = {"label": label, "count": len(bucket_videos), "avg_views": avg_views}
        if include_engagement:
            engagement_total = 0.0
            for v in bucket_videos:
                engagement_total += rate(v, "likes") + rate(v, "comments") + rate(v, "shares") + rate(v, "saves")
            row["avg_engagement"] = engagement_total / len(bucket_videos)
        rows.append(row)
    return rows


def compute_content(normalized: dict[str, Any], base_analysis: dict[str, Any]) -> dict[str, Any]:
    videos = normalized.get("videos") or []
    sorted_by_views = sorted(videos, key=lambda v: int(v.get("views") or 0), reverse=True)
    top_n = sorted_by_views[: min(10, len(sorted_by_views))]
    total = len(top_n)

    hook_distribution: list[dict[str, Any]] = []
    if total:
        for label, predicate in HOOK_PATTERNS:
            count = sum(1 for v in top_n if predicate(v.get("caption") or ""))
            if count:
                hook_distribution.append({
                    "pattern": label,
                    "count": count,
                    "total": total,
                    "ratio": count / total,
                })
        hook_distribution.sort(key=lambda item: item["count"], reverse=True)

    duration_engagement = compute_duration_buckets(videos, include_engagement=True)

    if videos:
        avg = {
            "like_rate": sum(rate(v, "likes") for v in videos) / len(videos),
            "comment_rate": sum(rate(v, "comments") for v in videos) / len(videos),
            "share_rate": sum(rate(v, "shares") for v in videos) / len(videos),
            "save_rate": sum(rate(v, "saves") for v in videos) / len(videos),
        }
        strongest_key = max(avg, key=avg.get)
        strongest_label = {
            "like_rate": "点赞驱动",
            "comment_rate": "评论互动",
            "share_rate": "社交传播",
            "save_rate": "收藏价值",
        }[strongest_key]
        engagement_profile = {**avg, "strongest": strongest_label}
    else:
        engagement_profile = {}

    captions = [v.get("caption", "") for v in videos]
    if captions:
        lengths = [len(c) for c in captions]
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        stddev = variance ** 0.5
        if stddev < 8:
            caption_verdict = "文案高度模板化，可复用脚本"
        elif stddev > 30:
            caption_verdict = "文案差异大，倾向个性化创作"
        else:
            caption_verdict = "文案有一定模板，但保留个性化空间"
        caption_style = {
            "avg_length": round(avg_length, 1),
            "stddev": round(stddev, 1),
            "verdict": caption_verdict,
        }
    else:
        caption_style = {}

    return {
        "hook_distribution": hook_distribution,
        "hook_examples": [v.get("caption", "") for v in top_n[:3]],
        "duration_engagement": duration_engagement,
        "engagement_profile": engagement_profile,
        "caption_style": caption_style,
    }


def analyze_with_focus(payload: dict[str, Any], focus: str) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = coerce_normalized(payload)
    base = analyze_video_response(normalized)
    if focus == "posting":
        base["posting"] = compute_posting(normalized)
    elif focus == "content":
        base["content"] = compute_content(normalized, base)
    base["focus"] = focus
    return normalized, base


# -------------------- digest 聚合 --------------------

def previous_day(day: str) -> str:
    parsed = datetime.strptime(day, "%Y-%m-%d").date()
    return (parsed - timedelta(days=1)).strftime("%Y-%m-%d")


def diff_creator(today: dict[str, Any], yesterday: dict[str, Any] | None) -> dict[str, Any]:
    today_creator = today.get("creator") or {}
    today_videos = today.get("videos") or []
    yesterday_videos = (yesterday or {}).get("videos") or []
    yesterday_creator = (yesterday or {}).get("creator") or {}

    yesterday_views = {v.get("video_id"): int(v.get("views") or 0) for v in yesterday_videos}
    yesterday_video_ids = set(yesterday_views.keys())

    follower_today = today_creator.get("follower_count")
    follower_yesterday = yesterday_creator.get("follower_count") if yesterday else None
    follower_delta = (
        follower_today - follower_yesterday
        if isinstance(follower_today, int) and isinstance(follower_yesterday, int)
        else None
    )

    aweme_today = today_creator.get("aweme_count")
    aweme_yesterday = yesterday_creator.get("aweme_count") if yesterday else None
    aweme_delta = (
        aweme_today - aweme_yesterday
        if isinstance(aweme_today, int) and isinstance(aweme_yesterday, int)
        else None
    )

    new_videos = [
        v for v in today_videos
        if v.get("video_id") and v["video_id"] not in yesterday_video_ids
    ]

    video_diffs = []
    for v in today_videos:
        vid = v.get("video_id")
        views_today = int(v.get("views") or 0)
        views_yesterday = yesterday_views.get(vid)
        delta = views_today - views_yesterday if views_yesterday is not None else None
        video_diffs.append({
            "video_id": vid,
            "video_url": v.get("video_url"),
            "caption": v.get("caption"),
            "publish_time": v.get("publish_time"),
            "views_today": views_today,
            "views_yesterday": views_yesterday,
            "views_delta": delta,
            "is_new": vid not in yesterday_video_ids,
        })

    biggest_view_jump = None
    delta_candidates = [d for d in video_diffs if d["views_delta"] is not None]
    if delta_candidates:
        biggest_view_jump = max(delta_candidates, key=lambda d: d["views_delta"])

    top_today = max(today_videos, key=lambda v: int(v.get("views") or 0), default=None)

    publish_times = [pt for pt in (parse_time(v.get("publish_time")) for v in today_videos) if pt]
    current = now_utc()
    last_7 = sum(1 for t in publish_times if current - t <= timedelta(days=7))
    days_since_last = None
    if publish_times:
        last_publish = max(publish_times)
        days_since_last = (current - last_publish).days

    status = "ok"
    if days_since_last is not None and days_since_last >= STALL_DAYS:
        status = "stall"
    elif last_7 >= SURGE_WEEK_THRESHOLD:
        status = "surge"

    return {
        "creator": today_creator,
        "follower_today": follower_today,
        "follower_delta": follower_delta,
        "aweme_today": aweme_today,
        "aweme_delta": aweme_delta,
        "new_video_count": len(new_videos),
        "new_videos": new_videos[:5],
        "video_diffs": video_diffs,
        "biggest_view_jump": biggest_view_jump,
        "top_today": (
            {
                "video_id": top_today.get("video_id"),
                "video_url": top_today.get("video_url"),
                "caption": top_today.get("caption"),
                "views": int(top_today.get("views") or 0),
            }
            if top_today else None
        ),
        "last_7_days_posts": last_7,
        "days_since_last_post": days_since_last,
        "status": status,
        "has_yesterday": yesterday is not None,
    }


def build_digest(group_id: str, day: str) -> dict[str, Any]:
    monitors = list_monitors(group_id=group_id, daily_only=True)
    yday = previous_day(day)
    creator_diffs: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for monitor in monitors:
        creator = monitor.get("creator") or {}
        creator_id = creator.get("creator_id") or creator.get("username") or ""
        today_snap = load_snapshot(group_id, creator_id, day)
        if not today_snap:
            missing.append({
                "username": creator.get("username"),
                "nickname": creator.get("nickname"),
                "remark": monitor.get("remark"),
            })
            continue
        yesterday_snap = load_snapshot(group_id, creator_id, yday)
        diff = diff_creator(today_snap, yesterday_snap)
        diff["remark"] = monitor.get("remark", "")
        creator_diffs.append(diff)

    follower_gainers = sorted(
        [c for c in creator_diffs if isinstance(c.get("follower_delta"), int)],
        key=lambda c: c["follower_delta"], reverse=True,
    )[:3]

    new_viral = []
    for c in creator_diffs:
        for v in c.get("new_videos", []):
            new_viral.append({
                "username": c["creator"].get("username"),
                "nickname": c["creator"].get("nickname"),
                "video_id": v.get("video_id"),
                "video_url": v.get("video_url"),
                "caption": v.get("caption"),
                "views": int(v.get("views") or 0),
            })
    new_viral.sort(key=lambda item: item["views"], reverse=True)
    new_viral_top = new_viral[:5]

    biggest_jumps = sorted(
        [
            {
                "username": c["creator"].get("username"),
                "nickname": c["creator"].get("nickname"),
                **c["biggest_view_jump"],
            }
            for c in creator_diffs
            if c.get("biggest_view_jump") and c["biggest_view_jump"]["views_delta"] is not None and c["biggest_view_jump"]["views_delta"] > 0
        ],
        key=lambda item: item["views_delta"], reverse=True,
    )[:3]

    stalled = [c for c in creator_diffs if c["status"] == "stall"]
    surged = [c for c in creator_diffs if c["status"] == "surge"]

    summary = {
        "monitors_total": len(monitors),
        "fetched": len(creator_diffs),
        "missing": len(missing),
        "new_videos_total": sum(c["new_video_count"] for c in creator_diffs),
        "with_yesterday": sum(1 for c in creator_diffs if c["has_yesterday"]),
    }

    digest = {
        "group_id": group_id,
        "date": day,
        "previous_date": yday,
        "summary": summary,
        "highlights": {
            "follower_gainers": [
                {
                    "username": c["creator"].get("username"),
                    "nickname": c["creator"].get("nickname"),
                    "follower_delta": c["follower_delta"],
                    "follower_today": c["follower_today"],
                }
                for c in follower_gainers if c["follower_delta"] is not None and c["follower_delta"] != 0
            ],
            "new_viral": new_viral_top,
            "biggest_view_jumps": biggest_jumps,
            "stalled": [
                {
                    "username": c["creator"].get("username"),
                    "nickname": c["creator"].get("nickname"),
                    "days_since_last_post": c["days_since_last_post"],
                }
                for c in stalled
            ],
            "surged": [
                {
                    "username": c["creator"].get("username"),
                    "nickname": c["creator"].get("nickname"),
                    "last_7_days_posts": c["last_7_days_posts"],
                }
                for c in surged
            ],
        },
        "creators": [
            {
                "username": c["creator"].get("username"),
                "nickname": c["creator"].get("nickname"),
                "remark": c.get("remark", ""),
                "follower_today": c["follower_today"],
                "follower_delta": c["follower_delta"],
                "new_videos": c["new_video_count"],
                "top_today": c["top_today"],
                "biggest_view_jump": c["biggest_view_jump"],
                "status": c["status"],
                "has_yesterday": c["has_yesterday"],
            }
            for c in creator_diffs
        ],
        "missing": missing,
    }
    digest["reply_text"] = build_digest_text(digest)
    return digest


def build_digest_text(digest: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = digest["summary"]
    highlights = digest["highlights"]
    creators = digest["creators"]
    yday = digest["previous_date"]
    today = digest["date"]

    lines.append(f"【TikTok 监控日报】{today}（对照 {yday}）")
    lines.append(
        f"群内监控 {summary['monitors_total']} 个达人，今日成功抓取 {summary['fetched']} 个，"
        f"新增视频共 {summary['new_videos_total']} 条。"
    )
    if summary["missing"]:
        lines.append(f"今日有 {summary['missing']} 个达人未抓取到数据，详见末尾。")
    if summary["with_yesterday"] < summary["fetched"]:
        lines.append(
            f"其中 {summary['fetched'] - summary['with_yesterday']} 个达人无昨日数据，"
            f"无法做对比，仅展示今日值。"
        )
    lines.append("")

    lines.append("一、涨粉 Top")
    if highlights["follower_gainers"]:
        for item in highlights["follower_gainers"]:
            lines.append(
                f"  - @{item['username']} {item.get('nickname','')}："
                f"{format_delta(item['follower_delta'])}（当前 {format_number(item['follower_today'])}）"
            )
    else:
        lines.append("  无明显涨粉变化。")
    lines.append("")

    lines.append("二、新爆款 Top")
    if highlights["new_viral"]:
        for item in highlights["new_viral"]:
            lines.append(
                f"  - @{item['username']}：{format_number(item['views'])} 播放 — {item['caption']}"
            )
    else:
        lines.append("  今日暂无新视频。")
    lines.append("")

    lines.append("三、播放量增长 Top（同一视频对比昨日）")
    if highlights["biggest_view_jumps"]:
        for item in highlights["biggest_view_jumps"]:
            lines.append(
                f"  - @{item['username']}：{format_delta(item['views_delta'])} 播放 — {item['caption']}"
            )
    else:
        lines.append("  暂无可对比的视频增长。")
    lines.append("")

    if highlights["stalled"] or highlights["surged"]:
        lines.append("四、异常信号")
        for item in highlights["stalled"]:
            days = item.get("days_since_last_post")
            lines.append(
                f"  - 停更：@{item['username']} 已 {days} 天未发布。"
            )
        for item in highlights["surged"]:
            lines.append(
                f"  - 高频发布：@{item['username']} 最近 7 天发了 {item['last_7_days_posts']} 条。"
            )
        lines.append("")

    lines.append("五、逐账号速览")
    if creators:
        for c in creators:
            arrow = "→"
            if isinstance(c["follower_delta"], int) and c["follower_delta"] != 0:
                arrow = "↑" if c["follower_delta"] > 0 else "↓"
            top = c.get("top_today") or {}
            top_view = format_number(top.get("views")) if top else "-"
            new_n = c["new_videos"]
            line = (
                f"  - @{c['username']} {c.get('nickname','')}：粉丝 {arrow} {format_delta(c['follower_delta'])}，"
                f"新增 {new_n} 条，今日最高 {top_view} 播放"
            )
            if c["status"] == "stall":
                line += "（停更预警）"
            elif c["status"] == "surge":
                line += "（高频发布）"
            if not c["has_yesterday"]:
                line += "（首日无对比）"
            lines.append(line)
    else:
        lines.append("  本群尚无每日监控达人。")

    if digest.get("missing"):
        lines.append("")
        lines.append("六、未抓取到数据")
        for item in digest["missing"]:
            lines.append(f"  - @{item['username']} {item.get('nickname','')}")

    return "\n".join(lines)


# -------------------- 教程 --------------------

TUTORIAL_TEXT = """【如何添加 TikTok 监控】

1. 找到对方的 TikTok 主页链接，例如 https://www.tiktok.com/@mrbeast，
   或者直接发送 @mrbeast、mrbeast 也可以。
2. 在群里 @机器人，发送：
       添加监控 https://www.tiktok.com/@mrbeast 备注：对标账号
   机器人会立刻拉取最近 40 条视频，并给出账号画像、爆款 Top3、内容方向等分析。
3. 分析返回后，机器人会询问"是否加入每日监控"。回复"加入每日监控 @mrbeast"即可订阅。
   订阅后，每天早上 8 点会在群里发送一份昨日 vs 今日的内容情报日报。
4. 想查看本群当前监控了哪些达人，发送：查看监控列表
5. 想取消某个达人的每日订阅，发送：取消每日监控 @mrbeast
6. 想完全移除监控，发送：移除监控 @mrbeast

提示：
- 不同群的监控列表互相独立。
- 每日日报包含涨粉 Top、新爆款 Top、播放量增长 Top、停更/高频发布预警，以及逐账号速览。
- 第一天加入的达人，次日才能产生对比数据。
- 想换个分析视角，可以加方向，例如：
    添加监控 @mrbeast 方向：发布策略
    添加监控 @mrbeast 方向：内容形式
  默认是综合画像。"""


# -------------------- 命令处理器 --------------------

def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def command_tutorial(args: argparse.Namespace) -> None:
    if args.format == "text":
        print(TUTORIAL_TEXT)
    else:
        print_json({"reply_text": TUTORIAL_TEXT})


def command_add(args: argparse.Namespace) -> None:
    unique_id = parse_unique_id(args.input)
    raw = fetch_posts(unique_id, args.count)
    normalized = normalize_response(raw)
    monitor = upsert_monitor(normalized["creator"], args)
    snapshot_file = save_snapshot(args.group_id, normalized, today_str(args.date))
    _, analysis = analyze_with_focus(normalized, args.focus)
    reply_text = build_report_text(args.focus, normalized["creator"], args.remark, analysis)

    if args.format == "text":
        print(reply_text)
        return

    output: dict[str, Any] = {
        "monitor": {
            "monitor_id": monitor["monitor_id"],
            "group_id": monitor["group_id"],
            "creator": normalized["creator"],
            "remark": monitor.get("remark", ""),
            "daily_enabled": monitor.get("daily_enabled", False),
            "store_path": str(store_path()),
            "snapshot_path": str(snapshot_file),
        },
        "analysis": analysis,
        "reply_text": reply_text,
    }
    if args.include_videos:
        output["videos"] = normalized["videos"]
    if args.include_raw:
        output["raw"] = raw
    print_json(output)


def command_videos(args: argparse.Namespace) -> None:
    unique_id = parse_unique_id(args.input)
    raw = fetch_posts(unique_id, args.count)
    if args.raw:
        print_json(raw)
    else:
        print_json(normalize_response(raw))


def command_analyze(args: argparse.Namespace) -> None:
    require_api_key()
    with open(args.input_json, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    normalized, analysis = analyze_with_focus(payload, args.focus)
    if args.format == "text":
        print(build_report_text(args.focus, normalized.get("creator") or {}, args.remark, analysis))
    else:
        print_json(analysis)


def command_list(args: argparse.Namespace) -> None:
    monitors = list_monitors(group_id=args.group_id, daily_only=args.daily_only)
    if args.format == "json":
        print_json({
            "group_id": args.group_id,
            "daily_only": args.daily_only,
            "monitors": monitors,
        })
        return

    if not monitors:
        scope = f"群 {args.group_id} " if args.group_id else ""
        suffix = "（仅每日订阅）" if args.daily_only else ""
        print(f"{scope}暂无监控记录{suffix}。")
        return

    header = f"群 {args.group_id} " if args.group_id else "全部 "
    suffix = "（每日订阅）" if args.daily_only else ""
    print(f"{header}监控列表 共 {len(monitors)} 个{suffix}：")
    for m in monitors:
        creator = m.get("creator") or {}
        flag = "✓" if m.get("daily_enabled") else "·"
        print(
            f"  [{flag}] @{creator.get('username','')} {creator.get('nickname','')}"
            f"  备注：{m.get('remark','')}"
        )
    print("说明：✓ = 已加入每日监控，· = 仅手动查询。")


def command_enable_daily(args: argparse.Namespace) -> None:
    unique_id = parse_unique_id(args.input)
    monitor = update_monitor(args.group_id, unique_id, daily_enabled=True)
    creator = monitor.get("creator") or {}
    if args.format == "text":
        print(f"已加入每日监控：@{creator.get('username','')} {creator.get('nickname','')}。"
              f"明日早 8 点会出现在本群日报中。")
    else:
        print_json({"monitor_id": monitor["monitor_id"], "daily_enabled": True})


def command_disable_daily(args: argparse.Namespace) -> None:
    unique_id = parse_unique_id(args.input)
    monitor = update_monitor(args.group_id, unique_id, daily_enabled=False)
    creator = monitor.get("creator") or {}
    if args.format == "text":
        print(f"已退出每日监控：@{creator.get('username','')} {creator.get('nickname','')}。"
              f"该达人仍保留在监控列表中，可手动查询。")
    else:
        print_json({"monitor_id": monitor["monitor_id"], "daily_enabled": False})


def command_remove(args: argparse.Namespace) -> None:
    unique_id = parse_unique_id(args.input)
    monitor = remove_monitor(args.group_id, unique_id)
    creator = monitor.get("creator") or {}
    if args.format == "text":
        print(f"已移除监控：@{creator.get('username','')} {creator.get('nickname','')}。")
    else:
        print_json({"removed_monitor_id": monitor["monitor_id"]})


def command_snapshot(args: argparse.Namespace) -> None:
    unique_id = parse_unique_id(args.input)
    raw = fetch_posts(unique_id, args.count)
    normalized = normalize_response(raw)
    monitor = find_monitor(load_store(store_path())["monitors"], args.group_id, unique_id)
    if monitor:
        update_monitor(args.group_id, unique_id, creator=normalized["creator"])
    path = save_snapshot(args.group_id, normalized, today_str(args.date))
    if args.format == "text":
        print(f"已写入快照：{path}")
    else:
        print_json({
            "group_id": args.group_id,
            "username": unique_id,
            "date": today_str(args.date),
            "snapshot_path": str(path),
            "video_count": len(normalized.get("videos") or []),
        })


def command_digest(args: argparse.Namespace) -> None:
    digest = build_digest(args.group_id, today_str(args.date))
    if args.format == "text":
        print(digest["reply_text"])
    else:
        print_json(digest)


# -------------------- main --------------------

def add_count_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--count", "--limit", dest="count", type=int, default=40,
                        help="拉取最近视频条数，默认 40。")


def add_format_argument(parser: argparse.ArgumentParser, default: str = "text") -> None:
    parser.add_argument("--format", choices=("json", "text"), default=default, help="输出格式。")


def add_focus_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--focus",
        choices=FOCUS_CHOICES,
        default="overall",
        help="分析方向：overall=综合画像（默认），posting=发布策略，content=内容形式。",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="灵途 TikTok 达人监控。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("tutorial", help="输出添加监控的中文教程文本。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_tutorial)

    p = subparsers.add_parser("add", help="添加达人到监控列表，并返回即时分析。")
    p.add_argument("--input", required=True, help="TikTok 主页 URL、@username 或裸名。")
    p.add_argument("--remark", default="", help="备注。")
    p.add_argument("--source", default="feishu_group", help="来源渠道。")
    p.add_argument("--group-id", required=True, help="群 ID（多群隔离主键）。")
    p.add_argument("--team-id", default="", help="团队 ID。")
    p.add_argument("--operator-id", default="default_user", help="操作人 ID。")
    add_count_argument(p)
    p.add_argument("--date", default="", help="快照日期，默认今天 (YYYY-MM-DD)。")
    add_focus_argument(p)
    p.add_argument("--include-videos", action="store_true", help="JSON 输出附带 normalize 后的视频列表。")
    p.add_argument("--include-raw", action="store_true", help="JSON 输出附带原始 fetchPosts 响应。")
    add_format_argument(p, default="json")
    p.set_defaults(func=command_add)

    p = subparsers.add_parser("videos", help="拉取达人最近视频。")
    p.add_argument("--input", required=True, help="TikTok 主页 URL、@username 或裸名。")
    add_count_argument(p)
    p.add_argument("--raw", action="store_true", help="输出原始 fetchPosts 响应而非 normalize 结果。")
    p.set_defaults(func=command_videos)

    p = subparsers.add_parser("analyze", help="分析一份 fetchPosts JSON（原始或 normalize）。")
    p.add_argument("--input-json", required=True, help="JSON 文件路径。")
    p.add_argument("--remark", default="", help="文本输出时附加的备注。")
    add_focus_argument(p)
    add_format_argument(p, default="json")
    p.set_defaults(func=command_analyze)

    p = subparsers.add_parser("list", help="列出某群的监控记录。")
    p.add_argument("--group-id", default=None, help="群 ID，留空则列出全部。")
    p.add_argument("--daily-only", action="store_true", help="只显示已开启每日监控的达人。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_list)

    p = subparsers.add_parser("enable-daily", help="开启某达人的每日监控。")
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="TikTok 主页 URL、@username 或裸名。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_enable_daily)

    p = subparsers.add_parser("disable-daily", help="关闭某达人的每日监控。")
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="TikTok 主页 URL、@username 或裸名。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_disable_daily)

    p = subparsers.add_parser("remove", help="从监控列表中移除某达人。")
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="TikTok 主页 URL、@username 或裸名。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_remove)

    p = subparsers.add_parser("snapshot", help="拉取并落盘某达人当日快照（不输出报告）。")
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="TikTok 主页 URL、@username 或裸名。")
    add_count_argument(p)
    p.add_argument("--date", default="", help="快照日期，默认今天 (YYYY-MM-DD)。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_snapshot)

    p = subparsers.add_parser("digest", help="生成某群的每日日报（昨日 vs 今日）。")
    p.add_argument("--group-id", required=True)
    p.add_argument("--date", default="", help="日报日期，默认今天 (YYYY-MM-DD)。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_digest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
