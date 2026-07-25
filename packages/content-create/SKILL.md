---
name: lingtu-content-create
version: 0.3.1
description: 灵途 AI 内容生成。通过灵途 AI 的任务化接口生成商品主图、AI 视频参考图、电商带货视频、爆款视频复刻等媒体内容。用户提到"生成图片/视频"、"商品图优化"、"参考图三件套"、"带货视频"、"UGC 短视频"、"爆款复刻"（含 TikTok/抖音/小红书/视频号/YouTube/Instagram 源视频），或需要把提示词与多张参考图传给灵途 AI 并轮询任务结果时使用。
---

# 灵途 AI 内容生成（图片 / 视频 / 爆款复刻）

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Overview

Use Lingtu AI's shared schedule API to create generated media from a prompt and optional reference images. Treat image and video creation as variants of the same workflow: submit a schedule creation request, poll by the returned schedule id, then return the generated assets.

This skill also covers product-content workflows around the API:

- Optimizing messy product photos into a standard 3-image AI video reference pack. Read `references/product-reference-workflow.md` when the user gives product images and asks to choose, clean up, optimize, or prepare references for AI video.
- Generating ecommerce selling videos from product references. Read `references/ecommerce-video-workflow.md` when the user asks for selling videos, UGC-style videos, target-market scripts, multiple variants, or short product ads.
- Remaking viral product videos. Read `references/viral-remake-workflow.md` when the user provides a viral video (TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram URL or local file), asks to copy a structure, or wants "爆款复刻". For URL sources, run `packages/video-understand` first to get the replication brief.

Use only the workflow references needed for the request; do not load all of them by default.

## Configuration

Authentication uses the `LINGTU_API_KEY` environment variable. OpenClaw injects it automatically when spawning skill subprocesses. For standalone CLI use, export it:

```bash
export LINGTU_API_KEY=xxx
```

If the user doesn't have an API key yet, generate a `/binduser` URL:

```bash
python3 shared/scripts/user_keys.py single bind
```

Open the returned link, complete the binding on the website, then set `LINGTU_API_KEY`. The key is sent as the `x-api-key` header. Do not commit API keys.

Use `https://api.ailingtu.com` as the default base URL. Read `references/api.md` before changing endpoint paths, request fields, response fields, or status mapping.

## Workflow

1. Collect the generation intent: media kind (`image`, `video`, or another supported type), prompt, output requirements, and optional reference images.
   - Video duration defaults by model: `gemini-omni-video`=10s, `veo3.1-extend`/`veo3.1-lite-extend`=8s, `grok-imagine-1.5`=15s, `seedance2.0-mini`/`seedance2.0`/`seedance2.0-fast`=10s. If the user specifies duration, use the user's value.
   - For AI video prompts, strictly use this field format in this exact order: `Video style:`, `Scene:`, `Camera:`, `Tone & pacing:`, `Character:`, `Spoken script:`, `Audio:`, `Overall feeling:`. Do not add other top-level fields or prose outside the format.
2. Upload local reference image files to Lingtu first via `POST /v1/file/upload` (multipart `file` field) and use the returned `data.url`. The create API only accepts remote http(s) URLs — base64 / `data:` URLs are no longer supported. Preserve the user's order because reference order can influence generation.
3. Create a Lingtu AI schedule using `scripts/lingtu_content_task.py`. The script auto-uploads any local path passed via `--reference-image` and accepts http(s) URLs as-is. Image generation sends references as `params.inputReferences`; video generation sends one reference as `params.inputReference` and multiple references as `params.inputReferences`. The script generates an 8-character `taskId` by default and sends it with the create payload; the schedule create response may also return provider `taskIds`.
4. Unless the user explicitly asks for multiple outputs, pass `--nums 1`, create only one schedule/task for the request, return the first successful asset, and stop. If the current task is pending, processing, or otherwise not explicitly failed or timed out, keep polling that same task and do not create a new one. Do not generate extra variants or rerun the same prompt after success. **Crucial: a script crash, network error, or non-zero exit during polling does NOT mean the task failed.** Always re-run poll-only with the existing id before considering a retry:
   ```bash
   python3 scripts/lingtu_content_task.py --kind video --poll-schedule-id <schedule_id>
   # or
   python3 scripts/lingtu_content_task.py --kind video --poll-task-id <task_id>
   ```
   Only treat the task as failed when the API explicitly returns a failure status (FAILED, CANCELLED, EXPIRED, error).
