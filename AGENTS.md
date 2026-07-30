# Lingtu AI Agent Instructions

Use this repository when a user asks for Lingtu AI content generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, single-video metric/comment export, video understanding, or TikTok/TikTok Shop video publishing.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Available Packages

- `packages/content-create`: media generation, product reference images, ecommerce videos, and viral remake workflows.
- `packages/tkshop-query`: TK shop list lookup, daily reports, and shop operations analysis.
- `packages/social-monitor`: TikTok/Instagram creator or competitor monitoring, account video lists, single-video material metrics, video comment export, group-level lists, daily subscriptions, and yesterday-vs-today digest reports.
- `packages/video-understand`: video understanding for local files and TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URLs — produces a natural-language replication prompt for remixing, tagging, or video breakdown.
- `packages/video-publish`: batch video publishing to TikTok Shop / TikTok creator accounts, schedule CSV generation, creator/product lookup, dry-run validation, and confirmed publishing.

## Shared Rules

- Authentication uses the `LINGTU_API_KEY` environment variable. OpenClaw injects it automatically when spawning skill subprocesses. Standalone CLI users must `export LINGTU_API_KEY=xxx`.
- When the user doesn't have an API key, generate a `/binduser` URL with `python3 shared/scripts/user_keys.py single bind`.
- When presenting a `/binduser` URL to the user, output the full URL exactly as generated — never shorten, truncate, elide, or reflow it. If the messaging platform compresses long URLs, print the URL in a separate line with no surrounding text so the link stays intact.
- The key is sent as the `x-api-key` header. Do not store API keys in this repository.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer the package scripts over ad hoc API calls.

## Routing

Use `packages/content-create` for product images, image references, ecommerce videos, viral remakes, and media-generation tasks.

Use `packages/tkshop-query` for shop lists, daily reports, merchant/store metrics, and business-operation questions.

Use `packages/social-monitor` for TikTok/Instagram creator links, usernames, 达人/竞品监控, group-level monitoring lists, daily digest subscriptions, yesterday-vs-today content reports, single-video metric refreshes, and video comment exports. Phrases such as "导出视频评论", "下载评论", "获取这条 TikTok/Instagram 的评论", "评论区反馈", "更新这批视频实时数据", or "获取 TikTok/Instagram 素材数据" should route here.

Use `packages/video-understand` when the user asks to analyze, summarize, tag, break down, or 二创 a single video — local file, uploaded material, or TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URL — and wants a replication prompt or content readout.

Use `packages/video-publish` when the user asks to publish videos, batch publish TikTok/TikTok Shop videos, create a publishing schedule table, look up authorized publishing creators, search products for publishing, preview/dry-run a schedule, or confirm a video publishing batch.
