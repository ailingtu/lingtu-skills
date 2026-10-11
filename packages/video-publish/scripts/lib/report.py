"""输出格式化：文本表格、JSON 结果汇总。"""

from __future__ import annotations

from typing import Any

from .config import PLATFORM_LABELS, PUBLISH_RECORDS_URL


def format_creators(creators: list[dict[str, Any]]) -> str:
    """格式化达人列表文本输出。"""
    if not creators:
        return "未找到已授权的达人账号。"

    lines = [f"共 {len(creators)} 个已授权达人：\n"]
    header = f"{'用户名':<24} {'平台':<12} {'区域':<10} {'图文':<6} {'用户类型':<12} {'标签'}"
    lines.append(header)
    lines.append("-" * len(header))

    for c in creators:
        auth_source = c.get("authSource", "")
        platform = _platform_label(auth_source)
        region = c.get("registerRegion") or c.get("selectionRegion") or "-"
        user_type = c.get("userType") or c.get("sellerType") or "-"
        tags = ", ".join(c.get("tagNames") or []) or "-"
        if "canPublishPhoto" in c:
            photo_flag = "是" if c.get("canPublishPhoto") else "否"
        else:
            photo_flag = "-"
        lines.append(
            f"{c.get('username', '?'):<24} {platform:<12} {region:<10} {photo_flag:<6} {user_type:<12} {tags}"
        )
    return "\n".join(lines)


def _platform_label(auth_source: str) -> str:
    if auth_source in ("TIKTOK_SHOP", "tiktok_shop"):
        return "TikTok Shop"
    elif auth_source in ("TIKTOK_LOGIN_KIT", "tiktok"):
        return "TikTok (养号)"
    if auth_source == "TIKTOK_BUSINESS_ACCOUNT_API":
        return "TikTok (高级版)"
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
        if "图文" in video_type:
            summary = f"已提交 {succeeded} 条{video_type}任务，等待平台发布。"
        else:
            summary = f"已提交 {succeeded} 条 {video_type} 视频任务，等待平台发布。"
        lines = [
            summary,
            f"提交结果：共 {total} 条，已提交 {succeeded}，失败或状态不明 {failed}，跳过 {results.get('skipped_count', 0)}。",
        ]
        basics = _format_publish_basics(results, rows)
        if basics:
            lines.append(f"发布基本信息：{basics}")
        lines.append(f"请前往发布记录确认发布内容：{PUBLISH_RECORDS_URL}")
        title = "\n".join(lines)

    lines = [title, ""]

    success_rows = [r for r in rows if r.get("status") == "success"]
    failed_rows = [r for r in rows if r.get("status") in ("failed", "unknown")]
    skipped_rows = [r for r in rows if r.get("status") == "skipped"]
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
            lines.append(f"  - 第 {r.get('index', '?')} 行 (@{r.get('creator_username', '?')}) [{r.get('status')}]：{err_text}")
        lines.append("")

    if skipped_rows:
        lines.append("跳过（已有记录）：")
        for r in skipped_rows:
            lines.append(f"  - @{r.get('creator_username')} postId={r.get('post_id') or '-'}：" + "; ".join(r.get('errors', [])))
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
            media = r.get("image_files") or r.get("video_file") or "?"
            media_label = "图片" if (r.get("media_type") or "").lower() == "photo" else "视频"
            lines.append(
                f"  - @{r.get('creator_username','?')} "
                f"[{PLATFORM_LABELS.get(r.get('platform',''), r.get('platform',''))}] "
                f"时间={r.get('scheduled_at','?')} 时区={r.get('timezone', '')} "
                f"文案={r.get('title', '')} 商品={r.get('product_id', '')} 购物车标题={r.get('product_title', '')} "
                f"{media_label}={media} 设置={r.get('publish_options', {})}"
            )

    return "\n".join(lines)


def _video_type_from_rows(rows: list[dict[str, Any]]) -> str:
    media_types = {(str(row.get("media_type") or "").strip().lower()) for row in rows}
    platforms = {row.get("platform") for row in rows if row.get("platform")}
    if media_types == {"photo"} and platforms == {"tiktok_shop"}:
        return "带货图文"
    if platforms == {"tiktok_shop"}:
        return "带货"
    if platforms == {"tiktok_business"}:
        return "高级版不带货图文" if media_types == {"photo"} else "高级版不带货"
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
