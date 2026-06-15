# Lingtu AI Capabilities

Use Lingtu AI packages from this repository when the user requests media generation or TK shop data analysis.

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

## Authentication

Require `LINGTU_API_KEY` in the process environment. Send it as `x-api-key`. Never write customer API keys into source files.
