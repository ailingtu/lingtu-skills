"""argparse 解析与子命令实现。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .analysis import analyze_with_focus
from .api import fetch_material, fetch_material_comments, fetch_posts
from .config import DEFAULT_PLATFORM, FOCUS_CHOICES, SUPPORTED_PLATFORMS
from .digest import build_digest
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
    load_store,
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


def command_tutorial(args: argparse.Namespace) -> None:
    if args.format == "text":
        print(TUTORIAL_TEXT)
    else:
        print_json({"reply_text": TUTORIAL_TEXT})


def command_add(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform)
    unique_id = parse_creator_handle(args.input, platform=platform)
    raw = fetch_posts(unique_id, args.count, platform=platform)
    normalized = normalize_response(raw, platform=platform)
    monitor = upsert_monitor(normalized["creator"], args)
    snapshot_file = save_snapshot(args.group_id, normalized, today_str(args.date))
    _, analysis = analyze_with_focus(normalized, args.focus, platform=platform)
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
    raw = fetch_posts(unique_id, args.count, platform=platform)
    normalized = normalize_response(raw, platform=platform)
    monitor = find_monitor(load_store(store_path())["monitors"], args.group_id, unique_id, platform=platform)
    if monitor:
        update_monitor(args.group_id, unique_id, platform=platform, creator=normalized["creator"])
    path = save_snapshot(args.group_id, normalized, today_str(args.date))
    if args.format == "text":
        print(f"已写入快照：{path}")
    else:
        print_json({
            "group_id": args.group_id,
            "platform": platform,
            "username": unique_id,
            "date": today_str(args.date),
            "snapshot_path": str(path),
            "video_count": len(normalized.get("videos") or []),
        })


def command_digest(args: argparse.Namespace) -> None:
    platform = normalize_platform(args.platform) if args.platform else None
    digest = build_digest(args.group_id, today_str(args.date), platform=platform)
    if args.format == "text":
        print(digest["reply_text"])
    else:
        print_json(digest)


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
    add_format_argument(p, default="text")
    p.set_defaults(func=command_snapshot)

    p = subparsers.add_parser("digest", help="生成某群的每日日报（昨日 vs 今日）。")
    add_platform_argument(p, allow_all=True)
    p.add_argument("--group-id", required=True)
    p.add_argument("--date", default="", help="日报日期，默认今天 (YYYY-MM-DD)。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_digest)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


def run() -> None:
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
