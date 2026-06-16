# Lingtu AI Capabilities

Use Lingtu AI packages from this repository when the user requests media generation, TK shop data analysis, TikTok creator or competitor monitoring, single-video understanding, or TK blacklist lookup.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Package Routing

- `packages/content-create`: product images, optimized product reference images, ecommerce videos, UGC videos, viral remakes, and other Lingtu AI media-generation tasks.
- `packages/tkshop-query`: shop lists, shop daily reports, store metrics, merchant metrics, product metrics, order metrics, customer metrics, and shop operations analysis.
- `packages/tiktok-monitor`: TikTok creator links, usernames, creator or competitor monitoring, group-level monitoring lists, daily digest subscriptions, and yesterday-vs-today TikTok reports.
- `packages/video-understand`: single local videos, TikTok URLs, or YouTube URLs that need summarization, tagging, breakdown, remix planning, or a replication prompt.
- `packages/tk-blacklist`: TK blacklist lookup and batch uniqueId checks.

## Shared Rules

- Require `LINGTU_API_KEY` in the process environment.
- Send the key as request header `x-api-key`.
- Start from each package's `SKILL.md` instruction file.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer package scripts over ad hoc API calls.
- Do not write customer API keys or private business data into source files.
