# Lingtu AI Task API Reference

Use this file as the source of truth for Lingtu AI media creation endpoints. Keep it concise and update it when the API paths and schemas are confirmed.

## Current Known Facts

- Base URL: `https://api.ailingtu.com`
- Auth header: `x-api-key: <key>`
- Shared key config: reads `LINGTU_API_KEY` from the environment.
- Creation model: create a schedule, receive a schedule id and optional task ids, poll until completion.
- The script sends a caller-generated 8-character `taskId` by default. In schedule mode, query task lists with `scheduleId`; if the create response returns `taskIds`, use them as an additional precise match.
- Reference images must be remote CDN URLs. Local files must be uploaded through `POST /v1/file/upload` first; use the returned `data.url` as the reference. Base64 / `data:` URLs are no longer accepted by the create API. Image generation uses `params.inputReferences` as an array; video generation uses `params.inputReference` for one reference or `params.inputReferences` for multiple references.
- Intended media types: image and video now; music or other content types may use the same pattern later.
- Video duration defaults (user-specified duration always wins):

| model | allowed seconds | default |
|---|---|---|
| `gemini-omni-video` | 6, 8, 10 | 10 |
| `veo3.1-lite-extend` | 8 (fixed) | 8 |
| `veo3.1-extend` | 8 (fixed) | 8 |
| `grok-imagine-1.5` | 6, 10, 15, 20, 25, 30 | 15 |
| `seedance2.0-mini` | 4, 8, 10, 12, 15 | 10 |
| `seedance2.0` | 4, 8, 10, 12, 15 | 10 |
| `seedance2.0-fast` | 4, 8, 10, 12, 15 | 10 |
- Polling expectation: poll for about 5 minutes before reporting timeout.
- Failure fallback: on provider failure, timeout, missing credentials, unknown response schema, network error, or any unexpected issue, surface `生成失败或遇到未知问题，请联系开发者：微信 yh8000m`.
- Source reference: app.ailingtu `/ai-creative/video` uses `src/api/ai/sora2.ts` plus `VideoGenerationForm*.vue`. Keep the new `x-api-key` auth style; do not copy app.ailingtu's project auth layer.
- Source reference: app.ailingtu `/ai-creative/image` uses `src/views/super-content/ImageCreation.vue` and the same `createSchedule` payload shape.

## Environment Variables

- `LINGTU_AI_BASE_URL`: optional override; defaults to `https://api.ailingtu.com`.
- `LINGTU_AI_CREATE_PATH`: optional create endpoint path; defaults to `/v1/ai/task/create`.
- `LINGTU_AI_STATUS_PATH`: optional status endpoint path with `{task_id}`; defaults to `/v1/ai/task/query?taskId={task_id}`.
- `LINGTU_AI_CREATE_MODE`: optional `auto`, `direct`, or `schedule`; defaults to `auto`. Auto uses schedule creation for both image and video requests. It must not submit through direct and then schedule for the same request.
- `LINGTU_AI_CLIENT_TASK_ID`: optional caller-generated task id. If unset, the script creates an 8-character lowercase alphanumeric id.
- `LINGTU_AI_SCHEDULE_CREATE_PATH`: optional schedule create endpoint path; defaults to `/v1/ai/schedule/create`.
- `LINGTU_AI_TASK_LIST_PATH`: optional task list path with `{schedule_id}` placeholder; defaults to `/v1/ai/task/listByScheduleId?scheduleId={schedule_id}`.

## API Key Configuration

Authentication uses the `LINGTU_API_KEY` environment variable. OpenClaw injects it automatically. For standalone CLI use, `export LINGTU_API_KEY=xxx`.

If you don't have an API key yet, generate a `/binduser` URL:

```bash
python3 shared/scripts/user_keys.py single bind
```

Open the returned link, complete the binding on the website, then set `LINGTU_API_KEY`.

## Endpoints

### File Upload

Upload a local image to obtain a remote CDN URL before creating an image/video task. The create API only accepts http(s) URLs for `params.inputReference` / `params.inputReferences`; base64 / data URLs are no longer supported.

- Method: `POST`
- Path: `/v1/file/upload`
- Auth: `x-api-key: <key>`
- Body: `multipart/form-data` with form field `file` (binary file content)
- Success response shape:

```json
{
  "code": 0,
  "data": {
    "id": "file id",
    "url": "https://static.ailingtu.com/...",
    "isNew": true
  }
}
```

- Use `data.url` as the reference image URL when calling schedule/task create.
- `data.isNew` is `false` when the same file content was already uploaded; the API returns the previously stored id/url.

### Direct Task Create

Use this when Codex needs to create one task and poll it immediately.

- Method: `POST`
- Path: `/v1/ai/task/create`
- Response task id fields: `taskId`, `task_id`, `id`, or nested `data.taskId`

Video request:

