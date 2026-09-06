# Lingtu AI Capabilities

Use Lingtu AI packages from this repository when the user requests media generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, social-media comment downloads, single-video metrics, single-video understanding, or TikTok/TikTok Shop video publishing.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Package Routing

- `packages/content-create`: product images, optimized product reference images, ecommerce videos, UGC videos, viral remakes, and other Lingtu AI media-generation tasks.
- `packages/tkshop-query`: shop lists, shop daily reports, store metrics, merchant metrics, product metrics, order metrics, customer metrics, and shop operations analysis.
- `packages/social-monitor`: TikTok/Instagram creator links, usernames, creator or competitor monitoring, account video lists, single-video material metrics, group-level monitoring lists, daily digest subscriptions, and yesterday-vs-today reports.
- `packages/social-comments`: TikTok, Instagram, Douyin, WeChat Channels, and Xiaohongshu single-video comment download and JSON export.
- `packages/video-understand`: single local videos, TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram URLs that need summarization, tagging, breakdown, remix planning, viral remake, or a replication prompt.
- `packages/video-publish`: batch TikTok / TikTok Shop video publishing, schedule CSV generation, authorized creator/product lookup, dry-run preview, and confirmed publishing.

## Authentication

- If `LINGTU_API_KEY` is missing, directly give the user the matching local command: macOS `export LINGTU_API_KEY='your-api-key'`; Windows PowerShell `$env:LINGTU_API_KEY = "your-api-key"`. For persistent configuration, macOS users add the export to `~/.zshrc`; Windows users run `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")` and open a new terminal. Never ask users to paste the real key into chat.
- Scripts read `LINGTU_API_KEY` from the environment and send it as the `x-api-key` header.

## Shared Rules

- Start from each package's `SKILL.md` instruction file.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer package scripts over ad hoc API calls.
- Do not write customer API keys or private business data into source files.
