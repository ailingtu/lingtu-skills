# 灵途 AI 能力套件

[English Version](README.en.md)

将灵途 AI 的能力封装为可复用的技能包，适配 Codex、Claude Code、Cursor、OpenClaw、Dify、OpenAI 等不同智能体和平台。核心包与模型无关，适配器仅做薄层翻译。

灵途 AI 官网：[www.ailingtu.com](https://www.ailingtu.com)。

仓库地址：[ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills)。需要更新时，从该 GitHub 仓库拉取最新版本。

## 简介

将灵途 AI 的能力封装为可复用的技能包，适配以下平台：

| 适配器 | 目标 |
|--------|------|
| Codex | 安装为 Codex Skills |
| Claude Code | 注入 CLAUDE.md |
| Cursor | 注入 AGENTS.md |
| OpenClaw | 注入 AGENTS.md |
| Dify | 导出工作流配置 |
| OpenAI | 导出 GPT 提示词 |

## 包含哪些能力

- **`packages/content-create`** — 生成商品图、AI 视频参考图、电商卖货视频、爆款复刻视频等。
- **`packages/tkshop-query`** — 查询 TK 店铺数据：日报、店铺列表、AI 经营问答。
- **`packages/social-monitor`** — TikTok / Instagram 达人竞品监控、账号视频列表、单条视频素材数据和近期视频情报报告。
- **`packages/social-comments`** — 下载和导出 TikTok、Instagram、抖音、视频号及小红书单条视频评论，支持自动分页和 JSON 保存。
- **`packages/video-understand`** — 视频理解与内容分析：将本地视频或 TikTok/抖音/小红书/视频号/YouTube/Instagram 链接解析为自然语言的复刻提示词，可用于二创、打标、爆款复刻和视频拆解。
- **`packages/video-publish`** — TikTok Shop / TikTok 普通视频批量发布、CSV 排期生成、达人/商品查询和 dry-run 校验。

## 目录结构 

```text
packages/
  content-create/   # 图片与视频生成
  tkshop-query/     # TK 店铺数据查询
  social-monitor/   # 社媒达人/竞品监控、素材数据
  social-comments/  # 社交媒体视频评论下载
  video-understand/ # 视频理解与复刻提示词生成
  video-publish/    # 批量视频发布和排期
adapters/
  codex/            # Codex 技能安装
  claude/           # Claude Code 适配
  cursor/           # Cursor 适配
  openclaw/         # OpenClaw 适配
  dify/             # Dify 工作流导出
  openai/           # OpenAI GPT 适配
install.sh          # 一键安装脚本
```

## 环境准备

认证只使用 `LINGTU_API_KEY` 环境变量。请在自己的电脑上执行对应命令，不要把真实 Key 发到聊天中。

macOS 当前终端：

```bash
export LINGTU_API_KEY='your-api-key'
```

macOS 永久配置：把同一行加入 `~/.zshrc`，然后执行 `source ~/.zshrc`。

Windows PowerShell 当前窗口：

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

Windows 永久配置：

```powershell
[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")
```

执行后重新打开终端。

如果用户需要绑定 TikTok Shop 店铺，或店铺/店铺商品列表为空，让用户打开以下链接完成店铺绑定/授权后再继续：

https://app.ailingtu.com/teamshop

如果发布视频时没有已授权达人，或达人未找到/未授权，让用户打开以下链接完成达人授权后再继续：

https://app.ailingtu.com/video-post

## 安装

```bash
git clone https://github.com/ailingtu/lingtu-skills.git
cd lingtu-skills
./install.sh                               # 自动识别平台，然后引导选择要安装的能力
```

也可手动指定目标平台和能力包：

```bash
./install.sh codex all
./install.sh codex content-create tkshop-query social-monitor social-comments video-understand video-publish
./install.sh claude /path/to/project content-create
./install.sh cursor /path/to/project all
./install.sh openclaw /path/to/project all
./install.sh openai /path/to/export/dir tkshop-query
./install.sh dify /path/to/export/dir all
```

不指定能力包时，安装脚本会显示选择引导。客户可以输入 `all`、能力包名称，或输入 `1,2` 这样的编号多选。

### 分别上传到 SkillHub

为每项能力生成一个自包含目录和一个 ZIP：

```bash
python3 scripts/build_skillhub_packages.py
```

产物位于 `dist/skillhub/`。每个 ZIP 解压后的根目录直接包含
`SKILL.md`，可分别上传；不要把整个仓库作为一个 Skill 上传。详细结构和检查方式见
[`docs/skillhub-packaging.md`](docs/skillhub-packaging.md)。

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

- **公开仓库**：GitHub 公开仓库 [ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills)，客户直接 `git clone` / `git pull` 拉取。
- **版本发布**：以版本号（如 `v1.0.0`）为交付契约，客户可回滚。
- **Zip 包**：从 Release Tag 导出压缩包分发。
- **服务部署**：需要隐藏实现细节时，以服务或 Docker 方式交付。

## 开发说明

- 核心逻辑放在 `packages/` 中，适配器保持轻量。
- API 变更时，先更新对应包的 `references/api.md`，再更新脚本和适配器。
- 不要向客户暴露 API 密钥。
