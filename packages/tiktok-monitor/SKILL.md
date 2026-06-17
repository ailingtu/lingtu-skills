---
name: lingtu-tiktok-monitor
version: 0.5.0
description: TikTok 达人/竞品监控、单条素材数据与评论抓取/导出/下载、日报。通过灵途 `/v1/influencer/fetchPosts`、`/v1/material/tiktok/fetch`、`/v1/material/tiktok/fetchComments` 接口监控 TikTok 达人或对标账号，支持导出视频评论、下载评论、获取评论区反馈、更新单条或批量视频实时数据、加入群级监控列表、即时分析（综合/发布策略/内容形式 三种分析方向）、每日订阅，并按"昨日 vs 今日"差异生成中文日报。
---

# TikTok 达人 / 竞品监控与日报

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## 适用场景

当用户要求监控 TikTok 达人 / 竞品 / 对标账号、查看群里的监控列表、订阅每日内容情报日报、导出/下载/获取某条 TikTok 视频评论、总结评论区反馈、更新一批视频实时数据、或基于已抓取的视频数据出报告时，调用本技能。每个群（`group_id`）的监控列表互相独立。

如果用户要"分析某个视频内容/讲了什么/复刻/二创"，优先使用 `lingtu-video-understand`；若问题同时要求结合播放、点赞、评论或评论区反馈，先用本技能的 `material` / `comments` 获取数据，再把结果作为分析上下文交给视频理解流程。

## 使用流程

```text
用户在群里 @机器人 ──▶
  ├─ "如何添加监控" / "怎么用" ── tutorial
  ├─ "添加监控 <链接|@用户名>" ── add（即时分析 + 落今日快照）
  ├─ 答复"加入每日监控 @xxx" ── enable-daily（订阅）
  ├─ "查看监控列表" / "看一下都监控了谁" ── list
  ├─ "取消每日监控 @xxx" ── disable-daily
  └─ "移除监控 @xxx" ── remove

每天早 8 点（编排层 cron 触发）─▶
  for 群: for 达人: snapshot；最后一步 digest 输出当日中文日报到群里。
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
| `LINGTU_TIKTOK_MONITOR_STORE` | 监控元数据 JSON 文件路径 | `~/.lingtu/tiktok-monitor/monitors.json` |
| `LINGTU_TIKTOK_MONITOR_SNAPSHOTS` | 每日快照根目录 | `~/.lingtu/tiktok-monitor/snapshots` |

API Key 通过请求头 `x-api-key` 发送。请勿提交密钥或私有监控数据。

API 字段、`code` 取值参见 `references/api.md`，改接口前先更新该文档。

## 子命令

所有命令默认输出文本，便于直接贴回群消息；加 `--format json` 用于编排层。`--input` 接 TikTok 主页 URL、`@username` 或裸名。

### 教程
```bash
python3 scripts/lingtu_tiktok_monitor.py tutorial
```

### 添加监控（即时分析 + 落今日快照）
```bash
python3 scripts/lingtu_tiktok_monitor.py add \
  --input "https://www.tiktok.com/@mrbeast" \
  --group-id feishu_group_001 \
  --remark "对标账号" \
  --focus overall \
  --format text
```

`--focus` 控制分析方向（默认 `overall`）：

| 值 | 含义 | 报告侧重 |
|----|------|----------|
| `overall` | 综合画像（默认） | 频率 / 爆款 / 内容方向 / 钩子 / hashtag / 价值判断 |
| `posting` | 发布策略 | 节奏 + 时段画像 + 周度趋势 + 时长策略 + 爆款时间窗 |
| `content` | 内容形式 | 钩子句式分布 + 时长×互动 + 互动率画像 + 文案风格 |

`analyze` 也接受 `--focus`，可基于已有 JSON 切换分析方向。

### 列出群内监控
```bash
python3 scripts/lingtu_tiktok_monitor.py list --group-id feishu_group_001
python3 scripts/lingtu_tiktok_monitor.py list --group-id feishu_group_001 --daily-only
```

### 开启 / 关闭每日监控
```bash
python3 scripts/lingtu_tiktok_monitor.py enable-daily  --group-id feishu_group_001 --input mrbeast
python3 scripts/lingtu_tiktok_monitor.py disable-daily --group-id feishu_group_001 --input mrbeast
```

### 移除监控
```bash
python3 scripts/lingtu_tiktok_monitor.py remove --group-id feishu_group_001 --input mrbeast
```

### 单条快照（每日 8 点编排循环调用）
```bash
python3 scripts/lingtu_tiktok_monitor.py snapshot \
  --group-id feishu_group_001 --input mrbeast --count 40
```

### 每日日报（昨日 vs 今日）
```bash
python3 scripts/lingtu_tiktok_monitor.py digest --group-id feishu_group_001
python3 scripts/lingtu_tiktok_monitor.py digest --group-id feishu_group_001 --date 2026-06-11
```

### 仅查视频 / 离线分析
```bash
python3 scripts/lingtu_tiktok_monitor.py videos  --input mrbeast --count 40
python3 scripts/lingtu_tiktok_monitor.py videos  --input mrbeast --count 5 --raw
python3 scripts/lingtu_tiktok_monitor.py analyze --input-json ./posts.json --format text
```

### 单条素材数据 / 评论
```bash
python3 scripts/lingtu_tiktok_monitor.py material \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822"

python3 scripts/lingtu_tiktok_monitor.py material \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822" \
  --format text

python3 scripts/lingtu_tiktok_monitor.py comments \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822"

python3 scripts/lingtu_tiktok_monitor.py comments \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822" \
  --max-pages 3

python3 scripts/lingtu_tiktok_monitor.py comments \
  --video-url "https://www.tiktok.com/@user/video/7624922739500993822" \
  --raw
```

`material` 用于更新单条或批量视频实时指标；批量时由编排层循环调用即可。`comments` 默认自动按 `cursor` 翻页并输出规范化评论 JSON，适合全量导出；加 `--raw` 可保留聚合后的原始字段，`--first-page` 可只拉第一页，`--max-pages` 可限制页数。

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

## 错误处理约定

- `code:-1`（uniqueId 不存在）→ 抛中文提示："未获取到该达人数据：…（uniqueId=xxx）"，原样回显给用户。
- 缺 `LINGTU_API_KEY` → 中文提示。
- 网络/HTTP 错误 → 中文提示。
- `digest` 中单个达人的 snapshot 缺失不会中断流程，会进入"未抓取到数据"段。
