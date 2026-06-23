---
name: lingtu-social-monitor
version: 0.8.0
description: 社媒达人/竞品监控、单条视频素材数据与评论抓取/导出/下载、日报、告警。当前已接入 TikTok 和 Instagram 的账号视频列表、单条视频数据、视频评论接口；Instagram 使用 `/v1/influencer/ins/fetchPosts`、`/v1/material/ins/fetch`、`/v1/material/ins/fetchComments`。支持单条/批量添加监控（可一键开启每日订阅）、视频评论导出、评论区反馈、单条视频实时数据、群级监控列表、即时分析（综合/发布策略/内容形式）、每日订阅、按"昨日 vs 今日"差异生成中文日报和结构化告警事件、本地快照单天/范围/最新查询、标签/备注/告警阈值（暂存）等监控元数据维护。
---

# 社媒达人 / 竞品监控与日报

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## 适用场景

当用户要求监控 TikTok / Instagram 达人、竞品、对标账号，查看群里的监控列表，订阅每日内容情报日报，导出/下载/获取某条视频评论，总结评论区反馈，更新一批视频实时数据，或基于已抓取的视频数据出报告时，调用本技能。每个群（`group_id`）的监控列表互相独立；同一群下不同平台的同名账号也会分开存储。

如果用户要"分析某个视频内容/讲了什么/复刻/二创"，优先使用 `lingtu-video-understand`；若问题同时要求结合播放、点赞、评论或评论区反馈，先用本技能的 `material` / `comments` 获取数据，再把结果作为分析上下文交给视频理解流程。

## 使用流程

```text
用户在群里 @机器人 ──▶
  ├─ "如何添加监控" / "怎么用" ── tutorial
  ├─ "添加监控 <链接|@用户名>" ── add（即时分析 + 落今日快照；可加 --enable-daily 一步到位）
  ├─ "批量添加 ..." ── batch-add（不做即时分析，可 --enable-daily / --tags / --remark）
  ├─ 答复"加入每日监控 @xxx" ── enable-daily（订阅）
  ├─ "查看监控列表" / "看一下都监控了谁" ── list
  ├─ "查这个达人详情" ── monitor get
  ├─ "打个标签 / 改备注 / 改告警阈值" ── tag / remark / alert-config
  ├─ "取消每日监控 @xxx" ── disable-daily
  └─ "移除监控 @xxx" ── remove

每天早 8 点（编排层 cron 触发）─▶
  for 群: for 达人: snapshot；最后一步 digest 输出当日中文日报到群里。
  digest JSON 中已内嵌 alerts；如需"刚抓完立刻看"可调 alerts check。
```

第一天添加的达人，次日才会出现"昨日 vs 今日"对比；当日无对照时，速览行会标注"首日无对比"。

## 配置

获取 API Key：https://app.ailingtu.com/api-key-management。设置环境变量：

```bash
export LINGTU_API_KEY="..."
```

桌面应用使用：

```bash
launchctl setenv LINGTU_API_KEY "..."   # macOS
setx LINGTU_API_KEY "..."               # Windows
```

可选环境变量：

| 变量 | 含义 | 默认 |
|------|------|------|
| `LINGTU_AI_BASE_URL` | API base URL | `https://api.ailingtu.com` |
| `LINGTU_SOCIAL_MONITOR_STORE` | 监控元数据 JSON 文件路径 | `~/.lingtu/social-monitor/monitors.json` |
| `LINGTU_SOCIAL_MONITOR_SNAPSHOTS` | 每日快照根目录 | `~/.lingtu/social-monitor/snapshots` |

API Key 通过请求头 `x-api-key` 发送。请勿提交密钥或私有监控数据。

API 字段、`code` 取值参见 `references/api.md`，改接口前先更新该文档。

## 子命令

所有命令默认输出文本，便于直接贴回群消息；加 `--format json` 用于编排层。需要平台数据的命令接受 `--platform tiktok|instagram`，当前默认 `tiktok`。`--input` 接主页 URL、`@username` 或裸名。

当前状态：

- `--platform tiktok`：账号视频列表、单条视频素材数据、评论抓取、监控、日报均已接入。
- `--platform instagram`：账号视频列表、单条视频素材数据、评论抓取、监控、日报均已接入；评论支持 `--sort-order popular|newest`。
- Instagram 的列表接口（fetchPosts）只返回 `commentCount` / `videoPlayCount`（非视频帖均为 null），没有 `likeCount` 之外的互动指标；爆款 / 互动率分析以 `material` 单条接口为准。

### 教程
```bash
python3 scripts/lingtu_social_monitor.py tutorial
```

