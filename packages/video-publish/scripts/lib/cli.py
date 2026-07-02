"""argparse 解析与子命令实现。"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))
from lingtu_auth import add_identity_arguments, configure_identity

from .api import (
    create_post,
    list_creator_accounts,
    list_shop_products,
    require_api_key,
    resolve_creator_batch,
    upload_file,
)
from .config import (
    DEFAULT_DESKTOP,
    PLATFORM_LABELS,
    SUPPORTED_PLATFORMS,
)
from .excel_utils import (
    generate_excel_template,
    parse_date_for_filename,
    parse_datetime_to_epoch_ms,
    parse_excel_or_csv,
    parse_timezone,
    sanitize_product_title,
)
from .report import format_creators, format_products, format_publish_results
from .scheduler import auto_assign_schedule


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _format_preview_table(rows_data: list[dict[str, str]], times: list[str], tz: str, dates: list[str]) -> str:
    """将排期数据格式化为聊天预览文本。"""
    from collections import defaultdict

    # 按日期+达人分组统计
    by_day_creator: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows_data:
        parts = r["scheduled_at"].split()
        d = parts[0]
        c = r["creator_username"]
        by_day_creator[d][c] += 1

    lines = ["📋 排期预览：", ""]
    lines.append(f"类型：{'带货视频' if rows_data[0].get('platform') == 'tiktok_shop' else '养号视频'}")
    lines.append(f"时区：{tz}")
    lines.append(f"时间段：{' / '.join(times)}")
    lines.append(f"产品ID：{rows_data[0].get('product_id') or '无'}")
    lines.append("")

    # 按日期汇总
    for d in dates:
        dc = by_day_creator[d]
        total = sum(dc.values())
        creators_str = "、".join(f"{c}({n}条)" for c, n in dc.items())
        lines.append(f"{d}：共 {total} 条 — {creators_str}")

    lines.append("")
    all_creators = set(r["creator_username"] for r in rows_data)
    lines.append(f"共 {len(dates)} 天 · {len(rows_data)} 条视频 · {len(all_creators)} 个达人")
    lines.append("")
    lines.append("确认后生成 Excel，你只需补充：")
    lines.append("  · 购物车标题 · 视频文案内容 · 视频文件名")

    return "\n".join(lines)


# ── gen-csv ──────────────────────────────────────────────────

def command_gen_csv(args: argparse.Namespace) -> None:
    platform = args.platform
    date_str = parse_date_for_filename(args.date)
    tz_raw = args.timezone
    tz_iana = parse_timezone(tz_raw)
    count = max(1, args.count)
    days = max(1, args.days)

    # 生成时间列表
    from .scheduler import compute_schedule_times
    from datetime import datetime, timedelta
    times = compute_schedule_times(count)

    # 计算多天日期列表
    start_dt = datetime.strptime(date_str, "%Y-%m-%d")
    dates = [(start_dt + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(days)]

    product_id = args.product_id or ""
    if platform == "tiktok":
        product_id = ""

    # 获取达人列表（dry-run 先不调 API，用用户输入直接预览）
    raw_creators = [u.strip() for u in args.creators.split(",") if u.strip()] if args.creators else []

    if args.dry_run:
        creator_list = raw_creators if raw_creators else ["（全部已授权达人）"]
        rows_data: list[dict[str, str]] = []
        for d in dates:
            for creator in creator_list:
                for t in times:
                    rows_data.append({
                        "creator_username": creator, "platform": platform,
                        "product_id": product_id, "product_title": "", "title": "",
                        "timezone": tz_iana, "scheduled_at": f"{d} {t}", "video_file": "",
                    })
        print(_format_preview_table(rows_data, times, tz_iana, dates))
        return

    # ── 正式生成：调 API 验证达人 ──
    require_api_key()

    if raw_creators:
        creator_list = raw_creators
    else:
        result = list_creator_accounts(platform=platform)
        data = result.get("data") or {}
        items = data.get("list") or []
        creator_list = [item.get("username", "") for item in items if item.get("username")]
        if not creator_list:
            raise SystemExit(f"该平台（{PLATFORM_LABELS.get(platform, platform)}）下没有已授权的达人。")

    # 验证指定的达人是否存在
    if raw_creators:
        found, not_found = resolve_creator_batch(creator_list, platform=platform)
        if not_found:
            print(f"⚠ 以下达人未找到或未授权：{', '.join(not_found)}", file=sys.stderr)
        if not found:
            raise SystemExit("所有指定的达人均未找到或未授权。")
        creator_list = list(found.keys())

    # 构建所有行
    rows_data = []
    for d in dates:
        for creator in creator_list:
            for t in times:
                rows_data.append({
                    "creator_username": creator, "platform": platform,
                    "product_id": product_id, "product_title": "", "title": "",
                    "timezone": tz_iana, "scheduled_at": f"{d} {t}", "video_file": "",
                })

    # 生成文件夹和 Excel
    if days == 1:
        folder_name = f"视频发布_{date_str}"
    else:
        end_str = dates[-1]
        folder_name = f"视频发布_{date_str}_to_{end_str}"
    output_dir = args.output_dir or str(DEFAULT_DESKTOP / folder_name)
    output_dir = str(Path(output_dir).expanduser())
    excel_path = str(Path(output_dir) / "schedule.xlsx")

    generated = generate_excel_template(
        output_path=excel_path,
        rows_data=rows_data,
    )

    output = {
        "folder": output_dir,
        "excel": generated,
        "platform": platform,
        "date": date_str,
        "days": days,
        "dates": dates,
        "timezone": tz_iana,
        "creators": creator_list,
        "creators_count": len(creator_list),
        "videos_per_creator_per_day": count,
        "total_rows": len(rows_data),
    }

    if args.format == "json":
        print_json(output)
        return

    print(f"已在桌面创建排期文件夹：{output_dir}")
    print(f"  ├── schedule.xlsx  ← 排期表（已预填达人、时间，带下拉校验）")
    print(f"  └── （请将视频文件拖入此文件夹）")
    print()
    print(f"达人数量：{len(creator_list)}")
    print(f"日期范围：{date_str} ~ {dates[-1]}（{days} 天）")
    print(f"每达人每日：{count} 条")
    print(f"发布时间：{', '.join(times)}（{tz_iana}）")
    print(f"总排期行数：{len(rows_data)}")
    print()
    print("下一步：")
    print(f"  1. 打开 schedule.xlsx，填写 title 和 video_file（填文件名即可）")
    print(f"  2. 将所有视频文件复制到文件夹内")
    print(f"  3. 运行：lingtu_video_publish.py publish --folder {output_dir} --confirm")


# ── creators ─────────────────────────────────────────────────

def command_creators(args: argparse.Namespace) -> None:
    platform = args.platform or None
    result = list_creator_accounts(
        platform=platform,
        page_size=args.page_size,
    )
    data = result.get("data") or {}
    items = data.get("list") or []

    if args.username:
        keyword = args.username.strip().lower()
        items = [i for i in items if keyword in (i.get("username") or "").lower()]

    if args.format == "json":
        print_json({"creators": items, "total": len(items)})
        return

    print(format_creators(items))


# ── publish ──────────────────────────────────────────────────

def command_publish(args: argparse.Namespace) -> None:
    folder = Path(args.folder).expanduser()
    if not folder.exists():
        raise SystemExit(f"文件夹不存在：{folder}")
    if not folder.is_dir():
        raise SystemExit(f"路径不是文件夹：{folder}")

    # 查找排期文件
    excel_file = folder / "schedule.xlsx"
    csv_file = folder / "schedule.csv"
    if excel_file.exists():
        schedule_path = str(excel_file)
    elif csv_file.exists():
        schedule_path = str(csv_file)
    else:
        raise SystemExit(f"文件夹内未找到 schedule.xlsx 或 schedule.csv：{folder}")

    rows = parse_excel_or_csv(schedule_path)
    if not rows:
        raise SystemExit("排期表为空。")

    # 校验每行
    validation_errors: list[dict[str, Any]] = []
    valid_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        errors = _validate_row(row, idx, folder)
        if errors:
            validation_errors.append({"index": idx + 2, "row": row, "errors": errors})
        else:
            valid_rows.append(row)

    # 自动分配时间为空的行
    if valid_rows:
        rows_with_empty_time = [r for r in valid_rows if not (r.get("scheduled_at") or "").strip()]
        if rows_with_empty_time and not args.date:
            raise SystemExit("存在未填写时间的行，请使用 --date 指定日期以自动分配时间。")
        if rows_with_empty_time and args.date:
            valid_rows = auto_assign_schedule(valid_rows, parse_date_for_filename(args.date))

    # dry-run
    if not args.confirm:
        results: dict[str, Any] = {
            "mode": "dry-run",
            "total": len(rows),
            "dry_run_valid": len(valid_rows),
            "dry_run_invalid": len(validation_errors),
            "succeeded": 0,
            "failed_count": len(validation_errors),
            "rows": [],
            "validation_errors": validation_errors,
        }
        for idx, row in enumerate(valid_rows):
            results["rows"].append({
                "index": idx + 2,
                "creator_username": row.get("creator_username", ""),
                "platform": row.get("platform", ""),
                "title": row.get("title", ""),
                "video_file": row.get("video_file", ""),
                "scheduled_at": row.get("scheduled_at", ""),
                "status": "dry-run",
            })
        for ve in validation_errors:
            results["rows"].append({
                "index": ve["index"],
                "creator_username": ve["row"].get("creator_username", ""),
                "platform": ve["row"].get("platform", ""),
                "title": ve["row"].get("title", ""),
                "video_file": ve["row"].get("video_file", ""),
                "scheduled_at": ve["row"].get("scheduled_at", ""),
                "status": "failed",
                "errors": ve["errors"],
            })

        if args.format == "json":
            print_json(results)
        else:
            print(format_publish_results(results))
            if not args.confirm:
                print("\n这是 dry-run。加 --confirm 执行实际发布。", file=sys.stderr)
        if validation_errors:
            sys.exit(1)
        return

    # 批量查 creatorId
    usernames = list({r["creator_username"].strip() for r in valid_rows})
    creator_map, not_found = resolve_creator_batch(usernames)

    results: dict[str, Any] = {
        "mode": "live",
        "total": len(valid_rows),
        "succeeded": 0,
        "failed_count": 0,
        "rows": [],
    }

    for idx, row in enumerate(valid_rows):
        if idx > 0 and args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

        username = row["creator_username"].strip()
        entry: dict[str, Any] = {
            "index": idx + 2,
            "creator_username": username,
            "platform": row.get("platform", ""),
            "title": row.get("title", ""),
            "video_file": row.get("video_file", ""),
            "scheduled_at": row.get("scheduled_at", ""),
            "status": "failed",
            "post_id": None,
            "video_url": None,
            "post_status": None,
            "errors": [],
        }

        try:
            creator_info = creator_map.get(username.lower())
            if not creator_info:
                raise SystemExit(f"未找到创作者账号：{username}。请确认该账号已授权。")

            # 上传视频
            video_name = row.get("video_file", "").strip()
            video_path = folder / video_name
            if not video_path.exists():
                video_path_candidates = list(folder.glob(video_name))
                if video_path_candidates:
                    video_path = video_path_candidates[0]
                else:
                    raise SystemExit(f"视频文件不存在：{video_path}")

            print(f"[{idx + 2}/{len(valid_rows)}] 上传：{video_name}", file=sys.stderr)
            upload_result = upload_file(str(video_path))
            file_id = upload_result.get("id", "")
            video_url = upload_result.get("url", "")
            entry["video_url"] = video_url

            # 构建发布请求
            platform = row.get("platform", "tiktok_shop")
            tz_str = parse_timezone(row.get("timezone"))
            scheduled_at = None
            scheduled_tz = None
            if row.get("scheduled_at", "").strip():
                scheduled_at = parse_datetime_to_epoch_ms(row["scheduled_at"].strip(), tz_str)
                scheduled_tz = tz_str

            print(f"[{idx + 2}/{len(valid_rows)}] 发布：{username} - {row.get('title', '')}", file=sys.stderr)
            raw_product_title = row.get("product_title") or ""
            clean_product_title = sanitize_product_title(raw_product_title) if raw_product_title else ""

            post_result = create_post(
                creator_id=creator_info["creatorId"],
                title=row.get("title", "") or "Untitled",
                business_id=file_id,
                platform=platform,
                scheduled_at=scheduled_at,
                scheduled_tz=scheduled_tz,
                oauth_region=creator_info.get("oauthRegion"),
                product_id=row.get("product_id") or None,
                product_title=clean_product_title,
                product_source=row.get("product_source") or "SHOP",
            )

            entry["status"] = "success"
            entry["post_id"] = post_result.get("postId") or str(post_result.get("id", ""))
            entry["post_status"] = post_result.get("status", "")
            entry["video_url"] = post_result.get("videoUrl") or entry["video_url"]

        except SystemExit as exc:
            entry["errors"].append(str(exc))
        except Exception as exc:
            entry["errors"].append(f"{type(exc).__name__}: {exc}")

        results["rows"].append(entry)
        if entry["status"] == "success":
            results["succeeded"] += 1
        else:
            results["failed_count"] += 1

    if args.format == "json":
        print_json(results)
    else:
        print(format_publish_results(results))
    if results["failed_count"] > 0:
        sys.exit(1)


def _validate_row(row: dict[str, str], idx: int, folder: Path) -> list[str]:
    """逐行校验，返回错误信息列表。"""
    errors: list[str] = []

    creator = (row.get("creator_username") or "").strip()
    if not creator:
        errors.append("creator_username 为空")

    platform = (row.get("platform") or "").strip()
    if platform not in SUPPORTED_PLATFORMS:
        errors.append(f"platform 无效：{platform}（可选：{', '.join(SUPPORTED_PLATFORMS)}）")

    title = (row.get("title") or "").strip()
    if not title:
        errors.append("title 为空")

    if platform == "tiktok_shop":
        product_id = (row.get("product_id") or "").strip()
        if not product_id:
            errors.append("带货视频 (tiktok_shop) 必须填写 产品ID")
        product_title = (row.get("product_title") or "").strip()
        if not product_title:
            errors.append("带货视频 (tiktok_shop) 必须填写 购物车标题")

    scheduled_at = (row.get("scheduled_at") or "").strip()
    if scheduled_at:
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", scheduled_at):
            errors.append(f"scheduled_at 格式错误：{scheduled_at}（需要 YYYY-MM-DD HH:MM）")

    tz_raw = (row.get("timezone") or "").strip()
    if tz_raw:
        try:
            parse_timezone(tz_raw)
        except SystemExit as exc:
            errors.append(str(exc))

    video_file = (row.get("video_file") or "").strip()
    if not video_file:
        errors.append("video_file 为空")
    else:
        vp = folder / video_file
        if not vp.exists():
            candidates = list(folder.glob(video_file))
            if not candidates:
                errors.append(f"视频文件不存在：{video_file}")

    return errors


# ── fill ─────────────────────────────────────────────────────

def command_fill(args: argparse.Namespace) -> None:
    """更新 Excel 排期表中的单元格。"""
    folder = Path(args.folder).expanduser()
    schedule_file = folder / "schedule.xlsx"
    if not schedule_file.exists():
        schedule_file = folder / "schedule.csv"
    if not schedule_file.exists():
        raise SystemExit(f"文件夹内未找到排期表：{folder}")

    try:
        from openpyxl import load_workbook
    except ImportError:
        raise SystemExit("需要 openpyxl 库：pip install openpyxl")

    wb = load_workbook(str(schedule_file))
    ws = wb.active
    if ws is None:
        raise SystemExit("无法打开工作表。")

    # 读取表头映射
    headers = [str(c.value or "").strip() for c in next(ws.iter_rows(min_row=1, max_row=1))]
    from .config import COLUMN_LABEL_TO_KEY, COLUMN_LABELS
    col_map: dict[str, int] = {}
    for idx, h in enumerate(headers):
        eng = COLUMN_LABEL_TO_KEY.get(h, h)
        col_map[eng] = idx

    target_col = args.col
    if target_col not in col_map:
        avail = [COLUMN_LABELS.get(c, c) for c in col_map]
        raise SystemExit(f"找不到列「{target_col}」，可用列：{', '.join(avail)}")
    col_idx = col_map[target_col]

    updated = 0

    # 自动填产品标题
    if args.auto_product_title:
        require_api_key()
        pid_col_idx = col_map.get("product_id", -1)
        updated_count = 0
        for row_idx in range(2, ws.max_row + 1):
            pid = str(ws.cell(row=row_idx, column=pid_col_idx + 1).value or "").strip()
            if not pid:
                continue
            creator = str(ws.cell(row=row_idx, column=col_map.get("creator_username", 0) + 1).value or "").strip()
            if not creator:
                continue
            try:
                # 尝试从 shop 产品搜索获取标题
                from .api import list_shop_products, resolve_creator_batch
                cinfo = resolve_creator_batch([creator]).get(creator.lower(), {})
                cid = (cinfo or {}).get("creatorId", "")
                if cid:
                    result = list_shop_products(creator_id=cid, page_size=5, title_keyword=pid)
                    products = (result.get("data") or {}).get("products") or []
                    # 匹配 product id
                    for p in products:
                        if str(p.get("id", "")) == pid:
                            from .excel_utils import sanitize_product_title
                            title = sanitize_product_title(p.get("title", ""))
                            ws.cell(row=row_idx, column=col_idx + 1).value = title
                            updated_count += 1
                            break
            except SystemExit:
                pass  # 单个失败跳过，继续其他行
        updated = updated_count
        print(f"已自动填入 {updated} 个购物车标题", file=sys.stderr)

    # 按行号填充
    elif args.row is not None:
        row_idx = args.row + 1  # 0-indexed → Excel row (header=1)
        ws.cell(row=row_idx, column=col_idx + 1).value = args.value
        updated = 1

    # 按 creator 筛选填充
    elif args.creator:
        creator_col_idx = col_map.get("creator_username", 0)
        for row_idx in range(2, ws.max_row + 1):
            c = str(ws.cell(row=row_idx, column=creator_col_idx + 1).value or "").strip()
            if c.lower() == args.creator.lower():
                ws.cell(row=row_idx, column=col_idx + 1).value = args.value
                updated += 1

    # 填充所有行
    elif args.value:
        for row_idx in range(2, ws.max_row + 1):
            ws.cell(row=row_idx, column=col_idx + 1).value = args.value
            updated = ws.max_row - 1

    wb.save(str(schedule_file))
    wb.close()

    if args.format == "json":
        print_json({"updated": updated, "col": target_col})
    else:
        print(f"已更新 {updated} 行：{COLUMN_LABELS.get(target_col, target_col)}")


# ── products search ──────────────────────────────────────────

def command_products_search(args: argparse.Namespace) -> None:
    username = args.creator_username.strip()
    platform = args.platform or "tiktok_shop"
    source = args.source or "shop"

    require_api_key()

    creator_info = resolve_creator_batch([username], platform=platform)[0].get(username.lower())
    if not creator_info:
        raise SystemExit(f"未找到创作者账号：{username}")

    creator_id = creator_info["creatorId"]
    if not creator_id:
        raise SystemExit(f"创作者 {username} 缺少 creatorId")

    if source == "shop":
        result = list_shop_products(
            creator_id=creator_id,
            page_size=args.page_size,
            title_keyword=args.keyword or None,
        )
    else:
        from .api import list_showcase_products
        result = list_showcase_products(
            creator_id=creator_id,
            page_size=args.page_size,
        )

    data = result.get("data") or {}
    products = data.get("products") or []

    if args.keyword and source == "shop":
        keyword = args.keyword.strip().lower()
        products = [p for p in products if keyword in (p.get("title") or "").lower()]

    if args.format == "json":
        print_json({"products": products, "total": len(products)})
        return

    print(format_products(products, source))


# ── argparse helpers ─────────────────────────────────────────

def add_format_argument(parser: argparse.ArgumentParser, default: str = "json") -> None:
    parser.add_argument("--format", choices=("json", "text"), default=default, help="输出格式。")


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


# ── parser ───────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="灵途批量视频发布。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # gen-csv
    p = subparsers.add_parser("gen-csv", help="生成排期 Excel 模板（桌面文件夹）。")
    p.add_argument("--platform", choices=SUPPORTED_PLATFORMS, required=True, help="发布平台。")
    p.add_argument("--creators", default=None, help="逗号分隔的达人用户名，不传则取全部已授权。")
    p.add_argument("--date", required=True, help="起始日期 YYYY-MM-DD。")
    p.add_argument("--days", type=int, default=1, help="连续发布天数，默认 1。")
    p.add_argument("--count", type=int, default=3, help="每达人每日发布条数，默认 3。")
    p.add_argument("--product-id", default="", help="产品 ID（仅 tiktok_shop）。")
    p.add_argument("--timezone", required=True, help="时区简码或 IANA，如 EST、PST、CN、America/New_York。")
    p.add_argument("--output-dir", default=None, help="自定义输出目录，默认 ~/Desktop/视频发布_{date}/。")
    p.add_argument("--dry-run", action="store_true", help="仅预览排期表，不生成文件。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_gen_csv)

    # creators
    p = subparsers.add_parser("creators", help="列出已授权的创作者账号。")
    p.add_argument("--platform", choices=SUPPORTED_PLATFORMS, default=None, help="筛选平台。")
    p.add_argument("--username", default="", help="按用户名搜索。")
    p.add_argument("--page-size", type=int, default=200, help="每页数量。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_creators)

    # publish
    p = subparsers.add_parser("publish", help="从文件夹读取排期表并执行发布。")
    p.add_argument("--folder", required=True, help="排期文件夹路径。")
    p.add_argument("--date", default="", help="自动排期日期 YYYY-MM-DD（未填时间的行必传）。")
    p.add_argument("--confirm", action="store_true", help="确认发布（默认 dry-run）。")
    p.add_argument("--sleep-ms", type=int, default=500, help="每行操作间隔毫秒，默认 500。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_publish)

    # fill
    p = subparsers.add_parser("fill", help="更新 Excel 排期表单元格。")
    p.add_argument("--folder", required=True, help="排期文件夹路径。")
    p.add_argument("--col", required=True, help="要填充的列名（英文 key 或中文名）。")
    p.add_argument("--value", default="", help="填充的值（所有行/按 --creator/按 --row）。")
    p.add_argument("--row", type=int, default=None, help="行号（0=第一行数据）。")
    p.add_argument("--creator", default=None, help="只填充指定达人的行。")
    p.add_argument("--auto-product-title", action="store_true", help="自动从产品 API 搜索并填入购物车标题。")
    add_format_argument(p, default="text")
    p.set_defaults(func=command_fill)

    # products
    pp = subparsers.add_parser("products", help="商品查询（子命令）。")
    pps = pp.add_subparsers(dest="products_command", required=True)
    ps = pps.add_parser("search", help="搜索创作者的商品。")
    ps.add_argument("--creator-username", required=True, help="创作者用户名。")
    ps.add_argument("--platform", choices=SUPPORTED_PLATFORMS, default="tiktok_shop", help="平台。")
    ps.add_argument("--source", choices=("shop", "showcase"), default="shop", help="商品来源。")
    ps.add_argument("--keyword", default="", help="商品标题关键词。")
    ps.add_argument("--page-size", type=int, default=20, help="每页数量。")
    add_format_argument(ps, default="text")
    ps.set_defaults(func=command_products_search)

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
