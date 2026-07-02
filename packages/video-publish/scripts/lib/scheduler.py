"""时间自动分配：为空时间的行填充默认时间段。"""

from __future__ import annotations

from typing import Any

from .config import DEFAULT_SCHEDULE_TIMES


def compute_schedule_times(count: int) -> list[str]:
    """根据每达人每日发布条数生成时间列表（HH:MM 格式）。

    count ≤ 3: 使用默认早中晚 (09:00, 14:00, 19:00)
    count > 3:  从 09:00 开始每 2 小时递增
    """
    if count <= 3:
        slots = list(DEFAULT_SCHEDULE_TIMES[:count])
    else:
        slots = []
        for i in range(count):
            hour = 9 + i * 2
            if hour >= 24:
                hour = hour % 24
            slots.append(hour)
    return [f"{h:02d}:00" for h in slots]


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

    times = compute_schedule_times(count_per_creator)

    creator_index: dict[str, int] = {}
    for row in rows:
        scheduled_at = (row.get("scheduled_at") or "").strip()
        if not scheduled_at:
            creator = row.get("creator_username", "")
            idx = creator_index.get(creator, 0)
            if idx >= len(times):
                hour = 9 + idx * 2
                time_str = f"{hour:02d}:00"
            else:
                time_str = times[idx]
            row["scheduled_at"] = f"{date} {time_str}"
            creator_index[creator] = idx + 1

    return rows
