# Lingtu AI Capabilities

Use Lingtu AI packages from this repository when the user requests media generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, single-video metric/comment export, single-video understanding, or TK blacklist lookup.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Package Routing

- `packages/content-create`: product images, optimized product reference images, ecommerce videos, UGC videos, viral remakes, and other Lingtu AI media-generation tasks.
- `packages/tkshop-query`: shop lists, shop daily reports, store metrics, merchant metrics, product metrics, order metrics, customer metrics, and shop operations analysis.
- `packages/social-monitor`: TikTok/Instagram creator links, usernames, creator or competitor monitoring, account video lists, single-video material metrics, video comment exports/downloads, group-level monitoring lists, daily digest subscriptions, and yesterday-vs-today reports.
- `packages/video-understand`: single local videos, TikTok URLs, or YouTube URLs that need summarization, tagging, breakdown, remix planning, or a replication prompt.
- `packages/tk-blacklist`: TK blacklist lookup and batch uniqueId checks.

## Authentication (single-user mode)

- Before first use, run `python3 shared/scripts/user_keys.py single bind` to bind the administrator key.
- Scripts resolve the API key automatically and send it as the `x-api-key` header.
- Do not set `LINGTU_API_KEY` in the environment — prefer the package scripts which handle auth internally.

## Shared Rules

- Start from each package's `SKILL.md` instruction file.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer package scripts over ad hoc API calls.
- Do not write customer API keys or private business data into source files.
