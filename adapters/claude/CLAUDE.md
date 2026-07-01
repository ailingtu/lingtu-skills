# Lingtu AI Capabilities

Use Lingtu AI packages from this repository when the user requests media generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, single-video metric/comment export, video understanding, or TK blacklist lookup.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Content Creation

Read `packages/content-create/SKILL.md` when the user asks for:

- product images
- optimized product reference images
- ecommerce or UGC-style videos
- viral product video remakes
- Lingtu AI media-generation tasks

Use `packages/content-create/scripts/lingtu_content_task.py` for API calls.

## TKShop Query

Read `packages/tkshop-query/SKILL.md` when the user asks for:

- shop lists
- shop daily reports
- store, product, merchant, order, or customer metrics
- shop operations analysis

Use `packages/tkshop-query/scripts/lingtu_shop_data.py` for deterministic API calls.

## Social Monitor

Read `packages/social-monitor/SKILL.md` when the user asks for:

- TikTok/Instagram creator or competitor monitoring
- creator recent-video lookups
- single-video material metrics
- video comment exports or downloads
- comment feedback summaries
- group-level daily digest reports

Use `packages/social-monitor/scripts/lingtu_social_monitor.py` for deterministic API calls.

## Video Understand

Read `packages/video-understand/SKILL.md` when the user asks for:

- summarizing, tagging, or breaking down a single local video
- summarizing, tagging, or breaking down a TikTok / YouTube / Instagram URL
- remix planning or replication prompts

If the user also asks for metrics or comments, fetch them first with `packages/social-monitor`.

## TK Blacklist

Read `packages/tk-blacklist/SKILL.md` when the user asks for:

- TK 达人黑名单查询
- checking whether TikTok uniqueIds are blacklisted
- influencer risk-control lookup by uniqueId

Use `packages/tk-blacklist/scripts/lingtu_tk_blacklist.py` for deterministic API calls.

## Authentication (single-user mode)

Before first use, run `python3 shared/scripts/user_keys.py single bind` to bind the administrator key. Scripts resolve the API key automatically and send it as the `x-api-key` header. Do not set `LINGTU_API_KEY` in the environment. Never write customer API keys into source files.
