"""监控元数据 (`monitors.json`) 与每日快照的读写。"""

from __future__ import annotations

import argparse
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


def upsert_monitor(creator: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    path = store_path()
    data = load_store(path)
    monitors = data["monitors"]
    username = creator.get("username") or ""
    platform = normalize_platform(creator.get("platform") or getattr(args, "platform", DEFAULT_PLATFORM))
    creator_id = creator.get("creator_id") or stable_id("creator", username)
    timestamp = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")

    existing = find_monitor(monitors, args.group_id, username, platform=platform)
    if existing:
        existing["remark"] = args.remark or existing.get("remark", "")
        existing["updated_at"] = timestamp
        existing["creator"] = creator
        if "daily_enabled" not in existing:
            existing["daily_enabled"] = False
        monitor = existing
    else:
        monitor = {
            "monitor_id": stable_id("monitor", f"{args.group_id}:{platform}:{creator_id or username}"),
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
