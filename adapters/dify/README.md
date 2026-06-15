# Dify Adapter

Import the package instructions into Dify as prompt/tool documentation.

Recommended setup:

1. Create one workflow or agent for content creation using `packages/content-create/SKILL.md`.
2. Create one workflow or agent for TK shop data queries using `packages/tkshop-query/SKILL.md`.
3. Expose scripts through your preferred tool executor or wrap the Lingtu API endpoints directly.
4. Store `LINGTU_API_KEY` as a Dify secret or environment variable. Send it as `x-api-key`.

Keep package `references/api.md` as the source of truth for endpoint paths and response fields.
