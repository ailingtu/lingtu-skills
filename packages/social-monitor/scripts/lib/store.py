"""监控元数据 (`monitors.json`) 与每日快照的读写。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_PLATFORM
from .utils import (
    normalize_platform,
    now_utc,
    slugify_handle,
    snapshots_dir,
    stable_id,
    store_path,
)


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


def find_monitor(monitors: list[dict[str, Any]], group_id: str, username: str, platform: str = DEFAULT_PLATFORM) -> dict[str, Any] | None:
    platform = normalize_platform(platform)
    return next(
        (
            item
            for item in monitors
            if item.get("group_id") == group_id
            and item.get("creator", {}).get("platform") == platform
            and item.get("creator", {}).get("username") == username
        ),
        None,
    )


def upsert_monitor(
    creator: dict[str, Any],
    *,
    group_id: str,
    source: str = "feishu_group",
    team_id: str = "",
    operator_id: str = "default_user",
    remark: str = "",
    tags: list[str] | None = None,
    platform: str | None = None,
) -> dict[str, Any]:
    path = store_path()
    data = load_store(path)
    monitors = data["monitors"]
    username = creator.get("username") or ""
    platform = normalize_platform(platform or creator.get("platform") or DEFAULT_PLATFORM)
    creator_id = creator.get("creator_id") or stable_id("creator", username)
    timestamp = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")

    existing = find_monitor(monitors, group_id, username, platform=platform)
    if existing:
        if remark:
            existing["remark"] = remark
        elif "remark" not in existing:
            existing["remark"] = ""
        if tags is not None:
            existing["tags"] = tags
        elif "tags" not in existing:
            existing["tags"] = []
        existing["updated_at"] = timestamp
        existing["creator"] = creator
        if "daily_enabled" not in existing:
            existing["daily_enabled"] = False
        if "alert_config" not in existing:
            existing["alert_config"] = {}
        monitor = existing
    else:
        monitor = {
            "monitor_id": stable_id("monitor", f"{group_id}:{platform}:{creator_id or username}"),
            "source": source,
            "group_id": group_id,
            "team_id": team_id,
            "operator_id": operator_id,
            "remark": remark,
            "tags": tags or [],
            "added_at": timestamp,
            "updated_at": timestamp,
            "daily_enabled": False,
            "alert_config": {},
            "creator": creator,
        }
        monitors.append(monitor)
    save_store(path, data)
    return monitor


def update_monitor(group_id: str, username: str, platform: str = DEFAULT_PLATFORM, **changes: Any) -> dict[str, Any]:
    platform = normalize_platform(platform)
    path = store_path()
    data = load_store(path)
    monitor = find_monitor(data["monitors"], group_id, username, platform=platform)
    if not monitor:
        raise SystemExit(f"未找到监控记录（platform={platform}, group_id={group_id}, username={username}）。")
    monitor.update(changes)
    monitor["updated_at"] = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    save_store(path, data)
    return monitor


def patch_alert_config(
    group_id: str,
    username: str,
    platform: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    platform = normalize_platform(platform)
    path = store_path()
    data = load_store(path)
    monitor = find_monitor(data["monitors"], group_id, username, platform=platform)
    if not monitor:
        raise SystemExit(f"未找到监控记录（platform={platform}, group_id={group_id}, username={username}）。")
    cfg = dict(monitor.get("alert_config") or {})
    for key, value in updates.items():
        if value is None:
            cfg.pop(key, None)
        else:
            cfg[key] = value
    monitor["alert_config"] = cfg
    monitor["updated_at"] = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    save_store(path, data)
    return monitor


def remove_monitor(group_id: str, username: str, platform: str = DEFAULT_PLATFORM) -> dict[str, Any]:
    platform = normalize_platform(platform)
    path = store_path()
    data = load_store(path)
    monitor = find_monitor(data["monitors"], group_id, username, platform=platform)
    if not monitor:
        raise SystemExit(f"未找到监控记录（platform={platform}, group_id={group_id}, username={username}）。")
    data["monitors"] = [m for m in data["monitors"] if m is not monitor]
    save_store(path, data)
    return monitor


def list_monitors(group_id: str | None = None, daily_only: bool = False, platform: str | None = None) -> list[dict[str, Any]]:
    data = load_store(store_path())
    items = data["monitors"]
    if platform is not None:
        normalized_platform = normalize_platform(platform)
        items = [m for m in items if (m.get("creator") or {}).get("platform") == normalized_platform]
    if group_id is not None:
        items = [m for m in items if m.get("group_id") == group_id]
    if daily_only:
        items = [m for m in items if m.get("daily_enabled")]
    return items


def snapshot_path(group_id: str, platform: str, creator_id: str, day: str) -> Path:
    safe_group = slugify_handle(group_id) or "default"
    safe_platform = slugify_handle(normalize_platform(platform)) or DEFAULT_PLATFORM
    safe_creator = slugify_handle(creator_id) or "unknown"
    return snapshots_dir() / safe_group / safe_platform / safe_creator / f"{day}.json"


def save_snapshot(group_id: str, normalized: dict[str, Any], day: str) -> Path:
    creator = normalized.get("creator") or {}
    platform = normalize_platform(creator.get("platform") or DEFAULT_PLATFORM)
    creator_id = creator.get("creator_id") or creator.get("username") or "unknown"
    path = snapshot_path(group_id, platform, creator_id, day)
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


def load_snapshot(group_id: str, platform: str, creator_id: str, day: str) -> dict[str, Any] | None:
    path = snapshot_path(group_id, platform, creator_id, day)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def list_snapshot_dates(group_id: str, platform: str, creator_id: str) -> list[str]:
    safe_group = slugify_handle(group_id) or "default"
    safe_platform = slugify_handle(normalize_platform(platform)) or DEFAULT_PLATFORM
    safe_creator = slugify_handle(creator_id) or "unknown"
    folder = snapshots_dir() / safe_group / safe_platform / safe_creator
    if not folder.exists():
        return []
    dates: list[str] = []
    for child in folder.iterdir():
        if child.is_file() and child.suffix == ".json":
            stem = child.stem
            if len(stem) == 10 and stem[4] == "-" and stem[7] == "-":
                dates.append(stem)
    dates.sort()
    return dates


def list_snapshot_creators(group_id: str, platform: str | None = None) -> list[dict[str, str]]:
    """枚举某 group 下所有有快照的（platform, creator_id）。"""
    safe_group = slugify_handle(group_id) or "default"
    root = snapshots_dir() / safe_group
    if not root.exists():
        return []
    items: list[dict[str, str]] = []
    target_platform = normalize_platform(platform) if platform else None
    for platform_dir in root.iterdir():
        if not platform_dir.is_dir():
            continue
        plat = platform_dir.name
        if target_platform and plat != target_platform:
            continue
        for creator_dir in platform_dir.iterdir():
            if creator_dir.is_dir():
                items.append({"platform": plat, "creator_id": creator_dir.name})
    items.sort(key=lambda x: (x["platform"], x["creator_id"]))
    return items