5. Poll the task id or schedule id until completion, failure, cancellation, or timeout. Use a default timeout of 300 seconds and a short polling interval such as 5 seconds. Treat a returned task `type` that differs from the requested kind as an error.
6. Return the generated image/video URLs or saved files. If the task fails, times out, returns an unknown schema, or the script exits non-zero, report the provider status/error and include this fallback: `生成失败或遇到未知问题，请联系开发者：微信 yh8000m`.

## Product Content Routing

For product content requests, select the narrowest workflow before calling the API:

- **User provides raw product images and asks what to use or improve**: inspect the images first, classify them by role, ask for missing angles only when necessary, then follow `references/product-reference-workflow.md`.
- **User already has 3 optimized reference images and asks for videos**: follow `references/ecommerce-video-workflow.md`.
- **User gives a competitor/viral video (including TikTok / 抖音 / 小红书 / 视频号 / YouTube / Instagram links) or asks to recreate a popular style**: follow `references/viral-remake-workflow.md` (analyze via `packages/video-understand` when a URL is given).

When using generated reference images for video, preserve this order unless the user gives another order: product main image, selling-point/detail image, lifestyle scene image.

## Script Usage

The bundled script supports direct task creation only as an explicit compatibility option. Its default `--create-mode auto` uses schedule creation for both images and videos. Do not submit the same payload through both create APIs for one user request.

```bash
python3 scripts/lingtu_content_task.py \
  --kind video \
  --prompt "A clean product reveal video for a smart desk lamp" \
  --model gemini-omni-video \
  --seconds 10 \
  --size 720x1280 \
  --reference-image ./ref-1.png \
  --reference-image ./ref-2.jpg
```

The script also reads endpoint paths from environment variables:

```bash
export LINGTU_AI_CREATE_MODE="auto"
export LINGTU_AI_CREATE_PATH="/v1/ai/task/create"
export LINGTU_AI_STATUS_PATH="/v1/ai/task/query?taskId={task_id}"
export LINGTU_AI_SCHEDULE_CREATE_PATH="/v1/ai/schedule/create"
export LINGTU_AI_TASK_LIST_PATH="/v1/ai/task/listByScheduleId?scheduleId={schedule_id}"
```

Use `--create-mode schedule` when you want to force schedule behavior explicitly. Use `--client-task-id abc12345` only when the caller needs a specific 8-character task id; otherwise let the script generate one.

For `--kind video`, supported models: `gemini-omni-video` (default), `veo3.1-lite-extend`, `veo3.1-extend`, `grok-imagine-1.5`, `seedance2.0-mini`, `seedance2.0`, `seedance2.0-fast`. Each model has different allowed durations (see `references/api.md`). If a requested model returns "未知模型", do not keep retrying that model; report the provider response and ask for the supported model name or use a confirmed model.

For `--kind image`, supported models: `gpt-image-2` (default), `nano-banana-2`, `nano-banana-2-2k`, `nano-banana-2-4k`, `seedream5.0-lite`.

Use `--payload-json` for provider-specific fields that are not yet formalized in the script:

```bash
python3 scripts/lingtu_content_task.py \
  --kind image \
  --prompt "A clean product hero image" \
  --model gpt-image-2 \
  --aspect-ratio 1:1 \
  --nums 1 \
  --payload-json '{"businessType":"MERCHANT_SKU","businessId":"SKU-001"}'
```

## Result Handling

When the script returns `markdown`, include those Markdown image/video embeds first in the final response so Codex can render generated images and videos directly. The script downloads remote generated images and videos into the output directory when possible, then emits local absolute file paths in Markdown because remote media URLs may render as placeholders in the Codex desktop app. After the rendered media, include the returned `output_dir` as a clickable local directory path so the user can open it and inspect all files. Also present original URLs when they are useful for sharing. Use Markdown media syntax such as `![Lingtu video result](/absolute/path/result.mp4)`, not a plain text link. When results are base64 payloads, save them under a user-appropriate output directory and return the absolute file paths.

When the script returns `contact_developer` or `message`, include the message in the final response. Do not hide the developer contact on provider failure, timeout, missing credentials, unknown response shape, network errors, or any other unexpected issue.

If the API schema differs from the default script assumptions, update `references/api.md` first, then update `scripts/lingtu_content_task.py` so future uses stay deterministic.
