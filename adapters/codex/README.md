# Codex Adapter

The two core packages are already Codex-compatible because each package contains a `SKILL.md`.

Repository source: https://github.com/ailingtu/lingtu-skills. When users ask to update Lingtu AI skills, pull the latest version from this repository.

Install them with:

```bash
./install.sh codex
```

This copies:

- `packages/content-create` to `~/.codex/skills/lingtu-content-create`
- `packages/tkshop-query` to `~/.codex/skills/tkshop-query`

Set `LINGTU_API_KEY` before launching Codex.
