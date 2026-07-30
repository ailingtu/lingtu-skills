# Dify Adapter

Import the package instructions into Dify as prompt/tool documentation.

Recommended setup:

1. Create one workflow or agent for content creation using `packages/content-create/SKILL.md`.
2. Create one workflow or agent for TK shop data queries using `packages/tkshop-query/SKILL.md`.
3. Create one workflow or agent for social monitoring using `packages/social-monitor/SKILL.md`.
4. Create one workflow or agent for video understanding using `packages/video-understand/SKILL.md`.
5. Create one workflow or agent for video publishing using `packages/video-publish/SKILL.md`.
6. Expose scripts through your preferred tool executor or wrap the Lingtu API endpoints directly.
7. Set your API key and run `python3 shared/scripts/user_keys.py single bind` if you need a `/binduser` URL:

```bash
export LINGTU_API_KEY=xxx
```

Scripts read `LINGTU_API_KEY` from the environment and send it as `x-api-key`.

Keep package `references/api.md` as the source of truth for endpoint paths and response fields.
