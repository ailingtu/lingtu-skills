# Lingtu AI Agent Kit

[中文版](README.md)

Packages reusable Lingtu AI capabilities for different AI agents and platforms, including Codex, Claude Code, Cursor, OpenClaw, Dify, and OpenAI. Core packages are model-agnostic; adapters provide thin translation layers.

Lingtu AI website: [www.ailingtu.com](https://www.ailingtu.com).

Repository: [ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills). When users ask to update, pull the latest version from this GitHub repository.

## What's Inside

- **`packages/content-create`** — generate product images, AI video reference packs, ecommerce/UGC selling videos, and viral-remake media through Lingtu AI.
- **`packages/tkshop-query`** — query TK shop data: daily reports, shop lists, and AI-powered operations Q&A.
- **`packages/social-monitor`** — monitor TikTok/Instagram creators or competitor accounts, fetch account video lists and single-video material metrics, export video comments, and generate recent-video intelligence reports.
- **`packages/video-understand`** — turn a local video file or a TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URL into a natural-language replication prompt for remixing, tagging, viral remake, or video breakdown.
- **`packages/video-publish`** — batch TikTok / TikTok Shop video publishing, schedule CSV generation, creator/product lookup, and dry-run validation.

## Repository Layout

```text
packages/
  content-create/   # Image & video generation
  tkshop-query/     # TK shop data & analytics
  social-monitor/   # Social creator monitoring, material metrics, comment export
  video-understand/ # Video understanding & replication-prompt generation
  video-publish/    # Batch video publishing and schedules
adapters/
  codex/            # Codex skill installation
  claude/           # Claude Code CLAUDE.md
  cursor/           # Cursor AGENTS.md
  openclaw/         # OpenClaw AGENTS.md
  dify/             # Dify workflow export
  openai/           # OpenAI custom GPT prompt
install.sh          # One-command installer
```

## Prerequisites

Authentication uses the `LINGTU_API_KEY` environment variable. OpenClaw injects it automatically. For standalone CLI use:

```bash
export LINGTU_API_KEY=xxx
```

If you don't have an API key yet, generate a `/binduser` URL:

```bash
python3 shared/scripts/user_keys.py single bind
```

Open the returned link, complete the binding on the website, then set `LINGTU_API_KEY`. Requests send the key as the `x-api-key` header. Never commit API keys or business data.

To bind a TikTok Shop, or when the shop / shop-product list is empty, ask the user to open this link and finish shop authorization before retrying:

https://app.ailingtu.com/teamshop

When video publishing has no authorized creators, or a creator is missing / unauthorized, ask the user to open this link and finish creator authorization before retrying:

https://app.ailingtu.com/video-post

## Install

```bash
git clone https://github.com/ailingtu/lingtu-skills.git
cd lingtu-skills
./install.sh                               # Auto-detect platform, then ask which packages to install
```

Or specify a target and packages explicitly:

```bash
./install.sh codex all
./install.sh codex content-create tkshop-query social-monitor video-understand video-publish
./install.sh claude /path/to/project content-create
./install.sh cursor /path/to/project all
./install.sh openclaw /path/to/project all
./install.sh openai /path/to/export/dir tkshop-query
./install.sh dify /path/to/export/dir all
```

When no package is specified, the installer shows a selection guide. Customers can enter `all`, a package name, or package numbers such as `1,2`.

## Quick Start — Content Create

```bash
cd packages/content-create

# Generate product images
python3 scripts/lingtu_content_task.py \
  --kind image \
  --prompt "A clean product hero image on white background" \
  --model gpt-image-2 \
  --aspect-ratio 1:1 \
  --nums 3 \
  --reference-image /path/to/product.png

# Generate ecommerce video
python3 scripts/lingtu_content_task.py \
  --kind video \
  --prompt "A clean product reveal video" \
  --model gemini-omni-video \
  --seconds 10 \
  --size 720x1280 \
  --reference-image /path/to/ref-1.png \
  --reference-image /path/to/ref-2.png
```

## Quick Start — TKShop Query

```bash
cd packages/tkshop-query

# List all shops
python3 scripts/lingtu_shop_data.py list-shops

# Get daily report
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09

# Get a specific shop's report
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09 --shop-name "Your Shop"

# Ask an AI operations question
python3 scripts/lingtu_shop_data.py ask "What issues have there been in recent shop operations?"
```

## Quick Start — Social Monitor

```bash
cd packages/social-monitor

# Add a creator or competitor account and generate a 40-video report
python3 scripts/lingtu_social_monitor.py add \
  --platform tiktok \
  --input "https://www.tiktok.com/@example" \
  --remark "Competitor account, fitness products" \
  --source feishu_group \
  --group-id local_default \
  --operator-id user_001 \
  --format text
```

`group_id` is an isolation key: use a Feishu group id in Feishu, or a stable local id such as `local_default` for Cursor / Codex / CLI.

## Quick Start — Video Understand

```bash
cd packages/video-understand

# Parse a TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram URL and stream a replication prompt
python3 scripts/lingtu_video_understand.py replicate \
  --url "https://www.tiktok.com/@user/video/1234567890"
# Douyin / Xiaohongshu / WeChat Channels examples:
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://www.douyin.com/video/7123456789012345678"
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://www.xiaohongshu.com/explore/64abcdef0123456789abcdef"
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://channels.weixin.qq.com/web/pages/feed?eid=..."

# Parse a local video file (auto-upload + replicate)
python3 scripts/lingtu_video_understand.py replicate --file ./clip.mp4

# Upload only — returns file id and CDN url, no replication
python3 scripts/lingtu_video_understand.py upload ./clip.mp4
```

## Quick Start — Video Publish

```bash
cd packages/video-publish

# Generate a CSV schedule template
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok_shop \
  --region US \
  --date 2026-07-05 \
  --product-id pid_001234

# Dry-run preview (after editing schedule.csv and adding videos)
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/video_publish_2026-07-05

# Confirm publish
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/video_publish_2026-07-05 \
  --confirm
```

## Delivery

- Public GitHub repository [ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills); customers `git clone` / `git pull` directly.
- Versioned GitHub Releases (`v1.0.0`) as the contract.
- Zip archive from a release tag.
- Service or Docker deployment for private implementations.

## Development

Keep core logic in `packages/`. Keep adapters thin. When an API contract changes, update `references/api.md` first, then the script and adapter notes.
