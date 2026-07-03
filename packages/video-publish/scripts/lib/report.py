"""输出格式化：文本表格、JSON 结果汇总。"""

from __future__ import annotations

from typing import Any

from .config import PLATFORM_LABELS, PUBLISH_RECORDS_URL


def format_creators(creators: list[dict[str, Any]]) -> str:
    """格式化达人列表文本输出。"""
    if not creators:
        return "未找到已授权的达人账号。"

    lines = [f"共 {len(creators)} 个已授权达人：\n"]
    header = f"{'用户名':<24} {'平台':<12} {'区域':<10} {'用户类型':<12} {'标签'}"
    lines.append(header)
    lines.append("-" * len(header))

    for c in creators:
        auth_source = c.get("authSource", "")
        platform = _platform_label(auth_source)
        region = c.get("registerRegion") or c.get("selectionRegion") or "-"
        user_type = c.get("userType") or c.get("sellerType") or "-"
        tags = ", ".join(c.get("tagNames") or []) or "-"
        lines.append(
            f"{c.get('username', '?'):<24} {platform:<12} {region:<10} {user_type:<12} {tags}"
        )
    return "\n".join(lines)


def _platform_label(auth_source: str) -> str:
    if auth_source in ("TIKTOK_SHOP", "tiktok_shop"):
        return "TikTok Shop"
    elif auth_source in ("TIKTOK_LOGIN_KIT", "tiktok"):
        return "TikTok (养号)"
    return auth_source or "-"


def format_publish_results(results: dict[str, Any]) -> str:
    """格式化发布结果文本输出。"""
    mode = results.get("mode", "dry-run")
    total = results.get("total", 0)
    succeeded = results.get("succeeded", 0)
    failed = results.get("failed_count", 0)
    rows: list[dict[str, Any]] = results.get("rows", [])

    if mode == "dry-run":
        title = f"[DRY-RUN] 排期校验完成：共 {total} 条"
        if results.get("needs_edit_count", 0) > 0:
            title += f"，{results['needs_edit_count']} 条需修改"
        title += "\n加 --confirm 执行实际发布。"
    elif mode == "needs-edit":
        title = (
            f"排期表需要修改：共 {total} 条，"
            f"{results.get('needs_edit_count', 0)} 条需修改，{results.get('dry_run_valid', 0)} 条可发布。\n"
            "这通常是用户编辑 CSV 时新增或删减行导致的，不算发布失败。请按提示修改后再确认发布。"
        )
    else:
        video_type = results.get("video_type") or _video_type_from_rows(rows)
        lines = [
            f"发布完成，发布 {succeeded} 条 {video_type} 视频。",
            f"发布结果：共 {total} 条，成功 {succeeded}，失败 {failed}。",
        ]
        basics = _format_publish_basics(results, rows)
        if basics:
            lines.append(f"发布基本信息：{basics}")
        lines.append(f"请前往发布记录确认发布内容：{PUBLISH_RECORDS_URL}")
        title = "\n".join(lines)

    lines = [title, ""]

    success_rows = [r for r in rows if r.get("status") == "success"]
    failed_rows = [r for r in rows if r.get("status") == "failed"]
    dry_rows = [r for r in rows if r.get("status") == "dry-run"]
    needs_edit_rows = [r for r in rows if r.get("status") == "needs-edit"]

    if success_rows:
        lines.append("成功：")
        for r in success_rows:
            post_id = r.get("post_id") or "-"
            post_status = r.get("post_status") or "-"
            lines.append(
                f"  - @{r.get('creator_username','?')} "
                f"\"{r.get('title','')}\" "
                f"→ postId={post_id} status={post_status}"
            )
        lines.append("")

    if failed_rows:
        lines.append("失败：")
        for r in failed_rows:
            errors = r.get("errors", [])
            err_text = "; ".join(errors) if errors else "未知错误"
            lines.append(f"  - 第 {r.get('index', '?')} 行 (@{r.get('creator_username', '?')})：{err_text}")
        lines.append("")

    if needs_edit_rows:
        lines.append("需修改：")
        for r in needs_edit_rows:
            errors = r.get("errors", [])
            err_text = "; ".join(errors) if errors else "请检查该行内容"
            lines.append(f"  - 第 {r.get('index', '?')} 行 (@{r.get('creator_username', '?') or '-'})：{err_text}")
        lines.append("")

    if dry_rows:
        lines.append("待发布（dry-run）：")
        for r in dry_rows:
            lines.append(
                f"  - @{r.get('creator_username','?')} "
                f"[{PLATFORM_LABELS.get(r.get('platform',''), r.get('platform',''))}] "
                f"时间={r.get('scheduled_at','?')} "
                f"视频={r.get('video_file','?')}"
            )

    return "\n".join(lines)


def _video_type_from_rows(rows: list[dict[str, Any]]) -> str:
    platforms = {row.get("platform") for row in rows if row.get("platform")}
    if platforms == {"tiktok_shop"}:
        return "带货"
    if platforms == {"tiktok"}:
        return "普通/养号"
    return "混合"


def _format_publish_basics(results: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    creators = sorted({str(row.get("creator_username") or "").strip() for row in rows if row.get("creator_username")})
    platforms = sorted({PLATFORM_LABELS.get(str(row.get("platform") or ""), str(row.get("platform") or "")) for row in rows if row.get("platform")})
    scheduled = [str(row.get("scheduled_at") or "").strip() for row in rows if row.get("scheduled_at")]
    parts: list[str] = []
    if platforms:
        parts.append(f"类型 {'、'.join(platforms)}")
    if creators:
        sample = "、".join(f"@{creator}" for creator in creators[:5])
        suffix = f" 等 {len(creators)} 个达人" if len(creators) > 5 else ""
        parts.append(f"达人 {sample}{suffix}")
    if scheduled:
        parts.append(f"时间 {min(scheduled)} 至 {max(scheduled)}")
    if results.get("records_url"):
        parts.append(f"记录页 {results['records_url']}")
    return "；".join(parts)


def format_products(products: list[dict[str, Any]], source: str) -> str:
    """格式化产品搜索列表。"""
    if not products:
        return "未找到商品。"

    src_label = "店铺" if source == "shop" else "橱窗"
    lines = [f"{src_label}商品（共 {len(products)} 个）：\n"]
    for p in products:
        pid = p.get("id") or "-"
        title = p.get("title") or "-"
        price_info = p.get("price") or {}
        if isinstance(price_info, dict):
            amount = price_info.get("amount") or price_info.get("originalPrice", {}).get("minimumAmount") or "-"
        else:
            amount = "-"
        lines.append(f"  {pid}  {title}  ¥{amount}")
    return "\n".join(lines)
