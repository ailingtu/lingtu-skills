# Lingtu Content Create

Use this directory when the user asks Claude Code or OpenClaw to create images, product images, videos, or other media through Lingtu AI.

## Requirements

Single-user mode uses a configured administrator binding. Generate the administrator `/binduser` URL before running business scripts:

```bash
python3 shared/scripts/user_keys.py single bind
```

Open the returned link to bind the administrator's key. Send the resolved key as the request header `x-api-key`.

## Workflow

1. Read `references/api.md` if endpoint fields or response fields are unclear.
2. Use `scripts/lingtu_content_task.py` to create the schedule and poll it. The default `--create-mode auto` uses schedule creation for both images and videos. Do not submit the same prompt through both direct and schedule APIs for one request.
3. Preserve reference image order. Pass references with repeated `--reference-image`; the script auto-uploads local files through `POST /v1/file/upload` and uses the returned CDN URL. Remote http(s) URLs are passed through as-is. The create API only accepts remote URLs — base64 / `data:` URLs are no longer supported.
4. Return generated URLs or saved output paths from the script JSON. If the script returns `markdown`, include those Markdown embeds first in the final response so image and video results render directly. Then include the returned `output_dir` as a clickable local directory path so the user can open the folder. The script downloads remote images and videos to local absolute paths when possible; for videos, use `![Lingtu video result](/absolute/path/result.mp4)` instead of a plain link.
5. If the script reports `Task type mismatch`, do not show the returned asset as success; report the expected and actual task types.
6. The script sends an 8-character `taskId` by default. Use `--client-task-id` only when a caller needs a specific id.
7. For video model `gemini-omni-video`, omit `--seconds` unless the user specifies duration; the script defaults Gemini Omni videos to 10 seconds.
8. If generation fails, times out, returns an unknown schema, or the script exits non-zero, include this fallback in the final response: `生成失败或遇到未知问题，请联系开发者：微信 yh8000m`.

## Examples

Create an image:

```bash
python3 scripts/lingtu_content_task.py \
  --kind image \
  --prompt "A clean product hero image" \
  --model gpt-image-2 \
  --aspect-ratio 1:1 \
  --nums 3 \
  --create-mode schedule \
  --reference-image /absolute/path/ref.png
```

Create a video:

```bash
python3 scripts/lingtu_content_task.py \
  --kind video \
  --prompt "A clean 8 second product reveal video" \
  --model gemini-omni-video \
  --seconds 10 \
  --size 720x1280 \
  --reference-image /absolute/path/ref-1.png \
  --reference-image /absolute/path/ref-2.png
```

Defaults:

- Base URL: `https://api.ailingtu.com`
- Direct task create path: `/v1/ai/task/create`
- Query path: `/v1/ai/task/query?taskId={task_id}`
- Schedule create path: `/v1/ai/schedule/create`
- Task list path: `/v1/ai/task/listByScheduleId?scheduleId={schedule_id}`
- Image default model: `gpt-image-2`
- Video default model: `gemini-omni-video`
