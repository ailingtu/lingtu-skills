# Lingtu AI Agent Kit

Use this repository as a reusable Lingtu AI capability kit.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Routing

- For turning a video file (uploaded material) or a TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URL into a natural-language replication prompt (for 二创 generation or video tagging/understanding), read `packages/video-understand/SKILL.md`.
- For image generation, product reference optimization, ecommerce videos, and viral-remake media workflows, read `packages/content-create/SKILL.md`.
- For TK shop data lookup, daily reports, shop lists, and operations analysis, read `packages/tkshop-query/SKILL.md`.
- For TikTok/Instagram creator or competitor monitoring, recent-video lookups, single-video metric refreshes, and content intelligence reports, read `packages/social-monitor/SKILL.md`.
- For TikTok, Instagram, Douyin, WeChat Channels, or Xiaohongshu single-video comment downloads, exports, and comment feedback data, read `packages/social-comments/SKILL.md`.
- For batch TikTok video publishing — generating Excel schedule templates, uploading videos, and creating scheduled posts to TikTok Shop (带货) or TikTok nurture (养号) accounts — read `packages/video-publish/SKILL.md`.

## Environment & Authentication

The `LINGTU_API_KEY` environment variable is the sole authentication method. If it is missing, give the user the command for their operating system and ask them to run it locally. Never ask them to paste the real key into chat.

macOS:

```bash
export LINGTU_API_KEY='your-api-key'
```

To keep it across terminal sessions, add the same line to `~/.zshrc`, then run `source ~/.zshrc`.

Windows PowerShell:

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

To keep it across sessions, run `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")`, then open a new terminal.

## Execution

Use the scripts bundled in each package:

- `packages/video-understand/scripts/lingtu_video_understand.py`
- `packages/content-create/scripts/lingtu_content_task.py`
- `packages/tkshop-query/scripts/lingtu_shop_data.py`
- `packages/social-monitor/scripts/lingtu_social_monitor.py`
- `packages/social-comments/scripts/lingtu_social_comments.py`
- `packages/video-publish/scripts/lingtu_video_publish.py`

Read the relevant package `references/api.md` before changing API paths, schemas, response parsing, or status mappings.