### 添加监控（即时分析 + 落今日快照）
```bash
python3 scripts/lingtu_social_monitor.py add \
  --platform tiktok \
  --input "https://www.tiktok.com/@mrbeast" \
  --group-id feishu_group_001 \
  --remark "对标账号" \
  --tags "top-tier,NBA" \
  --focus overall \
  --format text

# 一键添加并开启每日监控
python3 scripts/lingtu_social_monitor.py add \
  --platform tiktok \
  --input "@mrbeast" \
  --group-id feishu_group_001 \
  --enable-daily
```

### 批量添加监控（不做即时分析）
```bash
# 逗号分隔
python3 scripts/lingtu_social_monitor.py batch-add \
  --platform tiktok \
  --inputs "@mrbeast,@tommy,@jane" \
  --group-id feishu_group_001 \
  --enable-daily

# 文件读取（每行一个；# 开头注释；空行忽略）
python3 scripts/lingtu_social_monitor.py batch-add \
  --platform tiktok \
  --inputs-file ./kols.txt \
  --group-id feishu_group_001 \
  --tags "top-tier" \
  --enable-daily \
  --sleep-ms 600 \
  --retries 2 \
  --retry-sleep-ms 1500 \
  --request-timeout 30 \
  --progress-every 10
```

JSON 输出包含 `success[] / failed[] / total / succeeded / failed_count`，失败项保留原始 `input` 与中文错误描述，便于编排层重试或汇总；成功项与失败项都会带 `attempts`。`--sleep-ms` 控制相邻请求间隔（默认 600ms），用于规避上游限速。`batch-add` 默认对单个达人失败重试 2 次；`--retries` / `--retry-sleep-ms` / `--request-timeout` 可在 Instagram 接口偶发慢请求或 500 时调大。`uniqueId` 不存在会直接失败，不做重试。批量过程中默认向 stderr 输出进度（开始、成功数 1/2/4/8... 里程碑、每处理 10 条、结束），不影响 stdout 的 JSON；可用 `--progress-every` 调整频率，或 `--no-progress` 关闭。

`--focus` 控制分析方向（默认 `overall`）：

| 值 | 含义 | 报告侧重 |
|----|------|----------|
| `overall` | 综合画像（默认） | 频率 / 爆款 / 内容方向 / 钩子 / hashtag / 价值判断 |
| `posting` | 发布策略 | 节奏 + 时段画像 + 周度趋势 + 时长策略 + 爆款时间窗 |
| `content` | 内容形式 | 钩子句式分布 + 时长×互动 + 互动率画像 + 文案风格 |

`analyze` 也接受 `--focus`，可基于已有 JSON 切换分析方向。

### 列出群内监控
```bash
python3 scripts/lingtu_social_monitor.py list --group-id feishu_group_001
python3 scripts/lingtu_social_monitor.py list --platform tiktok --group-id feishu_group_001
python3 scripts/lingtu_social_monitor.py list --group-id feishu_group_001 --daily-only
```

### 开启 / 关闭每日监控
```bash
python3 scripts/lingtu_social_monitor.py enable-daily  --platform tiktok --group-id feishu_group_001 --input mrbeast
python3 scripts/lingtu_social_monitor.py disable-daily --platform tiktok --group-id feishu_group_001 --input mrbeast
```

### 移除监控
```bash
python3 scripts/lingtu_social_monitor.py remove --platform tiktok --group-id feishu_group_001 --input mrbeast
```

### 单条快照（每日 8 点编排循环调用）
```bash
python3 scripts/lingtu_social_monitor.py snapshot \
  --platform tiktok --group-id feishu_group_001 --input mrbeast --count 40
```

### 读取本地快照
`snapshot-get` 不发起请求，直接读 `~/.lingtu/social-monitor/snapshots/{group}/{platform}/{creator_id}/{YYYY-MM-DD}.json`：

```bash
# 单天（默认今天）
python3 scripts/lingtu_social_monitor.py snapshot-get \
  --platform tiktok --group-id feishu_group_001 --input mrbeast

# 指定日期
python3 scripts/lingtu_social_monitor.py snapshot-get \
  --platform tiktok --group-id feishu_group_001 --input mrbeast --date 2026-06-22

# 时间范围（用于周报趋势）
python3 scripts/lingtu_social_monitor.py snapshot-get \
  --platform tiktok --group-id feishu_group_001 --input mrbeast \
  --from 2026-06-16 --to 2026-06-23

# 整 group 所有达人 + 各自最新快照日期（编排层做调度时用）
python3 scripts/lingtu_social_monitor.py snapshot-get \
  --group-id feishu_group_001 --latest-only
```

