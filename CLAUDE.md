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
- (WIP, do not advertise to end users) For turning structured report JSON into a shareable PNG long-image, read `packages/report-render/SKILL.md`. Still under development — only invoke when explicitly asked.

## Environment

Require `LINGTU_API_KEY` in the process environment. Get your key at https://app.ailingtu.com/api-key-management. Send it as the request header `x-api-key`.

## Execution

Use the scripts bundled in each package:

- `packages/video-understand/scripts/lingtu_video_understand.py`
- `packages/content-create/scripts/lingtu_content_task.py`
- `packages/tkshop-query/scripts/lingtu_shop_data.py`
- `packages/social-monitor/scripts/lingtu_social_monitor.py`
- `packages/report-render/scripts/lingtu_report_render.py` (WIP)

Read the relevant package `references/api.md` before changing API paths, schemas, response parsing, or status mappings.
