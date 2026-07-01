# Dify Adapter

Import the package instructions into Dify as prompt/tool documentation.

Recommended setup:

1. Create one workflow or agent for content creation using `packages/content-create/SKILL.md`.
2. Create one workflow or agent for TK shop data queries using `packages/tkshop-query/SKILL.md`.
3. Create one workflow or agent for TK blacklist lookup using `packages/tk-blacklist/SKILL.md`.
4. Expose scripts through your preferred tool executor or wrap the Lingtu API endpoints directly.
5. Run `python3 shared/scripts/user_keys.py single bind` to bind the administrator key. Scripts resolve the API key automatically and send it as `x-api-key`. Do not use `LINGTU_API_KEY`.

Keep package `references/api.md` as the source of truth for endpoint paths and response fields.
