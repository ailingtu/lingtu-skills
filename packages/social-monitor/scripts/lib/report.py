"""把分析结果格式化为人类可读的中文报告。"""

from __future__ import annotations

from typing import Any

from .config import DEFAULT_PLATFORM, FOCUS_LABELS
from .utils import format_number, platform_label


def build_profile_line(creator: dict[str, Any]) -> str:
    follower = creator.get("follower_count")
    aweme = creator.get("aweme_count")
    parts: list[str] = []
    if follower is not None:
        parts.append(f"粉丝 {format_number(follower)}")
    if aweme is not None:
        parts.append(f"作品 {format_number(aweme)}")
    return "（" + "，".join(parts) + "）" if parts else ""


def build_header(creator: dict[str, Any], remark: str, focus: str, video_count: int) -> str:
    label = FOCUS_LABELS.get(focus, focus)
    platform = platform_label(creator.get("platform") or DEFAULT_PLATFORM)
    return (
        f"已加入监控：{platform} @{creator.get('username','')} {creator.get('nickname','')}{build_profile_line(creator)}\n"
        f"备注：{remark or '无'}\n"
        f"分析方向：{label}（最近 {video_count} 条视频）\n"
    )


def build_footer(creator: dict[str, Any]) -> str:
    return f"\n建议：是否要把该账号加入每日监控？回复\"加入每日监控 @{creator.get('username','')}\"即可。"


