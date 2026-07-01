# Lingtu AI OpenAI Adapter Prompt

Repository source: https://github.com/ailingtu/lingtu-skills. When the user asks to update Lingtu AI skills, pull the latest version from this repository.

You can use four Lingtu AI packages:

1. Content creation package: `packages/content-create`
2. TKShop query package: `packages/tkshop-query`
3. Social monitor package: `packages/social-monitor`
4. TK blacklist package: `packages/tk-blacklist`

For media-generation requests, follow `packages/content-create/SKILL.md` and call `scripts/lingtu_content_task.py`.

For TK shop-data requests, follow `packages/tkshop-query/SKILL.md` and call `scripts/lingtu_shop_data.py`.

For TikTok/Instagram creator or competitor monitoring, account video lists, single-video metric refresh, video comment export/download, or comment feedback summary requests, follow `packages/social-monitor/SKILL.md` and call `scripts/lingtu_social_monitor.py`.

For TK blacklist lookup requests, follow `packages/tk-blacklist/SKILL.md` and call `scripts/lingtu_tk_blacklist.py`.

Before first use, run `python3 shared/scripts/user_keys.py single bind` to bind the administrator key. Scripts resolve the API key automatically and send it as `x-api-key`. Do not set `LINGTU_API_KEY` in the environment.

Before changing endpoint paths or response parsing, read the package `references/api.md`.
