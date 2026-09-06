# Lingtu AI Agent Instructions

Use this repository when a user asks for Lingtu AI content generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, social-media comment downloads, single-video metrics, video understanding, long-video segment remaking, or TikTok/TikTok Shop video publishing.

## Distribution

- User installation and upgrades must follow https://ailingtu.com/install/skills.md.
- Do not tell users to install or update Skills with GitHub, `git clone`, `git pull`, or another skill store.
- GitHub https://github.com/ailingtu/lingtu-skills is the development source only.

## Available Packages

- `packages/content-create`: media generation, product reference images, ecommerce videos, and viral remake workflows.
- `packages/tkshop-query`: TK shop list lookup, daily reports, and shop operations analysis.
- `packages/social-monitor`: TikTok/Instagram creator or competitor monitoring, account video lists, single-video material metrics, group-level lists, daily subscriptions, and yesterday-vs-today digest reports.
- `packages/social-comments`: TikTok, Instagram, Douyin, WeChat Channels, and Xiaohongshu single-video comment download and JSON export with pagination.
- `packages/video-understand`: video understanding for local files and TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URLs — produces a natural-language replication prompt for remixing, tagging, or video breakdown.
- `packages/video-remake`: self-contained long-video transcription, semantic cuts of at most 15 seconds, muted Wan3.0 segment generation, per-segment user approval, and final merge.
- `packages/video-publish`: batch video publishing to TikTok Shop / TikTok creator accounts, schedule CSV generation, creator/product lookup, dry-run validation, and confirmed publishing.

## Shared Rules

- Installing a Skill does not require authentication. When a Lingtu task needs `LINGTU_API_KEY` and it is missing, run `python3 shared/scripts/user_keys.py single bind` from the installed Skill root and give the generated authorization URL to the user. Never ask for, display, or store their API key.
- The key is sent as the `x-api-key` header. Do not store API keys in this repository.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer the package scripts over ad hoc API calls.

## Routing

Use `packages/content-create` for product images, image references, ecommerce videos, viral remakes, and media-generation tasks.

Use `packages/tkshop-query` for shop lists, daily reports, merchant/store metrics, and business-operation questions.

Use `packages/social-monitor` for TikTok/Instagram creator links, usernames, 达人/竞品监控, group-level monitoring lists, daily digest subscriptions, yesterday-vs-today content reports, single-video metric refreshes, and TikTok/Instagram 素材数据.

Use `packages/social-comments` for “导出视频评论”, “下载评论”, “获取这条 TikTok/Instagram/抖音/视频号/小红书评论”, “抓评论区”, or “评论区反馈”. It only downloads comment data; it does not monitor accounts or query video metrics.

Use `packages/video-understand` when the user asks to analyze, summarize, tag, break down, or 二创 a single video — local file, uploaded material, or TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URL — and wants a replication prompt or content readout.

Use `packages/video-remake` when the user provides a long local video and wants timestamped transcription, semantic splitting into clips no longer than 15 seconds, muted Wan3.0 regeneration, explicit approval of every generated segment, and final concatenation. This package does not call other Skills.

Use `packages/video-publish` when the user asks to publish videos, batch publish TikTok/TikTok Shop videos, create a publishing schedule table, look up authorized publishing creators, search products for publishing, preview/dry-run a schedule, or confirm a video publishing batch.
