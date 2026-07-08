# Lingtu AI Agent Kit

Use this repository as a reusable Lingtu AI capability kit.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Routing

- For turning a video file (uploaded material) or a TikTok/YouTube/Instagram URL into a natural-language replication prompt (for 二创 generation or video tagging/understanding), read `packages/video-understand/SKILL.md`.
- For image generation, product reference optimization, ecommerce videos, and viral-remake media workflows, read `packages/content-create/SKILL.md`.
- For TK shop data lookup, daily reports, shop lists, and operations analysis, read `packages/tkshop-query/SKILL.md`.
- For TikTok/Instagram creator or competitor monitoring, recent-video lookups, single-video metric refreshes, video comment exports/downloads, comment feedback summaries, and content intelligence reports, read `packages/social-monitor/SKILL.md`.
- For TK blacklist lookup — batch query whether TikTok creator uniqueIds are in the blacklist, returning region, nickname, feedback count, latest feedback time, and reasons — read `packages/tk-blacklist/SKILL.md`.
- For batch TikTok video publishing — generating Excel schedule templates, uploading videos, and creating scheduled posts to TikTok Shop (带货) or TikTok nurture (养号) accounts — read `packages/video-publish/SKILL.md`.
- (WIP, do not advertise to end users) For turning structured report JSON into a shareable PNG long-image, read `packages/report-render/SKILL.md`. Still under development — only invoke when explicitly asked.

## Environment & Authentication

The `LINGTU_API_KEY` environment variable is the sole authentication method. OpenClaw injects it automatically when spawning skill subprocesses. For standalone CLI use, export it manually:

```
export LINGTU_API_KEY=xxx
```

When the user explicitly asks to bind, configure, or set up their Lingtu / 灵途 API key — e.g. "绑定灵途密钥"、"配置灵途 API Key"、"bind lingtu key"、"帮我绑定一下灵途" — run:

```
python3 shared/scripts/user_keys.py single bind
```

This generates a `/binduser` authorization link. Return the link to the user and instruct them to open it in a browser. After binding on the website, the user gets their API key and sets `LINGTU_API_KEY`.

## Execution

Use the scripts bundled in each package:

- `packages/video-understand/scripts/lingtu_video_understand.py`
- `packages/content-create/scripts/lingtu_content_task.py`
- `packages/tkshop-query/scripts/lingtu_shop_data.py`
- `packages/social-monitor/scripts/lingtu_social_monitor.py`
- `packages/tk-blacklist/scripts/lingtu_tk_blacklist.py`
- `packages/report-render/scripts/lingtu_report_render.py` (WIP)
- `packages/video-publish/scripts/lingtu_video_publish.py`

Read the relevant package `references/api.md` before changing API paths, schemas, response parsing, or status mappings.