### 按需检查告警事件
`alerts check` 复用日报内部的 `check_alerts(prev, curr)` 函数，对比昨日/今日快照产出告警，无需等到 digest：

```bash
# 单达人
python3 scripts/lingtu_social_monitor.py alerts check \
  --platform tiktok --group-id feishu_group_001 --input mrbeast

# 整 group 的 daily 监控达人（不传 --input）
python3 scripts/lingtu_social_monitor.py alerts check \
  --group-id feishu_group_001
```

输出 `{ group_id, platform, date, username, alerts: [...] }`；`alerts` 与 digest JSON 的 `alerts` 结构一致，包含 `new_viral / stopped_posting / high_frequency / follower_drop` 四种类型。

### 标签 / 备注 / 告警阈值
```bash
python3 scripts/lingtu_social_monitor.py tag \
  --group-id feishu_group_001 --input mrbeast --tags "top-tier,NBA"

# CSV 批量打标签：表头 input,tags；tags 内多个标签用逗号分隔
python3 scripts/lingtu_social_monitor.py batch-tag \
  --platform instagram \
  --group-id feishu_group_001 \
  --input-file ./creator-tags.csv

# 在原标签基础上追加并去重
python3 scripts/lingtu_social_monitor.py batch-tag \
  --platform instagram \
  --group-id feishu_group_001 \
  --input-file ./creator-tags.csv \
  --append

python3 scripts/lingtu_social_monitor.py remark \
  --group-id feishu_group_001 --input mrbeast --remark "主要对标账号"

# v1.0 暂存不参与判定，等编排层有产品入口再接判定逻辑
python3 scripts/lingtu_social_monitor.py alert-config \
  --group-id feishu_group_001 --input mrbeast \
  --viral-threshold 500000 --max-silent-days 14

# 查询完整 monitor 元数据
python3 scripts/lingtu_social_monitor.py monitor get \
  --group-id feishu_group_001 --input mrbeast
```

### 每日日报（昨日 vs 今日）
```bash
python3 scripts/lingtu_social_monitor.py digest --group-id feishu_group_001
python3 scripts/lingtu_social_monitor.py digest --platform tiktok --group-id feishu_group_001
python3 scripts/lingtu_social_monitor.py digest --group-id feishu_group_001 --date 2026-06-11
```

### 仅查视频 / 离线分析
```bash
python3 scripts/lingtu_social_monitor.py videos  --platform tiktok --input mrbeast --count 40
python3 scripts/lingtu_social_monitor.py videos  --platform tiktok --input mrbeast --count 5 --raw
python3 scripts/lingtu_social_monitor.py analyze --input-json ./posts.json --format text
```

### 单条素材数据 / 评论
```bash
python3 scripts/lingtu_social_monitor.py material \
  --platform tiktok \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822"

python3 scripts/lingtu_social_monitor.py material \
  --platform tiktok \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822" \
  --format text

python3 scripts/lingtu_social_monitor.py comments \
  --platform tiktok \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822"

python3 scripts/lingtu_social_monitor.py comments \
  --platform tiktok \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822" \
  --max-pages 3

python3 scripts/lingtu_social_monitor.py comments \
  --platform tiktok \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822" \
  --raw

python3 scripts/lingtu_social_monitor.py comments \
  --platform instagram \
  --video-url "https://www.instagram.com/reel/C0Example/" \
  --sort-order newest
```

`material` 用于更新单条或批量视频实时指标；批量时由编排层循环调用即可。`comments` 默认自动按 `cursor` 翻页并输出规范化评论 JSON，适合全量导出；加 `--raw` 可保留聚合后的原始字段，`--first-page` 可只拉第一页，`--max-pages` 可限制页数。Instagram 评论请求会把响应里的 cursor 原样传回下一页，不做解码或改写。

## 编排层（bot/cron）建议

1. 收到群里"如何添加监控/怎么用"等问题 → `tutorial`，把文本贴回群。
2. 用户给出 URL/`@xxx` → `add`，把 `reply_text` 贴回群。文本末尾会主动询问"是否加入每日监控"。
3. 用户消息里出现"方向：发布策略 / 方向：内容形式"等关键词时，把对应值映射到 `--focus`（`posting` / `content`），不识别则用默认 `overall`。
4. 用户回复"加入每日监控 @xxx" → `enable-daily`。
5. 每天早 8 点：枚举所有 `group_id`；对每个群 `list --daily-only` → 串行 `snapshot`（建议达人间留 0.5–1s 限速）→ `digest` → 把 `reply_text` 发到群。
6. 失败的达人在 `digest` 的"未抓取到数据"段会自动列出，不会阻塞整体出图。

