# Lingtu AI Capabilities

This project includes Lingtu AI agent packages.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Use `packages/content-create`

Use for generated product images, reference images, ecommerce videos, viral remakes, visual content, and Lingtu AI media tasks. Start with `packages/content-create/SKILL.md`.

## Use `packages/tkshop-query`

Use for shop list lookup, daily reports, merchant/store metrics, and business-operation questions. Start with `packages/tkshop-query/SKILL.md`.

## Use `packages/tiktok-monitor`

Use for TikTok creator links, usernames, creator/competitor monitoring, single-video material metrics, video comment exports/downloads, comment feedback summaries, group-level monitoring lists, daily digest subscriptions, and yesterday-vs-today TikTok reports. Start with `packages/tiktok-monitor/SKILL.md`.

## Use `packages/video-understand`

Use for single local videos, TikTok URLs, or YouTube URLs that need summarization, tagging, breakdown, remix planning, or a replication prompt. If the user also asks for metrics or comments, fetch them first with `packages/tiktok-monitor`.

## Use `packages/tk-blacklist`

Use for TK 达人黑名单查询, TikTok influencer blacklist lookup, and batch uniqueId blacklist checks. Start with `packages/tk-blacklist/SKILL.md`.

## Environment

Set `LINGTU_API_KEY` before running scripts. Send it as `x-api-key`.