```json
{
  "taskId": "abc12345",
  "type": "VIDEO_GENERATION",
  "params": {
    "prompt": "text prompt",
    "model": "gemini-omni-video",
    "seconds": 10,
    "size": "720x1280",
    "inputReference": "https://static.ailingtu.com/ai-images/<id>.jpg",
    "inputReferences": ["https://static.ailingtu.com/ai-images/<id>.jpg"],
    "watermark": false
  },
  "nums": 1
}
```

For model `gemini-omni-video`, the default video request should use `"seconds": 10` unless the user specified another duration.

Image request:

```json
{
  "taskId": "abc12345",
  "type": "IMAGE_GENERATION",
  "params": {
    "prompt": "text prompt",
    "model": "gpt-image-2",
    "aspectRatio": "1:1",
    "inputReferences": ["https://static.ailingtu.com/ai-images/<id>.jpg"]
  },
  "nums": 3
}
```

Image models seen in app.ailingtu:
`gpt-image-2`, `nano-banana-2`, `nano-banana-2-2k`, `nano-banana-2-4k`, `seedream5.0-lite`.

Image aspect ratios seen in app.ailingtu:
`1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`.

## Video Model Reference

### All video models

| model | formMode | default seconds | allowed seconds | resolution |
|---|---|---|---|---|
| `gemini-omni-video` | veo | 10 | 6, 8, 10 | 720p, 1080p |
| `veo3.1-lite-extend` | veo | 8 | 8 (fixed) | 720p |
| `veo3.1-extend` | veo | 8 | 8 (fixed) | 720p |
| `grok-imagine-1.5` | grok | 15 | 6, 10, 15, 20, 25, 30 | 720p |
| `seedance2.0-mini` | seedance | 10 | 4, 8, 10, 12, 15 | 480p, 720p |
| `seedance2.0` | seedance | 10 | 4, 8, 10, 12, 15 | 480p, 720p |
| `seedance2.0-fast` | seedance | 10 | 4, 8, 10, 12, 15 | 480p, 720p |

### Resolution → size map

| resolution | portrait (9:16) | landscape (16:9) |
|---|---|---|
| 480p | `480x854` | `854x480` |
| 720p | `720x1280` | `1280x720` |
| 1080p | `1080x1920` | `1920x1080` |

`gemini-omni-video` supports 720p and 1080p. Veo models support 720p only. Seedance supports 480p and 720p. Grok supports 720p only.

### Task Query

- Method: `GET`
- Path: `/v1/ai/task/query`
- Query: `taskId=<task id>`

Expected detail fields seen in app.ailingtu:

```json
{
  "taskId": "task id",
  "thirdTaskId": "provider task id",
  "status": "PROCESSING",
  "type": "VIDEO_GENERATION",
  "model": "gemini-omni-video",
  "params": {
    "prompt": "text prompt"
  },
  "resultUrl": "provider result url",
  "customResult": {
    "coverUrl": "cover image url",
    "videoUrl": "video url"
  },
  "result": {
    "url": "video url",
    "thumbnailUrl": "cover image url"
  },
  "reason": "failure reason"
}
```

For image requests, require returned `type` to be `IMAGE_GENERATION`. For video requests, require returned `type` to be `VIDEO_GENERATION`. A mismatch means the provider routed or interpreted the request incorrectly; do not treat that result as success.

Processing statuses:
`WAITING_SUBMIT`, `SUBMITTING`, `SUBMIT_FAILED`, `PENDING`, `PROCESSING`, plus lowercase variants.

Success statuses:
`COMPLETED`, `completed`, `succeeded`, `success`, `done`, `finished`.

Failure statuses:
`FAILED`, `failed`, `CANCELLED`, `cancelled`, `EXPIRED`, `expired`, `error`, `failure`.

Primary video result fields:
`customResult.videoUrl`, `customResult.coverUrl`, `result.url`, `result.thumbnailUrl`, `resultUrl`.

Primary image result fields:
`result.url`, `result.resultUrl`, `result.videoUrl`, `resultUrl`, `customResult.coverUrl`, `customResult.videoUrl`, `result.thumbnailUrl`.

### Schedule Create

Image and video generation both use schedule creation:

- Method: `POST`
- Path: `/v1/ai/schedule/create`
- Response: `{ "data": { "scheduleId": "...", "taskIds": ["..."] } }`

Schedule payload wraps the same `params` shape:

```json
{
  "taskId": "abc12345",
  "type": "VIDEO_GENERATION",
  "params": {
    "prompt": "text prompt",
    "model": "gemini-omni-video",
    "seconds": 10,
    "size": "720x1280",
    "inputReferences": ["https://static.ailingtu.com/ai-images/<id>.jpg"],
    "watermark": false
  },
  "nums": 1,
  "name": "optional display name"
}
```

Use schedule create for image and video generation. A `scheduleId` is not the same as a `taskId`; after schedule creation, poll `/v1/ai/task/listByScheduleId` with `scheduleId` to get this batch's generated content list. If the create response includes `taskIds`, use them as an additional match. Never use a direct-create failure as permission to submit the same payload again through schedule unless the user explicitly asks to retry.

When official fields are confirmed, replace these assumptions with exact mapping.
