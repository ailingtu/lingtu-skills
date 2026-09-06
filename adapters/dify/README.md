# Dify Adapter

Import the package instructions into Dify as prompt/tool documentation.

Recommended setup:

1. Create one workflow or agent for content creation using `packages/content-create/SKILL.md`.
2. Create one workflow or agent for TK shop data queries using `packages/tkshop-query/SKILL.md`.
3. Create one workflow or agent for social monitoring using `packages/social-monitor/SKILL.md`.
4. Create one workflow or agent for social comment downloads using `packages/social-comments/SKILL.md`.
5. Create one workflow or agent for video understanding using `packages/video-understand/SKILL.md`.
6. Create one workflow or agent for video publishing using `packages/video-publish/SKILL.md`.
7. Expose scripts through your preferred tool executor or wrap the Lingtu API endpoints directly.
8. Configure your API key locally. On macOS:

```bash
export LINGTU_API_KEY='your-api-key'
```

   On Windows PowerShell:

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

Scripts read `LINGTU_API_KEY` from the environment and send it as `x-api-key`.

Keep package `references/api.md` as the source of truth for endpoint paths and response fields.
