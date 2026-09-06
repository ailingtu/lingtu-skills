# Lingtu Content Create

Use this directory when the user asks Claude Code or OpenClaw to create images, product images, videos, or other media through Lingtu AI.

## Requirements

Authentication uses the `LINGTU_API_KEY` environment variable. If it is missing, give the user the matching local command: macOS `export LINGTU_API_KEY='your-api-key'`; Windows PowerShell `$env:LINGTU_API_KEY = "your-api-key"`. Never ask the user to paste the real key into chat. The key is sent as the `x-api-key` header.

## Workflow

1. Read `references/api.md` if endpoint fields or response fields are unclear.
2. Use `scripts/lingtu_content_task.py` to create the schedule and poll it. The default `--create-mode auto` uses schedule creation for both images and videos. Do not submit the same prompt through both direct and schedule APIs for one request.
3. Preserve reference order. Pass images with repeated `--reference-image`; the script auto-uploads local files and uses the returned CDN URL. For `wan3.0-video`, pass reference videos with repeated `--reference-video` and reference voiceovers with repeated `--reference-audio` (or `--reference-dubbing`). These flags accept a local file path or an existing positive Lingtu file id and send integer arrays as `params.videoFileIds` / `params.audioFileIds`.
4. Unless the user explicitly asks for multiple outputs, create exactly one media task with `--nums 1`, return the first successful asset, and stop. If the current task is pending, processing, or otherwise not explicitly failed or timed out, keep polling that same task and do not create a new one. Do not create additional variants, rerun the same prompt, or keep submitting new schedules after a successful result. **Crucial: a script crash, network error, or non-zero exit during polling does NOT mean the task failed.** Always re-run poll-only with `--poll-task-id` or `--poll-schedule-id` before even considering a retry. Only treat the task as failed when the API explicitly returns a failure status (FAILED, CANCELLED, EXPIRED, error).
5. Return generated URLs or saved output paths from the script JSON. If the script returns `markdown`, include those Markdown embeds first in the final response so image and video results render directly. Then include the returned `output_dir` as a clickable local directory path so the user can open the folder. The script downloads remote images and videos to local absolute paths when possible; for videos, use `![Lingtu video result](/absolute/path/result.mp4)` instead of a plain link.
6. If the script reports `Task type mismatch`, do not show the returned asset as success; report the expected and actual task types.
7. The script sends an 8-character `taskId` by default. Use `--client-task-id` only when a caller needs a specific id.
8. For video models, omit `--seconds` unless the user specifies duration. Default durations: `wan3.0-video`=15s, `gemini-omni-video`=10s, `veo3.1-lite-extend`/`veo3.1-extend`=8s, `grok-imagine-1.5`=15s, `seedance2.0-mini`/`seedance2.0`/`seedance2.0-fast`=10s. `wan3.0-video` also accepts `-1` for adaptive duration or any integer from 1 through 30.
9. If generation fails, times out, returns an unknown schema, or the script exits non-zero, include this fallback in the final response: `生成失败或遇到未知问题，请联系开发者：微信 yh8000m`.

## Examples

Create an image:

```bash
python3 scripts/lingtu_content_task.py \
  --kind image \
  --prompt "A clean product hero image" \
  --model gpt-image-2 \
  --aspect-ratio 1:1 \
  --nums 1 \
  --create-mode schedule \
  --reference-image /absolute/path/ref.png
```

Create a video:

```bash
python3 scripts/lingtu_content_task.py \
  --kind video \
  --prompt "A clean 15 second product reveal video" \
  --model wan3.0-video \
  --seconds 15 \
  --size 720x1280 \
  --reference-image /absolute/path/ref-1.png \
  --reference-image /absolute/path/ref-2.png \
  --reference-video /absolute/path/motion-reference.mp4 \
  --reference-audio /absolute/path/voice-reference.mp3
```

Defaults:

- Base URL: `https://api.ailingtu.com`
- Direct task create path: `/v1/ai/task/create`
- Query path: `/v1/ai/task/query?taskId={task_id}`
- Schedule create path: `/v1/ai/schedule/create`
- Task list path: `/v1/ai/task/listByScheduleId?scheduleId={schedule_id}`
- Image default model: `gpt-image-2`
- Video default model: `wan3.0-video`
