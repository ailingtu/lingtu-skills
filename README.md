# 灵途 AI 能力套件

[English Version](README.en.md)

将灵途 AI 的能力封装为可独立安装的技能包。每项能力分别发布、分别安装，Skill 本身保持模型无关。

灵途 AI 官网：[www.ailingtu.com](https://www.ailingtu.com)。

源码仓库：[ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills)，仅用于开发和发布。用户安装与升级统一使用[灵途 Skills 官方安装文档](https://ailingtu.com/install/skills.md)，不要从 GitHub 安装。

## 包含哪些能力

- **`packages/content-create`** — 生成商品图、AI 视频参考图、电商卖货视频、爆款复刻视频等。
- **`packages/tkshop-query`** — 查询 TK 店铺数据：日报、店铺列表、AI 经营问答。
- **`packages/social-monitor`** — TikTok / Instagram 达人竞品监控、账号视频列表、单条视频素材数据和近期视频情报报告。
- **`packages/social-comments`** — 下载和导出 TikTok、Instagram、抖音、视频号及小红书单条视频评论，支持自动分页和 JSON 保存。
- **`packages/video-understand`** — 视频理解与内容分析：将本地视频或 TikTok/抖音/小红书/视频号/YouTube/Instagram 链接解析为自然语言的复刻提示词，可用于二创、打标、爆款复刻和视频拆解。
- **`packages/video-remake`** — 长视频转写、按语义切成15秒内无声片段、Wan3.0逐段重绘、逐段确认并合成最终视频；完全独立运行。
- **`packages/video-publish`** — TikTok Shop / TikTok 普通视频批量发布、CSV 排期生成、达人/商品查询和 dry-run 校验。

## 目录结构 

```text
packages/
  content-create/   # 图片与视频生成
  tkshop-query/     # TK 店铺数据查询
  social-monitor/   # 社媒达人/竞品监控、素材数据
  social-comments/  # 社交媒体视频评论下载
  video-understand/ # 视频理解与复刻提示词生成
  video-remake/     # 长视频分段重绘、确认与合成
  video-publish/    # 批量视频发布和排期
shared/scripts/     # 构建时复制进每个 Skill 的公共运行时
scripts/            # 单 Skill 构建工具
docs/               # CDN 单包发布说明
```

## 账号绑定

安装 Skill 不要求预先提供密钥。首次执行灵途任务且缺少 `LINGTU_API_KEY` 时，
Agent 会从已安装 Skill 根目录运行：

```bash
python3 shared/scripts/user_keys.py single bind
```

请打开生成的授权链接完成绑定。不要在聊天中发送、展示或保存 API Key。

如果用户需要绑定 TikTok Shop 店铺，或店铺/店铺商品列表为空，让用户打开以下链接完成店铺绑定/授权后再继续：

https://app.ailingtu.com/teamshop

如果发布视频时没有已授权达人，或达人未找到/未授权，让用户打开以下链接完成达人授权后再继续：

https://app.ailingtu.com/video-post

## 安装与升级

把下面这句话发给 Agent 即可：

> 根据 [https://ailingtu.com/install/skills.md](https://ailingtu.com/install/skills.md) 安装灵途 Skills。

Agent 会实时读取灵途官方索引，根据任务选择所需 Skill，并从灵途 TOS/CDN
逐个下载、校验和安装。升级也使用同一文档；不要通过 GitHub 或其他技能商店安装。

## 分别发布到灵途 CDN

为每项能力生成一个自包含目录和一个 ZIP：

```bash
python3 scripts/build_package.py content-create
```

产物位于 `dist/packages/`。每个 ZIP 解压后的根目录直接包含
`SKILL.md`，可分别上传；不要把整个仓库作为一个 Skill 上传。详细结构和检查方式见
[`docs/distribution-packaging.md`](docs/distribution-packaging.md)。

## 快速开始

### 内容生成（Content Create）

```bash
cd packages/content-create

# 生成商品图
python3 scripts/lingtu_content_task.py \
  --kind image \
  --prompt "一张白色背景的产品主图" \
  --model gpt-image-2 \
  --aspect-ratio 1:1 \
  --nums 3 \
  --reference-image /path/to/product.png

# 生成电商视频
python3 scripts/lingtu_content_task.py \
  --kind video \
  --prompt "一个简洁的产品展示视频" \
  --model gemini-omni-video \
  --seconds 10 \
  --size 720x1280 \
  --reference-image /path/to/ref-1.png \
  --reference-image /path/to/ref-2.png
```

### 店铺查询（TKShop Query）

```bash
cd packages/tkshop-query

# 查看店铺列表
python3 scripts/lingtu_shop_data.py list-shops

# 获取默认店铺日报
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09

# 获取指定店铺日报
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09 --shop-name "店铺名称"

# 向 AI 提问经营问题
python3 scripts/lingtu_shop_data.py ask "店铺最近经营有什么问题？"
```

### 社媒达人/竞品监控（Social Monitor）

```bash
cd packages/social-monitor

# 添加达人/竞品账号，并生成最近 40 条视频分析
python3 scripts/lingtu_social_monitor.py add \
  --platform tiktok \
  --input "https://www.tiktok.com/@example" \
  --remark "竞品账号，主卖健身产品" \
  --source feishu_group \
  --group-id local_default \
  --operator-id user_001 \
  --format text
```

`group_id` 是隔离键：飞书可用群 ID；本地 / Cursor / Codex 可用 `local_default` 等稳定标识。

### 社交媒体评论下载（Social Comments）

```bash
cd packages/social-comments

python3 scripts/lingtu_social_comments.py download \
  --video-url "https://www.tiktok.com/@user/video/1234567890" \
  --output ./comments.json
```

### 视频理解（Video Understand）

```bash
cd packages/video-understand

# 解析 TikTok / 抖音 / 小红书 / 视频号 / YouTube / Instagram 链接，流式返回复刻提示词
python3 scripts/lingtu_video_understand.py replicate \
  --url "https://www.tiktok.com/@user/video/1234567890"
# 抖音 / 小红书 / 视频号示例：
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://www.douyin.com/video/7123456789012345678"
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://www.xiaohongshu.com/explore/64abcdef0123456789abcdef"
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://channels.weixin.qq.com/web/pages/feed?eid=..."

# 解析本地视频文件（自动上传后再复刻）
python3 scripts/lingtu_video_understand.py replicate --file ./clip.mp4

# 仅上传文件，返回文件 id 和 CDN 地址
python3 scripts/lingtu_video_understand.py upload ./clip.mp4
```

### 长视频分段复刻（Video Remake）

```bash
cd packages/video-remake

# 导入带时间戳字幕，完成语义切片和消音
python3 scripts/lingtu_video_remake.py prepare ./source.mp4 \
  --transcript ./source.srt \
  --job-dir ./remake-job

# 每次只生成一段，用户确认后再生成下一段
python3 scripts/lingtu_video_remake.py generate --job-dir ./remake-job
python3 scripts/lingtu_video_remake.py approve \
  --job-dir ./remake-job --segment segment-001

# 所有片段确认后合成
python3 scripts/lingtu_video_remake.py merge \
  --job-dir ./remake-job --output ./final-remake.mp4
```

### 批量视频发布（Video Publish）

```bash
cd packages/video-publish

# 生成 CSV 排期模板
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok_shop \
  --region US \
  --date 2026-07-05 \
  --product-id pid_001234

# dry-run 预览（编辑 schedule.csv 并放入视频后）
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05

# 确认发布
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05 \
  --confirm
```

## 交付方式

- **灵途 TOS/CDN**：每个 `packages/*` 分别构建、发布和安装。
- **安装入口**：<https://ailingtu.com/install/skills.md>。
- **版本发布**：版本号维护在各自 `SKILL.md` 的 frontmatter 中。
- **GitHub**：公开仓库保留源码、测试和发布工具。

## 开发说明

- 核心逻辑放在 `packages/` 中；不要恢复跨平台适配器或批量安装层。
- API 变更时，先更新对应包的 `references/api.md`，再更新脚本。
- 每个发布物必须自包含，不得依赖安装目录外的文件。
- 不要向客户暴露 API 密钥。
