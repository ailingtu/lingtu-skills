# Lingtu AI Capabilities

This project includes Lingtu AI agent packages.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Use `packages/content-create`

Use for generated product images, reference images, ecommerce videos, viral remakes, visual content, and Lingtu AI media tasks. Start with `packages/content-create/SKILL.md`.

## Use `packages/tkshop-query`

Use for shop list lookup, daily reports, merchant/store metrics, and business-operation questions. Start with `packages/tkshop-query/SKILL.md`.

## Use `packages/social-monitor`

Use for TikTok/Instagram creator links, usernames, creator/competitor monitoring, account video lists, single-video material metrics, group-level monitoring lists, daily digest subscriptions, and yesterday-vs-today reports. Start with `packages/social-monitor/SKILL.md`.

## Use `packages/social-comments`

Use for downloading or exporting comments from one TikTok, Instagram, Douyin, WeChat Channels, or Xiaohongshu video, or obtaining comment data for feedback summaries. Start with `packages/social-comments/SKILL.md`.

## Use `packages/video-understand`

Use for single local videos, or TikTok / Douyin (抖音) / Xiaohongshu (小红书) / WeChat Channels (视频号) / YouTube / Instagram URLs that need summarization, tagging, breakdown, remix planning, viral remake, or a replication prompt. Fetch TikTok/Instagram metrics with `packages/social-monitor`; fetch supported-platform comments with `packages/social-comments`.

## Use `packages/video-publish`

Use for batch publishing TikTok / TikTok Shop videos, generating a publishing schedule CSV/Excel, looking up authorized publishing creators or products, dry-run / preview of a schedule, or confirming a publish batch. Start with `packages/video-publish/SKILL.md`.

## Authentication

If the API key is missing, give the user the matching command and ask them to run it locally. Never ask them to paste the real key into chat.

macOS:

```bash
export LINGTU_API_KEY='your-api-key'
```

Windows PowerShell:

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

Scripts read `LINGTU_API_KEY` from the environment and send it as the `x-api-key` header.
