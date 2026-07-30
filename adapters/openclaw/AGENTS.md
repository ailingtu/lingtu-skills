# Lingtu AI Capabilities

Use Lingtu AI packages from this repository when the user requests media generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, single-video metric/comment export, single-video understanding, or TikTok/TikTok Shop video publishing.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Package Routing

- `packages/content-create`: product images, optimized product reference images, ecommerce videos, UGC videos, viral remakes, and other Lingtu AI media-generation tasks.
- `packages/tkshop-query`: shop lists, shop daily reports, store metrics, merchant metrics, product metrics, order metrics, customer metrics, and shop operations analysis.
- `packages/social-monitor`: TikTok/Instagram creator links, usernames, creator or competitor monitoring, account video lists, single-video material metrics, video comment exports/downloads, group-level monitoring lists, daily digest subscriptions, and yesterday-vs-today reports.
- `packages/video-understand`: single local videos, TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram URLs that need summarization, tagging, breakdown, remix planning, viral remake, or a replication prompt.
- `packages/video-publish`: batch TikTok / TikTok Shop video publishing, schedule CSV generation, authorized creator/product lookup, dry-run preview, and confirmed publishing.

## Authentication

- OpenClaw injects `LINGTU_API_KEY` automatically when spawning skill subprocesses.
- If the user hasn't bound an API key yet, run `python3 shared/scripts/user_keys.py single bind` to generate a `/binduser` URL. The user opens it in a browser, completes the binding on the website, and the key is then set via OpenClaw.
- Scripts read `LINGTU_API_KEY` from the environment and send it as the `x-api-key` header.

## Shared Rules

- Start from each package's `SKILL.md` instruction file.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer package scripts over ad hoc API calls.
- Do not write customer API keys or private business data into source files.
