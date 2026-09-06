# Lingtu AI Agent Kit

[中文版](README.md)

Packages Lingtu AI capabilities as independently installable skills. Each capability is published and installed separately while remaining model-agnostic.

Lingtu AI website: [www.ailingtu.com](https://www.ailingtu.com).

Source repository: [ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills), for development and publishing only. Users must install and upgrade through the [official Lingtu Skills installation guide](https://ailingtu.com/install/skills.md), not GitHub.

## What's Inside

- **`packages/content-create`** — generate product images, AI video reference packs, ecommerce/UGC selling videos, and viral-remake media through Lingtu AI.
- **`packages/tkshop-query`** — query TK shop data: daily reports, shop lists, and AI-powered operations Q&A.
- **`packages/social-monitor`** — monitor TikTok/Instagram creators or competitor accounts, fetch account video lists and single-video material metrics, and generate recent-video intelligence reports.
- **`packages/social-comments`** — download and export comments from one TikTok, Instagram, Douyin, WeChat Channels, or Xiaohongshu video with automatic pagination and JSON output.
- **`packages/video-understand`** — turn a local video file or a TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URL into a natural-language replication prompt for remixing, tagging, viral remake, or video breakdown.
- **`packages/video-remake`** — independently transcribe a long video, cut it into muted semantic segments of at most 15 seconds, regenerate and approve each segment with Wan3.0, then merge the approved results.
- **`packages/video-publish`** — batch TikTok / TikTok Shop video publishing, schedule CSV generation, creator/product lookup, and dry-run validation.

## Repository Layout

```text
packages/
  content-create/   # Image & video generation
  tkshop-query/     # TK shop data & analytics
  social-monitor/   # Social creator monitoring and material metrics
  social-comments/  # Social video comment downloads
  video-understand/ # Video understanding & replication-prompt generation
  video-remake/     # Long-video segment remake, review, and merge
  video-publish/    # Batch video publishing and schedules
shared/scripts/     # Common runtime copied into each built Skill
scripts/            # Single-Skill build tooling
docs/               # CDN package publishing instructions
```

## Account binding

Installing a Skill does not require a key. Before the first Lingtu task, if
`LINGTU_API_KEY` is unavailable, the agent runs this from the installed Skill root:

```bash
python3 shared/scripts/user_keys.py single bind
```

Open the generated authorization URL to complete binding. Never send, display,
or save an API key in chat.

To bind a TikTok Shop, or when the shop / shop-product list is empty, ask the user to open this link and finish shop authorization before retrying:

https://app.ailingtu.com/teamshop

When video publishing has no authorized creators, or a creator is missing / unauthorized, ask the user to open this link and finish creator authorization before retrying:

https://app.ailingtu.com/video-post

## Install and upgrade

Send this instruction to your agent:

> Install Lingtu Skills by following [https://ailingtu.com/install/skills.md](https://ailingtu.com/install/skills.md).

The agent reads the live Lingtu package index, chooses the Skill required for
the task, then downloads, verifies, and installs each package separately from
Lingtu TOS/CDN. Use the same guide for upgrades. Do not install from GitHub or
another skill store.

## Publish Skills separately to Lingtu CDN

Build one self-contained Skill at a time:

```bash
python3 scripts/build_package.py content-create
```

The output is written to `dist/packages/`. See
[`docs/distribution-packaging.md`](docs/distribution-packaging.md) for validation and
publishing instructions.

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

## Quick Start — Social Comments

```bash
cd packages/social-comments

python3 scripts/lingtu_social_comments.py download \
  --video-url "https://www.tiktok.com/@user/video/1234567890" \
  --output ./comments.json
```

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

- **Lingtu TOS/CDN:** build, publish, and install each `packages/*` Skill separately.
- **Installation entry point:** <https://ailingtu.com/install/skills.md>.
- **Versions:** maintain each version in its `SKILL.md` frontmatter.
- **GitHub:** keep source code, tests, and publishing tools in the public repository.

## Development

Keep core logic in `packages/`; do not restore cross-platform adapters or a bulk installer. When an API contract changes, update `references/api.md` before the script. Every published Skill must be self-contained.
