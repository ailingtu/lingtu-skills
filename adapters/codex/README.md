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
- `packages/video-understand` to `~/.codex/skills/lingtu-video-understand`
- `packages/video-publish` to `~/.codex/skills/lingtu-video-publish`
- `packages/tk-blacklist` to `~/.codex/skills/lingtu-tk-blacklist`
- `shared/` to `~/.codex/skills/shared`

Before first use, set your API key and run `python3 shared/scripts/user_keys.py single bind` if you need a `/binduser` URL:

```bash
export LINGTU_API_KEY=xxx
```

Scripts read `LINGTU_API_KEY` from the environment and send it as `x-api-key`.
