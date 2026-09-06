# Codex Adapter

The core packages are already Codex-compatible because each package contains a `SKILL.md`.

Repository source: https://github.com/ailingtu/lingtu-skills. When users ask to update Lingtu AI skills, pull the latest version from this repository.

Install them with:

```bash
./install.sh codex
```

This copies:

- `packages/content-create` to `~/.codex/skills/lingtu-content-create`
- `packages/tkshop-query` to `~/.codex/skills/lingtu-tkshop-query`
- `packages/social-monitor` to `~/.codex/skills/lingtu-social-monitor`
- `packages/social-comments` to `~/.codex/skills/lingtu-social-comments`
- `packages/video-understand` to `~/.codex/skills/lingtu-video-understand`
- `packages/video-publish` to `~/.codex/skills/lingtu-video-publish`
- `shared/` to `~/.codex/skills/shared`

Before first use, configure your API key locally.

macOS:

```bash
export LINGTU_API_KEY='your-api-key'
```

Windows PowerShell:

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

Scripts read `LINGTU_API_KEY` from the environment and send it as `x-api-key`.
