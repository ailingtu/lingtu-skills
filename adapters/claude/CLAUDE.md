# Lingtu AI Capabilities

Use Lingtu AI packages from this repository when the user requests media generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, single-video metric/comment export, video understanding, TikTok/TikTok Shop video publishing, or TK blacklist lookup.

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
- summarizing, tagging, or breaking down a TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram URL
- remix planning or replication prompts

If the user also asks for metrics or comments, fetch them first with `packages/social-monitor`.

## Video Publish

Read `packages/video-publish/SKILL.md` when the user asks for:

- batch publishing TikTok / TikTok Shop videos
- generating a publishing schedule CSV/Excel
- looking up authorized publishing creators or products
- dry-run / preview of a schedule, or confirming a publish batch

Use `packages/video-publish/scripts/lingtu_video_publish.py` for deterministic API calls.

## TK Blacklist

Read `packages/tk-blacklist/SKILL.md` when the user asks for:

- TK 达人黑名单查询
- checking whether TikTok uniqueIds are blacklisted
- influencer risk-control lookup by uniqueId

Use `packages/tk-blacklist/scripts/lingtu_tk_blacklist.py` for deterministic API calls.

## Authentication

Authentication uses the `LINGTU_API_KEY` environment variable. Standalone CLI users must `export LINGTU_API_KEY=xxx`. If the user doesn't have a key yet, run `python3 shared/scripts/user_keys.py single bind` to generate a `/binduser` URL. Scripts send the key as the `x-api-key` header. Never write API keys into source files.
