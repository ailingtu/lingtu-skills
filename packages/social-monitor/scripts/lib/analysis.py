"""单账号分析：发布频率、爆款、内容方向、focus 视角。"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from .config import (
    DEFAULT_PLATFORM,
    HOOK_PATTERNS,
    THEME_RULES,
    WEEKDAY_NAMES,
)
from .normalize import coerce_normalized
from .utils import now_utc, parse_time


def rate(video: dict[str, Any], key: str) -> float:
    views = int(video.get("views", 0) or 0)
    if views <= 0:
        return 0.0
    return int(video.get(key, 0) or 0) / views


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


def analyze_video_response(payload: dict[str, Any], platform: str = DEFAULT_PLATFORM) -> dict[str, Any]:
    normalized = coerce_normalized(payload, platform=platform)
    return _analyze_normalized(normalized)


def _analyze_normalized(normalized: dict[str, Any]) -> dict[str, Any]:
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
            rated = [v for v in bucket_videos if int(v.get("views") or 0) > 0]
            if rated:
                engagement_total = sum(
                    rate(v, "likes") + rate(v, "comments") + rate(v, "shares") + rate(v, "saves")
                    for v in rated
                )
                row["avg_engagement"] = engagement_total / len(rated)
            else:
                row["avg_engagement"] = 0.0
        rows.append(row)
    return rows


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

    weekly_trend: list[dict[str, Any]] = []
    if publish_pairs:
        latest = max(pt for pt, _ in publish_pairs)
        # 包含 latest 当天的 7 天窗口的右开端点。
        right = latest.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        for i in range(4):
            window_end = right - timedelta(days=i * 7)
            window_start = window_end - timedelta(days=7)
            label = (
                f"第 {4 - i} 周（{window_start.strftime('%m-%d')} ~ "
                f"{(window_end - timedelta(days=1)).strftime('%m-%d')}）"
            )
            count = sum(1 for pt, _ in publish_pairs if window_start <= pt < window_end)
            weekly_trend.append({"week": label, "count": count})

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

    rated_videos = [v for v in videos if int(v.get("views") or 0) > 0]
    if rated_videos:
        n = len(rated_videos)
        avg = {
            "like_rate": sum(rate(v, "likes") for v in rated_videos) / n,
            "comment_rate": sum(rate(v, "comments") for v in rated_videos) / n,
            "share_rate": sum(rate(v, "shares") for v in rated_videos) / n,
            "save_rate": sum(rate(v, "saves") for v in rated_videos) / n,
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


def analyze_with_focus(payload: dict[str, Any], focus: str, platform: str = DEFAULT_PLATFORM) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = coerce_normalized(payload, platform=platform)
    base = _analyze_normalized(normalized)
    if focus == "posting":
        base["posting"] = compute_posting(normalized)
    elif focus == "content":
        base["content"] = compute_content(normalized, base)
    base["focus"] = focus
    return normalized, base
