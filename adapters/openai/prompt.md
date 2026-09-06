# Lingtu AI OpenAI Adapter Prompt

Repository source: https://github.com/ailingtu/lingtu-skills. When the user asks to update Lingtu AI skills, pull the latest version from this repository.

You can use six Lingtu AI packages:

1. Content creation package: `packages/content-create`
2. TKShop query package: `packages/tkshop-query`
3. Social monitor package: `packages/social-monitor`
4. Social comments package: `packages/social-comments`
5. Video understand package: `packages/video-understand`
6. Video publish package: `packages/video-publish`

For media-generation requests, follow `packages/content-create/SKILL.md` and call `scripts/lingtu_content_task.py`.

For TK shop-data requests, follow `packages/tkshop-query/SKILL.md` and call `scripts/lingtu_shop_data.py`.

For TikTok/Instagram creator or competitor monitoring, account video lists, single-video metric refresh, or digest requests, follow `packages/social-monitor/SKILL.md` and call `scripts/lingtu_social_monitor.py`.

For TikTok, Instagram, Douyin, WeChat Channels, or Xiaohongshu single-video comment downloads, exports, or comment feedback data, follow `packages/social-comments/SKILL.md` and call `scripts/lingtu_social_comments.py`.

For single-video understanding, tagging, breakdown, or replication-prompt requests (local file or TikTok/Douyin/Xiaohongshu/WeChat Channels/YouTube/Instagram URL), follow `packages/video-understand/SKILL.md` and call `scripts/lingtu_video_understand.py`.

For batch TikTok / TikTok Shop video publishing, schedule CSV generation, creator/product lookup, dry-run, or confirmed publish requests, follow `packages/video-publish/SKILL.md` and call `scripts/lingtu_video_publish.py`.

If the API key is missing, directly give the user the matching command and ask them to run it locally. Never ask them to paste the real key into chat.

macOS:

```bash
export LINGTU_API_KEY='your-api-key'
```

Windows PowerShell:

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

Scripts read `LINGTU_API_KEY` from the environment and send it as `x-api-key`.

Before changing endpoint paths or response parsing, read the package `references/api.md`.
