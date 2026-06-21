# Lingtu AI Agent Instructions

Use this repository when a user asks for Lingtu AI content generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, single-video metric/comment export, video understanding, or TK blacklist lookup.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Available Packages

- `packages/content-create`: media generation, product reference images, ecommerce videos, and viral remake workflows.
- `packages/tkshop-query`: TK shop list lookup, daily reports, and shop operations analysis.
- `packages/social-monitor`: TikTok/Instagram creator or competitor monitoring, account video lists, single-video material metrics, video comment export, group-level lists, daily subscriptions, and yesterday-vs-today digest reports.
- `packages/video-understand`: video understanding for local files and TikTok/YouTube/Instagram URLs — produces a natural-language replication prompt for remixing, tagging, or video breakdown.
- `packages/tk-blacklist`: TK blacklist lookup by TikTok uniqueId.

## Shared Rules

- Require `LINGTU_API_KEY` in the process environment.
- Send the key as `x-api-key`.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer the package scripts over ad hoc API calls.
- Do not store customer API keys in this repository.

## Routing

Use `packages/content-create` for product images, image references, ecommerce videos, viral remakes, and media-generation tasks.

Use `packages/tkshop-query` for shop lists, daily reports, merchant/store metrics, and business-operation questions.

Use `packages/social-monitor` for TikTok/Instagram creator links, usernames, 达人/竞品监控, group-level monitoring lists, daily digest subscriptions, yesterday-vs-today content reports, single-video metric refreshes, and video comment exports. Phrases such as "导出视频评论", "下载评论", "获取这条 TikTok/Instagram 的评论", "评论区反馈", "更新这批视频实时数据", or "获取 TikTok/Instagram 素材数据" should route here.

Use `packages/video-understand` when the user asks to analyze, summarize, tag, break down, or 二创 a single video — local file, uploaded material, or TikTok/YouTube/Instagram URL — and wants a replication prompt or content readout.

Use `packages/tk-blacklist` when the user asks to query TK 达人黑名单 / influencer blacklist records or check whether TikTok uniqueIds are blacklisted.
