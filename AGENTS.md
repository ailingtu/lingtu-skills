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

- Single-user mode is the default and requires a configured administrator binding, created with `python3 shared/scripts/user_keys.py single bind`. When no channel or user id is provided, generate and reuse a stable local user id with platform `LOCAL`. Do not use `LINGTU_API_KEY` for business scripts.
- Do not change auth mode to satisfy a business request. If current mode is `multi`, business scripts must use multi-user authentication with `--channel feishu|wechat --user-id <external-user-id>`; if the user is unbound, return the `/binduser` link and ask them to bind.
- Switching to multi-user mode clears local single-user key state where possible: the current process environment, the configured single-user administrator's local key, legacy top-level local config key fields, and macOS `launchctl` app environment.
- Only run `python3 shared/scripts/user_keys.py mode set single|multi` when the operator explicitly asks to administer the global auth mode, not during content generation, shop queries, social monitoring, video understanding, or blacklist lookups.
- Multi-user bot mode passes `--channel feishu|wechat --user-id <external-user-id>` to business scripts. Resolve keys through `shared/scripts/lingtu_auth.py`, which reads `~/.lingtu-skills/config.json` or calls `GET https://api.ailingtu.com/v1/apiKeyBind/check?externUid=<id>&platform=FEISHU|WEIXIN|LOCAL`.
- Binding token is required and session-scoped. Generate single-user administrator `/binduser` URLs with `python3 shared/scripts/user_keys.py single bind`, and multi-user bot URLs with `python3 shared/scripts/user_keys.py bind --channel <channel> --user-id <user_id>`. Each call creates a new unique session token for that user and overwrites the previous token, so old links expire. The binding-check endpoint uses only the latest token, and the token is cleared after a key is retrieved.
- When presenting a `/binduser` URL to the user, output the full URL exactly as generated — never shorten, truncate, elide, or reflow it. If the messaging platform compresses long URLs, print the URL in a separate line with no surrounding text so the link stays intact.
- Send the resolved key as `x-api-key`.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer the package scripts over ad hoc API calls.
- Do not store customer API keys in this repository.

## Auth Mode Triggers

These are administrative commands only. Run mode-switch commands only when the user's message exactly matches one of the listed Chinese phrases. Do not treat similar phrases, explanations, or business requests as permission to switch modes:

- `切换到多用户模式`: `python3 shared/scripts/user_keys.py mode set multi`
- `切换到单用户模式`: `python3 shared/scripts/user_keys.py mode set single`
- `查看认证模式` / `当前认证模式`: `python3 shared/scripts/user_keys.py mode get`

## Routing

Use `packages/content-create` for product images, image references, ecommerce videos, viral remakes, and media-generation tasks.

Use `packages/tkshop-query` for shop lists, daily reports, merchant/store metrics, and business-operation questions.

Use `packages/social-monitor` for TikTok/Instagram creator links, usernames, 达人/竞品监控, group-level monitoring lists, daily digest subscriptions, yesterday-vs-today content reports, single-video metric refreshes, and video comment exports. Phrases such as "导出视频评论", "下载评论", "获取这条 TikTok/Instagram 的评论", "评论区反馈", "更新这批视频实时数据", or "获取 TikTok/Instagram 素材数据" should route here.

Use `packages/video-understand` when the user asks to analyze, summarize, tag, break down, or 二创 a single video — local file, uploaded material, or TikTok/YouTube/Instagram URL — and wants a replication prompt or content readout.

Use `packages/tk-blacklist` when the user asks to query TK 达人黑名单 / influencer blacklist records or check whether TikTok uniqueIds are blacklisted.
