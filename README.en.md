# Lingtu AI Agent Kit

[中文版](README.md)

Packages reusable Lingtu AI capabilities for different AI agents and platforms, including Codex, Claude Code, Cursor, OpenClaw, Dify, and OpenAI. Core packages are model-agnostic; adapters provide thin translation layers.

Lingtu AI website: [www.ailingtu.com](https://www.ailingtu.com).

Repository: [ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills). When users ask to update, pull the latest version from this GitHub repository.

## What's Inside

- **`packages/content-create`** — generate product images, AI video reference packs, ecommerce/UGC selling videos, and viral-remake media through Lingtu AI.
- **`packages/tkshop-query`** — query TK shop data: daily reports, shop lists, and AI-powered operations Q&A.
- **`packages/social-monitor`** — monitor TikTok/Instagram creators or competitor accounts, fetch account video lists and single-video material metrics, export video comments, and generate recent-video intelligence reports.
- **`packages/video-understand`** — turn a local video file or a TikTok/YouTube/Instagram URL into a natural-language replication prompt for remixing, tagging, or video breakdown.
- **`packages/tk-blacklist`** — batch query TK blacklist records by TikTok uniqueId.
- **`packages/report-render`** — turn structured report JSON into shareable PNG long-images (work in progress, not yet installable).

## Repository Layout

```text
packages/
  content-create/   # Image & video generation
  tkshop-query/     # TK shop data & analytics
  social-monitor/   # Social creator monitoring, material metrics, comment export
  video-understand/ # Video understanding & replication-prompt generation
  tk-blacklist/ # TK blacklist query
  report-render/    # Report JSON to shareable PNG long-image
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

Set `LINGTU_API_KEY` before using any package:

```bash
export LINGTU_API_KEY="..."
```

| Platform | Command |
|----------|---------|
| macOS (app) | `launchctl setenv LINGTU_API_KEY "..."` |
| Windows (app) | `setx LINGTU_API_KEY "..."` |

Restart the app or terminal after setting. Requests send the key as header `x-api-key`. Never commit API keys or generated business data.

## Install

```bash
git clone https://github.com/ailingtu/lingtu-skills.git
cd lingtu-skills
./install.sh                               # Auto-detect platform, then ask which packages to install
```

Or specify a target and packages explicitly:

```bash
./install.sh codex all
./install.sh codex content-create tkshop-query social-monitor video-understand tk-blacklist
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
  --group-id mock_group_001 \
  --operator-id user_001 \
  --format text
```

## Quick Start — Video Understand

```bash
cd packages/video-understand

# Parse a TikTok / YouTube / Instagram URL and stream a replication prompt
python3 scripts/lingtu_video_understand.py replicate \
  --url "https://www.tiktok.com/@user/video/1234567890"

# Parse a local video file (auto-upload + replicate)
python3 scripts/lingtu_video_understand.py replicate --file ./clip.mp4

# Upload only — returns file id and CDN url, no replication
python3 scripts/lingtu_video_understand.py upload ./clip.mp4
```

## Quick Start — TK Blacklist

```bash
cd packages/tk-blacklist

# Batch check whether creators are in the blacklist
python3 scripts/lingtu_tk_blacklist.py search vexbolts xochitlklepper --format text
```

## Delivery

- Public GitHub repository [ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills); customers `git clone` / `git pull` directly.
- Versioned GitHub Releases (`v1.0.0`) as the contract.
- Zip archive from a release tag.
- Service or Docker deployment for private implementations.

## Development

Keep core logic in `packages/`. Keep adapters thin. When an API contract changes, update `references/api.md` first, then the script and adapter notes.
