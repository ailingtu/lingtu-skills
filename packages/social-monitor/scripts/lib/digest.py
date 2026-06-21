"""每日日报：昨日 vs 今日聚合 + 文本格式。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .config import DEFAULT_PLATFORM, STALL_DAYS, SURGE_WEEK_THRESHOLD
from .store import list_monitors, load_snapshot
from .utils import (
    format_delta,
    format_number,
    normalize_platform,
    now_utc,
    parse_time,
    platform_label,
)


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


def build_digest(group_id: str, day: str, platform: str | None = None) -> dict[str, Any]:
    monitors = list_monitors(group_id=group_id, daily_only=True, platform=platform)
    yday = previous_day(day)
    creator_diffs: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for monitor in monitors:
        creator = monitor.get("creator") or {}
        creator_platform = normalize_platform(creator.get("platform") or DEFAULT_PLATFORM)
        creator_id = creator.get("creator_id") or creator.get("username") or ""
        today_snap = load_snapshot(group_id, creator_platform, creator_id, day)
        if not today_snap:
            missing.append({
                "username": creator.get("username"),
                "nickname": creator.get("nickname"),
                "remark": monitor.get("remark"),
            })
            continue
        yesterday_snap = load_snapshot(group_id, creator_platform, creator_id, yday)
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
        "platform": platform,
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

    platform = digest.get("platform")
    title = f"{platform_label(platform)} 监控日报" if platform else "社媒监控日报"
    lines.append(f"【{title}】{today}（对照 {yday}）")
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