def build_overall_report(creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    frequency = analysis["frequency"]
    viral = analysis["viral"]
    themes = "、".join(analysis["top_themes"]) or "暂未归类"
    hashtags = "、".join(f"#{t}" for t in analysis["tag_signals"]["top_hashtags"]) or "暂无明显 hashtag"
    hook = analysis["hooks"]["examples"][0] if analysis["hooks"]["examples"] else "暂无样例"
    top_videos = analysis["viral"]["top_views"][:3]
    top_lines = "\n".join(
        f"   - {v['video_id']}：{format_number(v['views'])} 播放，{v['caption']}"
        for v in top_videos
    )

    body = (
        f"\n1. 发布频率：\n"
        f"最近 7 天发布 {frequency['last_7_days']} 条，最近 30 天发布 {frequency['last_30_days']} 条，"
        f"平均 {format_number(frequency['avg_days_per_video'])} 天一条。{frequency['signal']}。\n\n"
        f"2. 爆款表现：\n"
        f"最高播放 {format_number(viral['max_views'])}，有 {viral['viral_count']} 条明显跑出。Top 3：\n"
        f"{top_lines}\n\n"
        f"3. 内容方向：\n"
        f"主要内容为 {themes}。\n\n"
        f"4. 爆款开头：\n"
        f"高播放视频常用痛点/疑问/强指令开头，例如：\"{hook}\"。\n\n"
        f"5. 标签线索：\n"
        f"高频 hashtag：{hashtags}。{analysis['tag_signals']['signal']}\n\n"
        f"6. 内容结构：\n"
        f"{analysis['structure']}。\n\n"
        f"7. 账号价值判断：\n"
        f"{analysis['account_value']}"
    )
    return (
        build_header(creator, remark, "overall", analysis["video_count"])
        + body
        + build_footer(creator)
    )


def build_posting_report(creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    posting = analysis.get("posting") or {}
    frequency = analysis["frequency"]
    slots = posting.get("top_slots") or []
    cadence = posting.get("weekly_trend") or []
    durations = posting.get("duration_buckets") or []
    viral_window = posting.get("viral_window") or {}

    if slots:
        slot_lines = "\n".join(
            f"   - {item['weekday']} {item['hour']:02d}:00 — {item['count']} 条，平均播放 {format_number(item['avg_views'])}"
            for item in slots
        )
    else:
        slot_lines = "   - 暂无足够样本判断时段。"

    if cadence:
        cadence_lines = "\n".join(
            f"   - {item['week']}：发布 {item['count']} 条"
            for item in cadence
        )
    else:
        cadence_lines = "   - 暂无足够样本。"

    if durations:
        duration_lines = "\n".join(
            f"   - {item['label']}：{item['count']} 条，平均播放 {format_number(item['avg_views'])}"
            for item in durations
        )
    else:
        duration_lines = "   - 暂无时长数据。"

    viral_summary = viral_window.get("summary") or "样本不足，无法判断爆款是否集中在固定时段。"

    body = (
        f"\n1. 发布节奏：\n"
        f"最近 7 天 {frequency['last_7_days']} 条，最近 30 天 {frequency['last_30_days']} 条，"
        f"平均 {format_number(frequency['avg_days_per_video'])} 天一条。{frequency['signal']}。\n\n"
        f"2. 发布时段画像（Top 3 时段）：\n{slot_lines}\n\n"
        f"3. 周度发布趋势（最近 4 周）：\n{cadence_lines}\n\n"
        f"4. 时长策略：\n{duration_lines}\n\n"
        f"5. 爆款时间窗：\n   {viral_summary}\n\n"
        f"6. 策略判断：\n   {posting.get('verdict','暂无判断')}"
    )
    return (
        build_header(creator, remark, "posting", analysis["video_count"])
        + body
        + build_footer(creator)
    )


def build_content_report(creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    content = analysis.get("content") or {}
    themes = "、".join(analysis["top_themes"]) or "暂未归类"
    hashtags = "、".join(f"#{t}" for t in analysis["tag_signals"]["top_hashtags"]) or "暂无明显 hashtag"
    hooks = content.get("hook_distribution") or []
    sample_hooks = content.get("hook_examples") or analysis["hooks"]["examples"][:3]
    durations = content.get("duration_engagement") or []
    engagement = content.get("engagement_profile") or {}
    caption_style = content.get("caption_style") or {}

    if hooks:
        hook_lines = "\n".join(
            f"   - {item['pattern']}：{item['count']} / {item['total']} 条（{item['ratio']*100:.0f}%）"
            for item in hooks
        )
    else:
        hook_lines = "   - 暂未匹配到显著钩子句式。"

    if sample_hooks:
        hook_examples = "\n".join(f"   - \"{c}\"" for c in sample_hooks)
    else:
        hook_examples = "   - 暂无样例。"

    if durations:
        duration_lines = "\n".join(
            f"   - {item['label']}：{item['count']} 条，平均播放 {format_number(item['avg_views'])}，"
            f"平均互动率 {item['avg_engagement']*100:.2f}%"
            for item in durations
        )
    else:
        duration_lines = "   - 暂无时长数据。"

    engagement_strong = engagement.get("strongest", "暂无")
    engagement_line = (
        f"点赞率 {engagement.get('like_rate',0)*100:.2f}%，"
        f"评论率 {engagement.get('comment_rate',0)*100:.2f}%，"
        f"分享率 {engagement.get('share_rate',0)*100:.2f}%，"
        f"收藏率 {engagement.get('save_rate',0)*100:.2f}%"
    )

    body = (
        f"\n1. 内容方向：\n   {themes}\n\n"
        f"2. 开头钩子分布：\n{hook_lines}\n\n"
        f"3. 爆款开头样例：\n{hook_examples}\n\n"
        f"4. 时长 × 互动：\n{duration_lines}\n\n"
        f"5. 互动率画像：\n   {engagement_line}。该账号最强项是「{engagement_strong}」。\n\n"
        f"6. 文案风格：\n   平均字数 {caption_style.get('avg_length',0)}，标准差 {caption_style.get('stddev',0)}。"
        f"风格倾向：{caption_style.get('verdict','暂无判断')}\n\n"
        f"7. 标签线索：\n   {hashtags}。{analysis['tag_signals']['signal']}"
    )
    return (
        build_header(creator, remark, "content", analysis["video_count"])
        + body
        + build_footer(creator)
    )


def build_report_text(focus: str, creator: dict[str, Any], remark: str, analysis: dict[str, Any]) -> str:
    if focus == "posting":
        return build_posting_report(creator, remark, analysis)
    if focus == "content":
        return build_content_report(creator, remark, analysis)
    return build_overall_report(creator, remark, analysis)


def build_material_text(video: dict[str, Any]) -> str:
    platform = platform_label(video.get("platform") or DEFAULT_PLATFORM)
    return (
        f"【{platform} 素材数据】@{video.get('username','')} / {video.get('video_id','')}\n"
        f"播放 {format_number(video.get('views'))}，点赞 {format_number(video.get('likes'))}，"
        f"评论 {format_number(video.get('comments'))}，分享 {format_number(video.get('shares'))}，"
        f"收藏 {format_number(video.get('saves'))}。\n"
        f"发布时间：{video.get('publish_time') or '-'}；时长：{format_number(video.get('duration'))} 秒。\n"
        f"文案：{video.get('caption') or '-'}"
    )


TUTORIAL_TEXT = """【如何添加社媒监控（TikTok / Instagram）】

1. 找到对方的主页链接：
   - TikTok：https://www.tiktok.com/@mrbeast
   - Instagram：https://www.instagram.com/mrbeast/
   或者直接发送 @mrbeast、mrbeast 也可以。
2. 在群里 @机器人，发送：
       添加监控 https://www.tiktok.com/@mrbeast 备注：对标账号
       添加监控 https://www.instagram.com/mrbeast/ 平台：instagram 备注：对标账号
   机器人会立刻拉取最近 40 条视频，并给出账号画像、爆款 Top3、内容方向等分析。
3. 分析返回后，机器人会询问"是否加入每日监控"。回复"加入每日监控 @mrbeast"即可订阅。
   订阅后，每天早上 8 点会在群里发送一份昨日 vs 今日的内容情报日报。
4. 想查看本群当前监控了哪些达人，发送：查看监控列表
5. 想取消某个达人的每日订阅，发送：取消每日监控 @mrbeast
6. 想完全移除监控，发送：移除监控 @mrbeast

提示：
- 不同群的监控列表互相独立；同一群下不同平台的同名账号也会分开存储。
- 不写"平台："时默认 TikTok。
- 每日日报包含涨粉 Top、新爆款 Top、播放量增长 Top、停更/高频发布预警，以及逐账号速览。
- 第一天加入的达人，次日才能产生对比数据。
- 想换个分析视角，可以加方向，例如：
    添加监控 @mrbeast 方向：发布策略
    添加监控 @mrbeast 方向：内容形式
  默认是综合画像。"""
