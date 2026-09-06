# Lingtu Content Create

Lingtu Content Create is a reusable agent package for product-content generation with Lingtu AI. It supports image generation, optimized product reference images, ecommerce/UGC-style selling videos, viral-remake workflows, and direct Lingtu AI task submission through a schedule API.

Current package version: `0.3.3`. Remote installers can compare the `version` field in [`SKILL.md`](./SKILL.md) frontmatter to decide whether an installed copy needs updating.

## What It Does

- Optimizes messy product photos into a standard 3-image AI video reference pack.
- Generates product images and ecommerce videos with reference images.
- Designs short selling-video prompts for target markets and languages.
- Supports viral product video remake workflows.
- Creates Lingtu AI tasks, polls them to completion, and returns generated media URLs or local files.

## Agent Workflows

The main package instruction file is [`SKILL.md`](./SKILL.md). Codex can read it directly as a skill, and other agents can use it as the package prompt. Detailed workflows live in [`references/`](./references):

- [`product-reference-workflow.md`](./references/product-reference-workflow.md): choose and optimize product images into product-main, selling-point, and lifestyle-scene references.
- [`ecommerce-video-workflow.md`](./references/ecommerce-video-workflow.md): create target-market ecommerce video variants.
- [`viral-remake-workflow.md`](./references/viral-remake-workflow.md): analyze and remake viral product video structures.
- [`api.md`](./references/api.md): Lingtu AI task API assumptions and schema notes.

## Requirements

Authentication uses the `LINGTU_API_KEY` environment variable. Configure it locally and do not paste the real key into chat.

macOS:

```bash
export LINGTU_API_KEY='your-api-key'
```

Windows PowerShell:

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

For persistent setup, add the export to `~/.zshrc` on macOS, or run `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")` on Windows and open a new terminal.

The key is sent as `x-api-key: <key>`. Do not commit API keys or generated private media.

## Script Usage

Create a 15-second vertical ecommerce video with the default video model:

```bash
python3 scripts/lingtu_content_task.py \
  --kind video \
  --model wan3.0-video \
  --seconds 15 \
  --size 720x1280 \
  --prompt "15s vertical realistic phone video..." \
  --reference-image ./ref-1.png \
  --reference-image ./ref-2.png \
  --reference-image ./ref-3.png \
  --reference-video ./motion-reference.mp4 \
  --reference-audio ./voice-reference.mp3
```

For `wan3.0-video`, `--reference-video` and `--reference-audio` (also available as `--reference-dubbing`) accept either a local media path or an existing positive Lingtu file id. Repeat either flag to preserve multiple references in order.

Create an optimized product reference image:

```bash
python3 scripts/lingtu_content_task.py \
  --kind image \
  --model gpt-image-2 \
  --aspect-ratio 3:4 \
  --prompt "Create a clean AI video reference image..." \
  --reference-image ./product.jpg
```

## Recommended Product Reference Pack

For ecommerce video generation, use this order:

1. Product main image
2. Selling-point or detail image
3. Lifestyle scene image

This order helps the video model first lock product identity, then understand the key action and target scene.

## License

Licensed under the Apache License, Version 2.0. See [`LICENSE`](./LICENSE).

Generated media examples, if any, are for demonstration only and may have separate usage restrictions.