## 输出报告结构

`add` / `analyze` 的报告随 `--focus` 切换：

- `overall`（默认）：账号画像、发布频率、爆款 Top3、内容方向、爆款开头、标签线索、内容结构、账号价值判断。
- `posting`：发布节奏 + 发布时段画像 + 周度发布趋势 + 时长策略 + 爆款时间窗 + 策略判断。
- `content`：内容方向 + 开头钩子分布 + 爆款开头样例 + 时长×互动 + 互动率画像 + 文案风格 + 标签线索。

`digest` 日报覆盖：

- 顶部 TL;DR：群内监控数 / 今日成功抓取数 / 新增视频总数 / 缺失数。
- 一、涨粉 Top3。
- 二、新爆款 Top5（昨日不存在的视频，按今日播放降序）。
- 三、播放量增长 Top3（同一 `videoId` 对比昨日）。
- 四、异常信号：停更（≥7 天未发布）/ 高频发布（最近 7 天 ≥3 条）。
- 五、逐账号速览：每个达人 1 行（粉丝箭头、新增条数、今日最高播放、状态标记）。
- 六、未抓取到数据（如有）。

`digest --format json` 输出结构（保持现有命名，编排层据此对接）：

| 字段 | 含义 |
|------|------|
| `summary.{monitors_total, fetched, missing, new_videos_total, with_yesterday}` | 概览统计 |
| `highlights.follower_gainers[]` | 涨粉 Top（`follower_delta` / `follower_today`） |
| `highlights.new_viral[]` | 新爆款（含 `views / likes / comments / cover_url / publish_time / video_url`） |
| `highlights.biggest_view_jumps[]` | 同一视频的播放增长 Top |
| `highlights.stalled[]` | 停更（`days_since_last_post`） |
| `highlights.surged[]` | 高频发布（`last_7_days_posts`） |
| `creators[].status` | `ok` / `stall` / `surge` |
| `alerts[]` | 同 `alerts check` 输出，见下 |
| `missing[]` | 当日未抓到数据的达人 |

`alerts[]` schema：

| 字段 | 适用类型 | 说明 |
|------|----------|------|
| `type` | 全部 | `new_viral` / `stopped_posting` / `high_frequency` / `follower_drop` |
| `severity` | 全部 | `high` / `medium` / `low` |
| `username` / `platform` / `triggered_at` | 全部 | 触发时间为 unix ms |
| `video_id / video_url / caption / views / likes / cover_url / publish_time` | `new_viral` | 昨日快照中不存在 + 今日播放越过阈值 |
| `days_since_last_post / last_post_date` | `stopped_posting` | 最新视频距今 ≥ `STALL_DAYS`（默认 7） |
| `posts_last_7_days` | `high_frequency` | 最近 7 天发布数 ≥ `SURGE_WEEK_THRESHOLD`（默认 3） |
| `follower_delta / follower_today` | `follower_drop` | 粉丝下降，按 `FOLLOWER_DROP_HIGH/MEDIUM` 分级 |

阈值常量在 `lib/config.py` 中定义：`VIRAL_VIEWS_HIGH=1_000_000` / `VIRAL_VIEWS_MEDIUM=100_000` / `FOLLOWER_DROP_HIGH=10_000` / `FOLLOWER_DROP_MEDIUM=1_000` / `STALL_DAYS=7` / `SURGE_WEEK_THRESHOLD=3`。`monitors.json` 中每条记录的 `alert_config` 字段（`viral_threshold` / `follower_drop_threshold` / `max_silent_days`）v1.0 仅落盘，**不参与计算**，等编排层产品入口成熟后再接逐人阈值判定。

## 监控元数据 schema

`monitors.json` 单条记录：

```ts
interface MonitorEntry {
  monitor_id: string;
  source: string;
  group_id: string;
  team_id: string;
  operator_id: string;
  remark: string;
  tags: string[];
  added_at: string;        // ISO UTC
  updated_at: string;
  daily_enabled: boolean;
  alert_config: {
    viral_threshold?: number;
    follower_drop_threshold?: number;
    max_silent_days?: number;
  };
  creator: {
    platform, creator_id, username, nickname, profile_url,
    signature, follower_count, following_count, aweme_count, total_favorited
  };
}
```

## 错误处理约定

- `code:-1`（uniqueId 不存在）→ 抛中文提示："未获取到该达人数据：…（uniqueId=xxx）"，原样回显给用户。
- 缺 `LINGTU_API_KEY` → 中文提示。
- 网络/HTTP 错误 → 中文提示。
- `digest` 中单个达人的 snapshot 缺失不会中断流程，会进入"未抓取到数据"段。
