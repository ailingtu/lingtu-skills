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

Use for TikTok/Instagram creator links, usernames, creator/competitor monitoring, account video lists, single-video material metrics, video comment exports/downloads, comment feedback summaries, group-level monitoring lists, daily digest subscriptions, and yesterday-vs-today reports. Start with `packages/social-monitor/SKILL.md`.

## Use `packages/video-understand`

Use for single local videos, or TikTok / Douyin (抖音) / Xiaohongshu (小红书) / WeChat Channels (视频号) / YouTube / Instagram URLs that need summarization, tagging, breakdown, remix planning, viral remake, or a replication prompt. If the user also asks for metrics or comments on TikTok/Instagram, fetch them first with `packages/social-monitor`.

## Use `packages/video-publish`

Use for batch publishing TikTok / TikTok Shop videos, generating a publishing schedule CSV/Excel, looking up authorized publishing creators or products, dry-run / preview of a schedule, or confirming a publish batch. Start with `packages/video-publish/SKILL.md`.

## Authentication

Set your API key before use. Run `python3 shared/scripts/user_keys.py single bind` if you need a `/binduser` URL:

```bash
export LINGTU_API_KEY=xxx
```

Scripts read `LINGTU_API_KEY` from the environment and send it as the `x-api-key` header.
