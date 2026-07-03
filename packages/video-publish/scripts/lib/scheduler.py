"""时间自动分配：为空时间的行填充默认时间段。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .config import DEFAULT_SCHEDULE_TIMES


def compute_schedule_times(count: int, offset_minutes: int = 0) -> list[str]:
    """根据每达人每日发布条数生成时间列表（HH:MM 格式）。

    count ≤ 3: 使用默认早中晚 (09:00, 14:00, 19:00)
    count > 3:  从 09:00 开始每 2 小时递增

    offset_minutes 用于同一批次内按达人错峰，避免所有达人发布时间完全相同。
    """
    if count <= 3:
        hours = list(DEFAULT_SCHEDULE_TIMES[:count])
    else:
        hours = []
        for i in range(count):
            hour = 9 + i * 2
            if hour >= 24:
                hour = hour % 24
            hours.append(hour)

    base = datetime(2000, 1, 1)
    return [
        (base.replace(hour=h, minute=0) + timedelta(minutes=offset_minutes)).strftime("%H:%M")
        for h in hours
    ]


def creator_offset_minutes(index: int) -> int:
    """按达人序号生成稳定错峰分钟数。

    11 分钟步长在 2 小时窗口内可容纳大量达人，且不会把早中晚三个主时间段挤成同一分钟。
    """
    return (max(0, index) * 11) % 120


def build_schedule_rows(
    *,
    dates: list[str],
    creators: list[str],
    platform: str,
    product_id: str,
    timezone_by_creator: dict[str, str],
    count: int,
    count_by_date: dict[str, int] | None = None,
) -> list[dict[str, str]]:
    """构建带默认错峰时间的发布行。"""
    rows: list[dict[str, str]] = []
    for date in dates:
        day_count = max(1, count_by_date.get(date, count)) if count_by_date else count
        for creator_idx, creator in enumerate(creators):
            offset = creator_offset_minutes(creator_idx)
            times = compute_schedule_times(day_count, offset_minutes=offset)
            for scheduled_time in times:
                rows.append({
                    "creator_username": creator,
                    "platform": platform,
                    "product_id": product_id,
                    "product_title": "",
                    "product_source": "SHOP" if platform == "tiktok_shop" else "",
                    "title": "",
                    "timezone": timezone_by_creator.get(creator.lower(), ""),
                    "scheduled_at": f"{date} {scheduled_time}",
                    "video_file": "",
                })
    return rows


def auto_assign_schedule(
    rows: list[dict[str, Any]],
    date: str,
    count_per_creator: int | None = None,
) -> list[dict[str, Any]]:
    """为 scheduled_at 为空的行自动填充发布时间。

    按 creator 分组，每组内按 count_per_creator 分配时间段。
    如果某 creator 出现超过 count_per_creator 次，从 09:00 每 2h 递增。
    """
    if not rows:
        return rows

    if count_per_creator is None:
        # 默认取每个 creator 的行数上限作为 count
        from collections import Counter
        cnt = Counter(r.get("creator_username", "") for r in rows)
        max_count = max(cnt.values()) if cnt else 3
        count_per_creator = min(max_count, 3) if max_count <= 3 else max_count

    creator_index: dict[str, int] = {}
    creator_order: dict[str, int] = {}
    for row in rows:
        scheduled_at = (row.get("scheduled_at") or "").strip()
        if not scheduled_at:
            creator = row.get("creator_username", "")
            if creator not in creator_order:
                creator_order[creator] = len(creator_order)
            idx = creator_index.get(creator, 0)
            times = compute_schedule_times(
                count_per_creator,
                offset_minutes=creator_offset_minutes(creator_order[creator]),
            )
            if idx >= len(times):
                base = datetime.strptime(date, "%Y-%m-%d").replace(hour=9, minute=0)
                shifted = base + timedelta(hours=idx * 2, minutes=creator_offset_minutes(creator_order[creator]))
                time_str = shifted.strftime("%H:%M")
            else:
                time_str = times[idx]
            row["scheduled_at"] = f"{date} {time_str}"
            creator_index[creator] = idx + 1

    return rows
