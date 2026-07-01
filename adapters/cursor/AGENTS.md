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

Use for single local videos, TikTok URLs, YouTube URLs, or Instagram URLs that need summarization, tagging, breakdown, remix planning, or a replication prompt. If the user also asks for metrics or comments, fetch them first with `packages/social-monitor`.

## Use `packages/tk-blacklist`

Use for TK 达人黑名单查询, TikTok influencer blacklist lookup, and batch uniqueId blacklist checks. Start with `packages/tk-blacklist/SKILL.md`.

## Authentication (single-user mode)

Before first use, run `python3 shared/scripts/user_keys.py single bind` to bind the administrator key. Scripts resolve the API key automatically and send it as the `x-api-key` header. Do not set `LINGTU_API_KEY` in the environment.
