"""argparse 解析与子命令实现。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

from lingtu_auth import add_identity_arguments, configure_identity

from .analysis import analyze_with_focus
from .api import fetch_material, fetch_material_comments, fetch_posts
from .config import DEFAULT_PLATFORM, FOCUS_CHOICES, SUPPORTED_PLATFORMS
from .digest import build_digest, check_alerts
from .normalize import (
    normalize_comments_response,
    normalize_material_response,
    normalize_response,
)
from .report import (
    TUTORIAL_TEXT,
    build_comments_text,
    build_material_text,
    build_report_text,
)
from .store import (
    find_monitor,
    list_monitors,
    list_snapshot_creators,
    list_snapshot_dates,
    load_snapshot,
    load_store,
    patch_alert_config,
    remove_monitor,
    save_snapshot,
    update_monitor,
    upsert_monitor,
)
from .utils import (
    normalize_platform,
    parse_creator_handle,
    platform_label,
    require_api_key,
    store_path,
    today_str,
)


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _is_non_retryable_fetch_posts_error(message: str) -> bool:
    return (
        "未获取到该达人数据" in message
        or "缺少环境变量 LINGTU_API_KEY" in message
        or "不支持的平台" in message
    )


def fetch_posts_with_retries(
    unique_id: str,
    count: int,
    *,
    platform: str,
    request_timeout: int,
    retries: int,
    retry_sleep_ms: int,
) -> tuple[dict[str, Any], int]:
    max_attempts = max(1, retries + 1)
    retry_sleep_seconds = max(0, retry_sleep_ms) / 1000.0
    last_error = "未知错误"
    for attempt in range(1, max_attempts + 1):
        try:
            return fetch_posts(unique_id, count, platform=platform, timeout=request_timeout), attempt
        except SystemExit as exc:
            last_error = str(exc) or "未知错误"
            if _is_non_retryable_fetch_posts_error(last_error):
                break
            if attempt < max_attempts and retry_sleep_seconds > 0:
                time.sleep(retry_sleep_seconds)
    raise SystemExit(last_error)


def command_tutorial(args: argparse.Namespace) -> None:
    if args.format == "text":
        print(TUTORIAL_TEXT)
    else:
        print_json({"reply_text": TUTORIAL_TEXT})


def add_one(
    *,
    raw_input: str,
    platform: str,
    group_id: str,
    source: str = "feishu_group",
    team_id: str = "",
    operator_id: str = "default_user",
    remark: str = "",
    tags: list[str] | None = None,
    count: int = 40,
    date: str = "",
    focus: str | None = None,
    enable_daily: bool = False,
    request_timeout: int = 30,
) -> dict[str, Any]:
    """添加单个达人到监控（抓取 + upsert + 快照 + 可选分析 + 可选每日订阅）。

    抛 SystemExit 表示失败，由调用方捕获。
    """
    platform = normalize_platform(platform)
    unique_id = parse_creator_handle(raw_input, platform=platform)
    raw = fetch_posts(unique_id, count, platform=platform, timeout=request_timeout)
    normalized = normalize_response(raw, platform=platform)
    monitor = upsert_monitor(
        normalized["creator"],
        group_id=group_id,
        source=source,
        team_id=team_id,
        operator_id=operator_id,
        remark=remark,
        tags=tags,
        platform=platform,
    )
    snapshot_file = save_snapshot(group_id, normalized, today_str(date))
    if enable_daily and not monitor.get("daily_enabled"):
        monitor = update_monitor(group_id, unique_id, platform=platform, daily_enabled=True)

    analysis = None
    if focus:
        _, analysis = analyze_with_focus(normalized, focus, platform=platform)

    return {
        "monitor": monitor,
        "normalized": normalized,
        "raw": raw,
        "snapshot_path": snapshot_file,
        "analysis": analysis,
        "unique_id": unique_id,
    }


def command_add(args: argparse.Namespace) -> None:
    result = add_one(
        raw_input=args.input,
        platform=args.platform,
        group_id=args.group_id,
        source=args.source,
        team_id=args.team_id,
        operator_id=args.operator_id,
        remark=args.remark,
        tags=_split_tags(args.tags),
        count=args.count,
        date=args.date,
        focus=args.focus,
        enable_daily=args.enable_daily,
        request_timeout=max(1, args.request_timeout),
    )
    monitor = result["monitor"]
    normalized = result["normalized"]
    analysis = result["analysis"]
    reply_text = build_report_text(args.focus, normalized["creator"], args.remark, analysis)
    if args.enable_daily:
        reply_text = reply_text.rstrip() + "\n（已加入每日监控）"

    if args.format == "text":
        print(reply_text)
        return

    output: dict[str, Any] = {
        "monitor": {
            "monitor_id": monitor["monitor_id"],
            "group_id": monitor["group_id"],
            "creator": normalized["creator"],
            "remark": monitor.get("remark", ""),
            "tags": monitor.get("tags", []),
            "daily_enabled": monitor.get("daily_enabled", False),
            "store_path": str(store_path()),
            "snapshot_path": str(result["snapshot_path"]),
        },
        "analysis": analysis,
        "reply_text": reply_text,
    }
    if args.include_videos:
        output["videos"] = normalized["videos"]
    if args.include_raw:
        output["raw"] = result["raw"]
    print_json(output)


def _split_tags(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parts = [t.strip() for t in value.split(",")]
    return [t for t in parts if t]


def _merge_tags(existing: list[Any], incoming: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*existing, *incoming]:
        tag = str(value).strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        merged.append(tag)
    return merged


def _read_inputs_file(path: str) -> list[str]:
    p = Path(path).expanduser()
    if not p.exists():
        raise SystemExit(f"--inputs-file 文件不存在：{p}")
    items: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items


def _read_tag_rows(path: str) -> list[dict[str, str]]:
    p = Path(path).expanduser()
    if not p.exists():
        raise SystemExit(f"--input-file 文件不存在：{p}")
    with p.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise SystemExit("--input-file 不能为空，且必须包含表头 input,tags。")
        fieldnames = {name.strip() for name in reader.fieldnames if name}
        if "input" not in fieldnames or "tags" not in fieldnames:
            raise SystemExit("--input-file 必须包含表头 input,tags。")
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized_row = {
                key.strip() if isinstance(key, str) else key: value
                for key, value in row.items()
            }
            raw_input = (normalized_row.get("input") or "").strip()
            if not raw_input or raw_input.startswith("#"):
                continue
            tag_parts = [normalized_row.get("tags") or ""]
            extra_tags = normalized_row.get(None) or []
            if isinstance(extra_tags, list):
                tag_parts.extend(extra_tags)
            rows.append({"input": raw_input, "tags": ",".join(tag_parts)})
    return rows


def _batch_success_milestones(total: int) -> set[int]:
    milestones: set[int] = set()
    value = 1
    while value <= total:
        milestones.add(value)
        value *= 2
    if total:
        milestones.add(total)
    return milestones


def _print_batch_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def command_batch_add(args: argparse.Namespace) -> None:
    if bool(args.inputs) == bool(args.inputs_file):
        raise SystemExit("--inputs 和 --inputs-file 必须二选一。")
    if args.inputs:
        items = [t.strip() for t in args.inputs.split(",") if t.strip()]
    else:
        items = _read_inputs_file(args.inputs_file)
    if not items:
        raise SystemExit("未提供任何达人输入。")

    sleep_seconds = max(0, args.sleep_ms) / 1000.0
    tags = _split_tags(args.tags)

    success: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    max_attempts = max(1, args.retries + 1)
    retry_sleep_seconds = max(0, args.retry_sleep_ms) / 1000.0
    request_timeout = max(1, args.request_timeout)
    progress_enabled = not args.no_progress
    progress_every = max(1, args.progress_every)
    success_milestones = _batch_success_milestones(len(items))
    announced_success_counts: set[int] = set()
    if progress_enabled:
        _print_batch_progress(f"批量添加开始：共 {len(items)} 个达人。")

    for idx, item in enumerate(items):
        if idx > 0 and sleep_seconds > 0:
            time.sleep(sleep_seconds)
        last_error = "未知错误"
        succeeded = False
        for attempt in range(1, max_attempts + 1):
            try:
                result = add_one(
                    raw_input=item,
                    platform=args.platform,
                    group_id=args.group_id,
                    source=args.source,
                    team_id=args.team_id,
                    operator_id=args.operator_id,
                    remark=args.remark,
                    tags=tags,
                    count=args.count,
                    date=args.date,
                    focus=None,
                    enable_daily=args.enable_daily,
                    request_timeout=request_timeout,
                )
                creator = result["normalized"]["creator"]
                success.append({
                    "input": item,
                    "username": creator.get("username"),
                    "nickname": creator.get("nickname"),
                    "monitor_id": result["monitor"]["monitor_id"],
                    "snapshot_path": str(result["snapshot_path"]),
                    "daily_enabled": result["monitor"].get("daily_enabled", False),
                    "attempts": attempt,
                })
                succeeded = True
                break
            except SystemExit as exc:
                last_error = str(exc) or "未知错误"
                if _is_non_retryable_fetch_posts_error(last_error):
                    break
                if attempt < max_attempts and retry_sleep_seconds > 0:
                    time.sleep(retry_sleep_seconds)
        if not succeeded:
            failed.append({"input": item, "reason": last_error, "attempts": attempt})
        processed = idx + 1
        succeeded_count = len(success)
        if progress_enabled and succeeded_count in success_milestones and succeeded_count not in announced_success_counts:
            announced_success_counts.add(succeeded_count)
            _print_batch_progress(f"批量添加进度：已成功 {succeeded_count} 个，已处理 {processed}/{len(items)}，失败 {len(failed)}。")
        elif progress_enabled and (processed % progress_every == 0 or processed == len(items)):
            _print_batch_progress(f"批量添加进度：已处理 {processed}/{len(items)}，成功 {succeeded_count}，失败 {len(failed)}。")

    summary = {
        "total": len(items),
        "succeeded": len(success),
        "failed_count": len(failed),
        "success": success,
        "failed": failed,
    }
    if progress_enabled:
        _print_batch_progress(f"批量添加结束：共 {summary['total']} 条，成功 {summary['succeeded']}，失败 {summary['failed_count']}。")

    if args.format == "json":
        print_json(summary)
        return

    print(f"批量添加完成：共 {summary['total']} 条，成功 {summary['succeeded']}，失败 {summary['failed_count']}。")
    if success:
        print("成功：")
        for item in success:
            flag = " ✓每日" if item.get("daily_enabled") else ""
            print(f"  - @{item['username']} {item.get('nickname','') or ''}{flag}")
    if failed:
        print("失败：")
        for item in failed:
            print(f"  - {item['input']}：{item['reason']}")


def command_videos(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    raw = fetch_posts(unique_id, args.count, platform=platform)
    if args.raw:
        print_json(raw)
    else:
        print_json(normalize_response(raw, platform=platform))


def command_material(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    raw = fetch_material(args.video_url, platform=platform)
    if args.raw:
        print_json(raw)
        return

    normalized = normalize_material_response(raw, platform=platform)
    if args.format == "text":
        print(build_material_text(normalized["video"]))
    else:
        print_json(normalized)


def command_comments(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    max_pages = args.max_pages
    if max_pages is not None and max_pages < 1:
        raise SystemExit("--max-pages 必须大于等于 1")
    cursor: Any = args.cursor
    if isinstance(cursor, str) and cursor and cursor.lstrip().startswith(("{", "[")):
        try:
            cursor = json.loads(cursor)
        except json.JSONDecodeError:
            raise SystemExit("--cursor 看起来是 JSON 但解析失败，请检查转义。")
    raw = fetch_material_comments(
        args.video_url,
        platform=platform,
        sort_order=args.sort_order,
        cursor=cursor,
        max_pages=max_pages,
        fetch_all=not args.first_page,
    )
    if args.raw:
        print_json(raw)
        return

    normalized = normalize_comments_response(raw, platform=platform)
    if args.format == "text":
        print(build_comments_text(normalized, platform=platform))
    else:
        print_json(normalized)


def command_analyze(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    require_api_key()
    with open(args.input_json, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    normalized, analysis = analyze_with_focus(payload, args.focus, platform=platform)
    if args.format == "text":
        print(build_report_text(args.focus, normalized.get("creator") or {}, args.remark, analysis))
    else:
        print_json(analysis)


def command_list(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform) if args.platform else None
    monitors = list_monitors(group_id=args.group_id, daily_only=args.daily_only, platform=platform)
    if args.format == "json":
        print_json({
            "group_id": args.group_id,
            "platform": platform,
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
        label = platform_label(creator.get("platform") or DEFAULT_PLATFORM)
        print(
            f"  [{flag}] {label} @{creator.get('username','')} {creator.get('nickname','')}"
            f"  备注：{m.get('remark','')}"
        )
    print("说明：✓ = 已加入每日监控，· = 仅手动查询。")


def command_enable_daily(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    monitor = update_monitor(args.group_id, unique_id, platform=platform, daily_enabled=True)
    creator = monitor.get("creator") or {}
    if args.format == "text":
        print(f"已加入每日监控：@{creator.get('username','')} {creator.get('nickname','')}。"
              f"明日早 8 点会出现在本群日报中。")
    else:
        print_json({"monitor_id": monitor["monitor_id"], "daily_enabled": True})


def command_disable_daily(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    monitor = update_monitor(args.group_id, unique_id, platform=platform, daily_enabled=False)
    creator = monitor.get("creator") or {}
    if args.format == "text":
        print(f"已退出每日监控：@{creator.get('username','')} {creator.get('nickname','')}。"
              f"该达人仍保留在监控列表中，可手动查询。")
    else:
        print_json({"monitor_id": monitor["monitor_id"], "daily_enabled": False})


def command_remove(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    monitor = remove_monitor(args.group_id, unique_id, platform=platform)
    creator = monitor.get("creator") or {}
    if args.format == "text":
        print(f"已移除监控：@{creator.get('username','')} {creator.get('nickname','')}。")
    else:
        print_json({"removed_monitor_id": monitor["monitor_id"]})


def command_snapshot(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    raw, attempts = fetch_posts_with_retries(
        unique_id,
        args.count,
        platform=platform,
        request_timeout=max(1, args.request_timeout),
        retries=max(0, args.retries),
        retry_sleep_ms=args.retry_sleep_ms,
    )
    normalized = normalize_response(raw, platform=platform)
    monitor = find_monitor(load_store(store_path())["monitors"], args.group_id, unique_id, platform=platform)
    if monitor:
        update_monitor(args.group_id, unique_id, platform=platform, creator=normalized["creator"])
    path = save_snapshot(args.group_id, normalized, today_str(args.date))
    if args.format == "text":
        suffix = f"（尝试 {attempts} 次）" if attempts > 1 else ""
        print(f"已写入快照：{path}{suffix}")
    else:
        print_json({
            "group_id": args.group_id,
            "platform": platform,
            "username": unique_id,
            "date": today_str(args.date),
            "snapshot_path": str(path),
            "video_count": len(normalized.get("videos") or []),
            "attempts": attempts,
        })


def _resolve_creator_id(group_id: str, raw_input: str, platform: str) -> tuple[str, str]:
    """解析 --input 为 (uniqueId, creator_id)。

    优先用 monitors.json 中已存的 creator_id；找不到时退化用 uniqueId 兜底
    （等同于历史 snapshot 落盘的兜底逻辑）。
    """
    unique_id = parse_creator_handle(raw_input, platform=platform)
    monitor = find_monitor(load_store(store_path())["monitors"], group_id, unique_id, platform=platform)
    if monitor:
        creator = monitor.get("creator") or {}
        return unique_id, str(creator.get("creator_id") or unique_id)
    return unique_id, unique_id


def _validate_date_str(value: str, label: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise SystemExit(f"{label} 必须是 YYYY-MM-DD 格式：{value}") from exc


def command_snapshot_get(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform) if args.platform else None

    if args.latest_only:
        creators = list_snapshot_creators(args.group_id, platform=platform)
        items = []
        for entry in creators:
            dates = list_snapshot_dates(args.group_id, entry["platform"], entry["creator_id"])
            if not dates:
                continue
            items.append({
                "platform": entry["platform"],
                "creator_id": entry["creator_id"],
                "latest_date": dates[-1],
                "snapshot_count": len(dates),
            })
        print_json({
            "group_id": args.group_id,
            "platform": platform,
            "latest_only": True,
            "creators": items,
        })
        return

    if not args.input:
        raise SystemExit("--input 是必填的（或使用 --latest-only 列出全部）。")
    if platform is None:
        platform = normalize_platform(None)

    unique_id, creator_id = _resolve_creator_id(args.group_id, args.input, platform)

    if args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise SystemExit("--from 和 --to 必须同时提供。")
        _validate_date_str(args.from_date, "--from")
        _validate_date_str(args.to_date, "--to")
        if args.from_date > args.to_date:
            raise SystemExit("--from 不能晚于 --to。")
        all_dates = list_snapshot_dates(args.group_id, platform, creator_id)
        wanted = [d for d in all_dates if args.from_date <= d <= args.to_date]
        snapshots = []
        for day in wanted:
            snap = load_snapshot(args.group_id, platform, creator_id, day)
            if snap is not None:
                snapshots.append(snap)
        print_json({
            "group_id": args.group_id,
            "platform": platform,
            "username": unique_id,
            "creator_id": creator_id,
            "from": args.from_date,
            "to": args.to_date,
            "snapshots": snapshots,
        })
        return

    day = today_str(args.date)
    _validate_date_str(day, "--date")
    snap = load_snapshot(args.group_id, platform, creator_id, day)
    if snap is None:
        raise SystemExit(
            f"未找到快照（group_id={args.group_id}, platform={platform}, "
            f"username={unique_id}, date={day}）。"
        )
    print_json(snap)


def command_digest(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform) if args.platform else None
    digest = build_digest(args.group_id, today_str(args.date), platform=platform)
    if args.format == "text":
        print(digest["reply_text"])
    else:
        print_json(digest)


def _collect_alerts(group_id: str, day: str, platform: str | None, unique_id: str | None) -> list[dict[str, Any]]:
    yday = (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    monitors = list_monitors(group_id=group_id, daily_only=True, platform=platform)
    alerts: list[dict[str, Any]] = []
    for monitor in monitors:
        creator = monitor.get("creator") or {}
        if unique_id and creator.get("username") != unique_id:
            continue
        creator_platform = normalize_platform(creator.get("platform") or "tiktok")
        creator_id = creator.get("creator_id") or creator.get("username") or ""
        today_snap = load_snapshot(group_id, creator_platform, creator_id, day)
        if not today_snap:
            continue
        yesterday_snap = load_snapshot(group_id, creator_platform, creator_id, yday)
        alerts.extend(check_alerts(today_snap, yesterday_snap))
    return alerts


def command_alerts_check(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform) if args.platform else None
    day = today_str(args.date)
    _validate_date_str(day, "--date")
    target_unique_id: str | None = None
    if args.input:
        target_platform = platform or normalize_platform(None)
        target_unique_id = parse_creator_handle(args.input, platform=target_platform)
    alerts = _collect_alerts(args.group_id, day, platform, target_unique_id)
    print_json({
        "group_id": args.group_id,
        "platform": platform,
        "date": day,
        "username": target_unique_id,
        "alerts": alerts,
    })


def command_tag(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    tags = _split_tags(args.tags) or []
    monitor = update_monitor(args.group_id, unique_id, platform=platform, tags=tags)
    if args.format == "text":
        creator = monitor.get("creator") or {}
        joined = ", ".join(tags) if tags else "（已清空）"
        print(f"已更新标签：@{creator.get('username','')} → {joined}")
    else:
        print_json({"monitor_id": monitor["monitor_id"], "tags": monitor.get("tags", [])})


def command_batch_tag(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    rows = _read_tag_rows(args.input_file)
    if not rows:
        raise SystemExit("--input-file 未提供任何标签记录。")

    success: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for row in rows:
        raw_input = row["input"]
        try:
            unique_id = parse_creator_handle(raw_input, platform=platform)
            incoming_tags = _split_tags(row["tags"]) or []
            if args.append:
                existing = find_monitor(load_store(store_path())["monitors"], args.group_id, unique_id, platform=platform)
                if not existing:
                    raise SystemExit(f"未找到监控记录（platform={platform}, group_id={args.group_id}, username={unique_id}）。")
                tags = _merge_tags(existing.get("tags") or [], incoming_tags)
            else:
                tags = incoming_tags
            monitor = update_monitor(args.group_id, unique_id, platform=platform, tags=tags)
            creator = monitor.get("creator") or {}
            success.append({
                "input": raw_input,
                "username": creator.get("username") or unique_id,
                "monitor_id": monitor["monitor_id"],
                "tags": monitor.get("tags", []),
            })
        except SystemExit as exc:
            failed.append({"input": raw_input, "reason": str(exc) or "未知错误"})

    summary = {
        "total": len(rows),
        "succeeded": len(success),
        "failed_count": len(failed),
        "mode": "append" if args.append else "replace",
        "success": success,
        "failed": failed,
    }
    if args.format == "json":
        print_json(summary)
        return

    print(f"批量标签完成：共 {summary['total']} 条，成功 {summary['succeeded']}，失败 {summary['failed_count']}。")
    if success:
        print("成功：")
        for item in success:
            joined = ", ".join(item.get("tags") or []) or "（已清空）"
            print(f"  - @{item['username']} → {joined}")
    if failed:
        print("失败：")
        for item in failed:
            print(f"  - {item['input']}：{item['reason']}")


def command_remark(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    monitor = update_monitor(args.group_id, unique_id, platform=platform, remark=args.remark)
    if args.format == "text":
        creator = monitor.get("creator") or {}
        print(f"已更新备注：@{creator.get('username','')} → {args.remark or '（已清空）'}")
    else:
        print_json({"monitor_id": monitor["monitor_id"], "remark": monitor.get("remark", "")})


def command_alert_config(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    updates: dict[str, Any] = {}
    if args.viral_threshold is not None:
        updates["viral_threshold"] = args.viral_threshold if args.viral_threshold >= 0 else None
    if args.follower_drop_threshold is not None:
        updates["follower_drop_threshold"] = args.follower_drop_threshold if args.follower_drop_threshold >= 0 else None
    if args.max_silent_days is not None:
        updates["max_silent_days"] = args.max_silent_days if args.max_silent_days >= 0 else None
    if not updates:
        raise SystemExit("至少传一个阈值参数：--viral-threshold / --follower-drop-threshold / --max-silent-days。")
    monitor = patch_alert_config(args.group_id, unique_id, platform, updates)
    if args.format == "text":
        creator = monitor.get("creator") or {}
        print(f"已更新告警配置：@{creator.get('username','')} → {monitor.get('alert_config') or {}}")
    else:
        print_json({"monitor_id": monitor["monitor_id"], "alert_config": monitor.get("alert_config") or {}})


def command_monitor_get(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    monitor = find_monitor(load_store(store_path())["monitors"], args.group_id, unique_id, platform=platform)
    if not monitor:
        raise SystemExit(f"未找到监控记录（platform={platform}, group_id={args.group_id}, username={unique_id}）。")
    print_json(monitor)


# -------------------- argparse 助手 --------------------

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


def add_platform_argument(parser: argparse.ArgumentParser, *, required: bool = False, allow_all: bool = False) -> None:
    parser.add_argument(
        "--platform",
        choices=SUPPORTED_PLATFORMS,
        default=None if allow_all else DEFAULT_PLATFORM,
        required=required,
        help=(
            "平台：tiktok 或 instagram；默认 tiktok。"
            if not allow_all else
            "平台过滤：tiktok 或 instagram；留空表示全部平台。"
        ),
    )


def add_identity_arguments_recursive(parser: argparse.ArgumentParser) -> None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                existing = {
                    option
                    for child_action in child._actions
                    for option in child_action.option_strings
                }
                if "--channel" not in existing:
                    add_identity_arguments(child)
                add_identity_arguments_recursive(child)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="灵途跨平台达人监控。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("tutorial", help="输出添加监控的中文教程文本。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_tutorial)

    p = subparsers.add_parser("add", help="添加达人到监控列表，并返回即时分析。")
    add_platform_argument(p)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    p.add_argument("--remark", default="", help="备注。")
    p.add_argument("--tags", default=None, help="逗号分隔的标签，例如 'top-tier,NBA'。")
    p.add_argument("--source", default="feishu_group", help="来源渠道。")
    p.add_argument("--group-id", required=True, help="群 ID（多群隔离主键）。")
    p.add_argument("--team-id", default="", help="团队 ID。")
    p.add_argument("--operator-id", default="default_user", help="操作人 ID。")
    add_count_argument(p)
    p.add_argument("--date", default="", help="快照日期，默认今天 (YYYY-MM-DD)。")
    add_focus_argument(p)
    p.add_argument("--enable-daily", action="store_true", help="添加成功后立即开启每日监控。")
    p.add_argument("--request-timeout", type=int, default=30, help="单次 fetchPosts 请求超时秒数，默认 30。")
    p.add_argument("--include-videos", action="store_true", help="JSON 输出附带 normalize 后的视频列表。")
    p.add_argument("--include-raw", action="store_true", help="JSON 输出附带原始 fetchPosts 响应。")
    add_format_argument(p, default="json")
    p.set_defaults(func=command_add)

    p = subparsers.add_parser("batch-add", help="批量添加达人到监控列表（不做即时分析）。")
    add_platform_argument(p)
    p.add_argument("--inputs", default="", help="逗号分隔的主页 URL/@username/裸名。与 --inputs-file 二选一。")
    p.add_argument("--inputs-file", default="", help="每行一个达人的文件；# 开头视为注释。")
    p.add_argument("--group-id", required=True, help="群 ID。")
    p.add_argument("--remark", default="", help="所有新增达人的统一备注。")
    p.add_argument("--tags", default=None, help="逗号分隔的标签，作用于本批所有达人。")
    p.add_argument("--source", default="feishu_group", help="来源渠道。")
    p.add_argument("--team-id", default="", help="团队 ID。")
    p.add_argument("--operator-id", default="default_user", help="操作人 ID。")
    add_count_argument(p)
    p.add_argument("--date", default="", help="快照日期，默认今天 (YYYY-MM-DD)。")
    p.add_argument("--enable-daily", action="store_true", help="对每个新增达人开启每日监控。")
    p.add_argument("--sleep-ms", type=int, default=600, help="相邻达人请求间隔（毫秒），默认 600。")
    p.add_argument("--request-timeout", type=int, default=30, help="单次 fetchPosts 请求超时秒数，默认 30。")
    p.add_argument("--retries", type=int, default=2, help="单个达人失败后的重试次数，默认 2。")
    p.add_argument("--retry-sleep-ms", type=int, default=1500, help="同一达人重试间隔（毫秒），默认 1500。")
    p.add_argument("--progress-every", type=int, default=10, help="每处理多少个达人输出一次进度到 stderr，默认 10。")
    p.add_argument("--no-progress", action="store_true", help="关闭批量添加过程中的 stderr 进度提示。")
    add_format_argument(p, default="json")
    p.set_defaults(func=command_batch_add)

    p = subparsers.add_parser("videos", help="拉取达人最近视频。")
    add_platform_argument(p)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    add_count_argument(p)
    p.add_argument("--raw", action="store_true", help="输出原始 fetchPosts 响应而非 normalize 结果。")
    p.set_defaults(func=command_videos)

    p = subparsers.add_parser("material", help="获取单条视频素材数据。")
    add_platform_argument(p)
    p.add_argument("--video-url", required=True, help="视频 URL。")
    p.add_argument("--raw", action="store_true", help="输出原始 fetch 响应而非 normalize 结果。")
    add_format_argument(p, default="json")
    p.set_defaults(func=command_material)

    p = subparsers.add_parser("comments", help="获取单条视频素材评论数据。")
    add_platform_argument(p)
    p.add_argument("--video-url", required=True, help="视频 URL。")
    p.add_argument("--cursor", default=None, help="评论分页游标；首次请求不传，后续请求传接口返回的 cursor。Instagram 返回的是 JSON 对象，可直接以 JSON 字符串形式传入。")
    p.add_argument("--sort-order", choices=("popular", "newest"), default="popular", help="Instagram 评论排序：popular=热门（默认），newest=最新。TikTok 会忽略该参数。")
    p.add_argument("--first-page", action="store_true", help="只请求一页评论，不自动翻页。")
    p.add_argument("--max-pages", type=int, default=None, help="最多请求多少页；默认不限制，直到接口没有下一页。")
    p.add_argument("--raw", action="store_true", help="输出原始 fetchComments 响应而非 normalize 结果。")
    add_format_argument(p, default="json")
    p.set_defaults(func=command_comments)

    p = subparsers.add_parser("analyze", help="分析一份 fetchPosts JSON（原始或 normalize）。")
    add_platform_argument(p)
    p.add_argument("--input-json", required=True, help="JSON 文件路径。")
    p.add_argument("--remark", default="", help="文本输出时附加的备注。")
    add_focus_argument(p)
    add_format_argument(p, default="json")
    p.set_defaults(func=command_analyze)

    p = subparsers.add_parser("list", help="列出某群的监控记录。")
    add_platform_argument(p, allow_all=True)
    p.add_argument("--group-id", default=None, help="群 ID，留空则列出全部。")
    p.add_argument("--daily-only", action="store_true", help="只显示已开启每日监控的达人。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_list)

    p = subparsers.add_parser("enable-daily", help="开启某达人的每日监控。")
    add_platform_argument(p)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_enable_daily)

    p = subparsers.add_parser("disable-daily", help="关闭某达人的每日监控。")
    add_platform_argument(p)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_disable_daily)

    p = subparsers.add_parser("remove", help="从监控列表中移除某达人。")
    add_platform_argument(p)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_remove)

    p = subparsers.add_parser("snapshot", help="拉取并落盘某达人当日快照（不输出报告）。")
    add_platform_argument(p)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    add_count_argument(p)
    p.add_argument("--date", default="", help="快照日期，默认今天 (YYYY-MM-DD)。")
    p.add_argument("--request-timeout", type=int, default=30, help="单次 fetchPosts 请求超时秒数，默认 30。")
    p.add_argument("--retries", type=int, default=2, help="fetchPosts 失败后的重试次数，默认 2。")
    p.add_argument("--retry-sleep-ms", type=int, default=1500, help="fetchPosts 重试间隔（毫秒），默认 1500。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_snapshot)

    p = subparsers.add_parser("alerts", help="按需检查告警事件（基于本地快照）。")
    alerts_sub = p.add_subparsers(dest="alerts_command", required=True)
    pa = alerts_sub.add_parser("check", help="对比昨日/今日快照，返回告警列表。")
    add_platform_argument(pa, allow_all=True)
    pa.add_argument("--group-id", required=True)
    pa.add_argument("--input", default="", help="主页 URL/@username/裸名；留空则扫整 group 的 daily 监控达人。")
    pa.add_argument("--date", default="", help="检查日期，默认今天 (YYYY-MM-DD)。")
    pa.set_defaults(func=command_alerts_check)

    p = subparsers.add_parser("tag", help="为某达人设置/覆盖标签（逗号分隔）。")
    add_platform_argument(p)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    p.add_argument("--tags", required=True, help="逗号分隔的标签；传空字符串可清空。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_tag)

    p = subparsers.add_parser("batch-tag", help="从 CSV 批量设置/追加达人标签。")
    add_platform_argument(p)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input-file", required=True, help="CSV 文件，表头必须包含 input,tags。")
    p.add_argument("--append", action="store_true", help="追加标签并去重；默认覆盖原标签。")
    add_format_argument(p, default="json")
    p.set_defaults(func=command_batch_tag)

    p = subparsers.add_parser("remark", help="为某达人设置/覆盖备注。")
    add_platform_argument(p)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    p.add_argument("--remark", required=True, help="备注文本；传空字符串可清空。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_remark)

    p = subparsers.add_parser("alert-config", help="为某达人设置告警阈值（v1.0 暂存不参与计算）。")
    add_platform_argument(p)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    p.add_argument("--viral-threshold", type=int, default=None, help="单视频播放阈值；负值表示删除该字段。")
    p.add_argument("--follower-drop-threshold", type=int, default=None, help="掉粉阈值；负值表示删除该字段。")
    p.add_argument("--max-silent-days", type=int, default=None, help="静默天数阈值；负值表示删除该字段。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_alert_config)

    p = subparsers.add_parser("monitor", help="查询单条监控记录。")
    monitor_sub = p.add_subparsers(dest="monitor_command", required=True)
    pm = monitor_sub.add_parser("get", help="返回某达人完整的监控元数据 JSON。")
    add_platform_argument(pm)
    pm.add_argument("--group-id", required=True)
    pm.add_argument("--input", required=True, help="主页 URL、@username 或裸名。")
    add_format_argument(pm, default="json")
    pm.set_defaults(func=command_monitor_get)

    p = subparsers.add_parser("snapshot-get", help="读取本地已落盘的快照（单天 / 范围 / 整 group 最新）。")
    add_platform_argument(p, allow_all=True)
    p.add_argument("--group-id", required=True)
    p.add_argument("--input", default="", help="主页 URL、@username 或裸名；--latest-only 时可省略。")
    p.add_argument("--date", default="", help="单天日期，默认今天 (YYYY-MM-DD)。与 --from/--to 互斥。")
    p.add_argument("--from", dest="from_date", default="", help="范围起始日期 (YYYY-MM-DD)。")
    p.add_argument("--to", dest="to_date", default="", help="范围结束日期 (YYYY-MM-DD)。")
    p.add_argument("--latest-only", action="store_true", help="列出该 group 下所有达人及其最近一份快照日期。")
    p.set_defaults(func=command_snapshot_get)

    p = subparsers.add_parser("digest", help="生成某群的每日日报（昨日 vs 今日）。")
    add_platform_argument(p, allow_all=True)
    p.add_argument("--group-id", required=True)
    p.add_argument("--date", default="", help="日报日期，默认今天 (YYYY-MM-DD)。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_digest)

    add_identity_arguments_recursive(parser)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_identity(getattr(args, "channel", None), getattr(args, "user_id", None))
    args.func(args)


def run() -> None:
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
