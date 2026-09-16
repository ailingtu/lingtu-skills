# Lingtu AI Agent Instructions

Use this repository when a user asks for Lingtu AI OpenAPI developer integration, content generation, TK shop data analysis, TikTok/Instagram creator or competitor monitoring, social-media comment downloads, single-video metrics, video understanding, long-video segment remaking, or TikTok/TikTok Shop video publishing.

## Distribution

- Every Skill must expose the shared Lingtu Skills update intent in its description and a self-contained update workflow. Requests to update Lingtu Skills update only installed packages for the current Agent, require no business API key, and preserve backups outside scanned Skills directories. The scaffold carries this contract for new packages.

- User installation and upgrades must follow https://ailingtu.com/install/skills.md.
- Do not tell users to install or update Skills with Codeup, GitHub, `git clone`, `git pull`, or another skill store.
- Codeup https://codeup.aliyun.com/coss/ailingtu/skills is the development source only.
- Before updating or adding a package in the official SkillHub, read `docs/skillhub-release.md` completely. Normal releases must build and publish exactly one package with `--package`; never use an implicit full-directory publish for a single-Skill change.

## Available Packages

- `packages/openapi-guide`: public OpenAPI documentation lookup, API Key creation and safe-use guidance, integration code generation/review, and sanitized error diagnosis without making authenticated business API calls.
- `packages/tiktok-carousel`: TikTok / TikTok Shop shoppable carousel planning; default to a page-by-page plan, then generate images only when requested. Bundles image generation helpers and runs without another installed Skill.
- `packages/content-create`: media generation from products, images, and prompts; product images and ecommerce videos.
- `packages/tkshop-query`: TK shop list lookup, daily reports, and shop operations analysis.
- `packages/tk-blacklist`: batch TikTok creator blacklist lookup by uniqueId, including feedback count, latest feedback time, and reason.
- `packages/social-monitor`: TikTok/Instagram creator or competitor monitoring, account video lists, single-video material metrics, group-level lists, daily subscriptions, and yesterday-vs-today digest reports.
- `packages/social-comments`: TikTok, Instagram, Douyin, WeChat Channels, and Xiaohongshu single-video comment download and JSON export with pagination.
- `packages/video-understand`: video understanding for local files and TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URLs — produces a natural-language replication prompt for remixing, tagging, or video breakdown.
- `packages/video-remake`: viral video remaking (爆款复刻): semantic cuts, muted reference clips, Wan3.0 segment generation, per-segment user approval, and final merge.
- `packages/video-publish`: batch video publishing to TikTok Shop / TikTok creator accounts, schedule CSV generation, creator/product lookup, dry-run validation, and confirmed publishing.

## Shared Rules

- Installing a Skill does not require authentication. When a Lingtu task needs `LINGTU_API_KEY` and it is missing, direct the user to https://ailingtu.com/api-keys to create or manage a key and configure `LINGTU_API_KEY` in the environment running the Skill before retrying. Account-binding URL generation has been removed. Read `shared/references/api-key-setup.md` and show OS-specific terminal opening, setup commands, and app restart steps; do not just tell users to configure an environment variable. Never ask for, display, or store their API key.
- `packages/openapi-guide` is the exception: it reads public documentation and must never start account binding, inspect credentials, or call protected business endpoints. Developer applications use their own server-side credentials when run outside the Skill.
- Every authenticated Lingtu request must read only `LINGTU_API_KEY` and send it as the `x-api-key` header. Do not introduce alternate key environment variables or store API keys in this repository.
- Every `packages/*/SKILL.md` must declare `auth: lingtu-api-key` or `auth: none`. Use `python3 scripts/create_package.py ...` for new packages so this contract and the UI metadata are scaffolded consistently.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer the package scripts over ad hoc API calls.

## Routing

Use `packages/openapi-guide` for OpenAPI documentation questions, developer API Key creation/use guidance, endpoint discovery, integration examples, SDK/client code, contract review, and sanitized API error diagnosis. Do not use it to execute the business operation being documented.

Use `packages/tiktok-carousel` for TikTok 带货图文、商品轮播图、多图种草 and shoppable photo carousel requests. Plan first by default; proceed to image generation when the user confirms the plan or explicitly requests direct generation. This route takes precedence over generic product-image generation for these requests.

Use `packages/content-create` for product images, ecommerce videos, and media-generation tasks starting from products or prompts. Reference-based script, shot, pacing, and product adaptation also belong here; read `references/viral-remake-workflow.md`.

Use `packages/tkshop-query` for shop lists, daily reports, merchant/store metrics, and business-operation questions.

Use `packages/tk-blacklist` when the user asks whether one or more TikTok creators are blacklisted, requests TK creator risk checks, or provides uniqueIds for batch blacklist verification.

Use `packages/social-monitor` for TikTok/Instagram creator links, usernames, 达人/竞品监控, group-level monitoring lists, daily digest subscriptions, yesterday-vs-today content reports, single-video metric refreshes, and TikTok/Instagram 素材数据.

Use `packages/social-comments` for “导出视频评论”, “下载评论”, “获取这条 TikTok/Instagram/抖音/视频号/小红书评论”, “抓评论区”, or “评论区反馈”. It only downloads comment data; it does not monitor accounts or query video metrics.

Use `packages/video-understand` when the user asks to analyze, summarize, tag, break down, or 二创 a single video — local file, uploaded material, or TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URL — and wants a replication prompt or content readout.

Use `packages/video-remake` for 爆款复刻: transcribe and split the source video into semantic clips no longer than 15 seconds, mute reference clips, regenerate each with Wan3.0, get per-segment approval, and concatenate. This applies to short and long sources. Adapting a reference script/shot structure to a product is video generation under `packages/content-create`. The distributed package bundles its helpers and runs without other installed Skills.

Use `packages/video-publish` when the user asks to publish videos, batch publish TikTok/TikTok Shop videos, create a publishing schedule table, look up authorized publishing creators, search products for publishing, preview/dry-run a schedule, or confirm a video publishing batch.
