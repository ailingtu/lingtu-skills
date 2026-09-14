# AI 带货视频和 AI 商品图片生成 by 灵途 AI

面向电商商家与内容创作者的 AI 带货视频和 AI 商品图片生成 Skill，由灵途 AI 提供。从商品图片、卖点和提示词出发，生成电商带货视频、UGC 短视频、商品主图、卖点细节图和生活场景图。

Current package version: `0.4.0`. Remote installers can compare the `version` field in [`SKILL.md`](./SKILL.md) frontmatter to decide whether an installed copy needs updating.

## What It Does

- Generates product images and ecommerce videos with reference images.
- Designs short selling-video prompts for target markets and languages.
- Creates Lingtu AI tasks, polls them to completion, and returns generated media URLs or local files.

## Agent Workflows

The main package instruction file is [`SKILL.md`](./SKILL.md). Codex can read it directly as a skill, and other agents can use it as the package prompt. Detailed workflows live in [`references/`](./references):

- [`wan-prompt-guide.md`](./references/wan-prompt-guide.md): Wan 3.0 的素材指代、音色与台词、镜头和声音控制规则。
- [`ecommerce-video-workflow.md`](./references/ecommerce-video-workflow.md): create target-market ecommerce video variants.
- [`api.md`](./references/api.md): Lingtu AI task API assumptions and schema notes.

## Requirements

All authenticated requests use only the `LINGTU_API_KEY` environment variable and send it as `x-api-key`. If it is missing, ask the user to create or manage a key at https://ailingtu.com/api-keys and configure `LINGTU_API_KEY` in the environment running the Skill before retrying. Never paste the key into chat or commit it or generated private media.

## 模型偏好

视频默认使用 `wan3.0-video`，图片默认使用 `gpt-image-2`。不指定模型时自动读取本机偏好；“这次用”只覆盖当前任务，“以后默认用”则保存到 `~/.config/lingtu/content-create.json`，新对话继续沿用，升级不会覆盖。操作命令见 [模型偏好说明](./references/model-preferences.md)。

## Script Usage

Create a vertical ecommerce video using the saved or built-in model and its default duration:

```bash
python3 scripts/lingtu_content_task.py \
  --kind video \
  --size 480x854 \
  --prompt "15s vertical realistic phone video..." \
  --reference-image ./ref-1.png \
  --reference-image ./ref-2.png \
  --reference-image ./ref-3.png \
  --reference-video ./motion-reference.mp4 \
  --reference-audio ./voice-reference.mp3
```

For `wan3.0-video`, `--reference-video` and `--reference-audio` (also available as `--reference-dubbing`) accept either a local media path or an existing positive Lingtu file id. Repeat either flag to preserve multiple references in order.

Create a product image:

```bash
python3 scripts/lingtu_content_task.py \
  --kind image \
  --aspect-ratio 9:16 \
  --prompt "Create a clean product hero image..." \
  --reference-image ./product.jpg
```

## License

Licensed under the Apache License, Version 2.0. See [`LICENSE`](./LICENSE).

Generated media examples, if any, are for demonstration only and may have separate usage restrictions.

完整配置步骤（含 Mac / Windows 打开终端、命令和重启说明）：[API Key 配置指南](../../shared/references/api-key-setup.md)。
