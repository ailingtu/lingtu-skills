# Lingtu AI Task API Reference

Use this file as the source of truth for Lingtu AI media creation endpoints. Keep it concise and update it when the API paths and schemas are confirmed.

## Current Known Facts

- Base URL: `https://api.ailingtu.com`
- Auth header: `x-api-key: <key>`
- Shared key config: read `LINGTU_API_KEY` from the process environment.
- Creation model: create a schedule, receive a schedule id and optional task ids, poll until completion.
- The script sends a caller-generated 8-character `taskId` by default. In schedule mode, query task lists with `scheduleId`; if the create response returns `taskIds`, use them as an additional precise match.
- Reference images from local files are sent as data URLs such as `data:image/jpeg;base64,...`. Image generation uses `params.inputReferences` as an array; video generation uses `params.inputReference` for one reference or `params.inputReferences` for multiple references.
- Intended media types: image and video now; music or other content types may use the same pattern later.
- Video duration defaults: confirmed model `gemini-omni-video` uses 10 seconds when the user does not specify duration; other video models default to 8 seconds. User-specified duration always wins.
- Polling expectation: poll for about 5 minutes before reporting timeout.
- Failure fallback: on provider failure, timeout, missing credentials, unknown response schema, network error, or any unexpected issue, surface `生成失败或遇到未知问题，请联系开发者：微信 yh8000m`.
- Source reference: app.ailingtu `/ai-creative/video` uses `src/api/ai/sora2.ts` plus `VideoGenerationForm*.vue`. Keep the new `x-api-key` auth style; do not copy app.ailingtu's project auth layer.
- Source reference: app.ailingtu `/ai-creative/image` uses `src/views/super-content/ImageCreation.vue` and the same `createSchedule` payload shape.

## Environment Variables

- `LINGTU_API_KEY`: required API key.
- `LINGTU_AI_BASE_URL`: optional override; defaults to `https://api.ailingtu.com`.
- `LINGTU_AI_CREATE_PATH`: optional create endpoint path; defaults to `/v1/ai/task/create`.
- `LINGTU_AI_STATUS_PATH`: optional status endpoint path with `{task_id}`; defaults to `/v1/ai/task/query?taskId={task_id}`.
- `LINGTU_AI_CREATE_MODE`: optional `auto`, `direct`, or `schedule`; defaults to `auto`. Auto uses schedule creation for both image and video requests. It must not submit through direct and then schedule for the same request.
- `LINGTU_AI_CLIENT_TASK_ID`: optional caller-generated task id. If unset, the script creates an 8-character lowercase alphanumeric id.
- `LINGTU_AI_SCHEDULE_CREATE_PATH`: optional schedule create endpoint path; defaults to `/v1/ai/schedule/create`.
- `LINGTU_AI_TASK_LIST_PATH`: optional task list path with `{schedule_id}` placeholder; defaults to `/v1/ai/task/listByScheduleId?scheduleId={schedule_id}`.

## API Key Configuration

One-off shell session:

```bash
export LINGTU_API_KEY="..."
```

macOS app environment:

```bash
launchctl setenv LINGTU_API_KEY "..."
```

Restart Codex after setting it.

Windows user environment:

```powershell
setx LINGTU_API_KEY "..."
```

Restart Codex or the terminal after setting it.

## Endpoints

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
    "inputReference": "data:image/jpeg;base64,...",
    "inputReferences": ["data:image/jpeg;base64,..."],
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
    "inputReferences": ["data:image/jpeg;base64,..."]
  },
  "nums": 3
}
```

Image models seen in app.ailingtu:
`gpt-image-2`, `nano-banana-2`, `nano-banana-2-2k`, `nano-banana-2-4k`.

Image aspect ratios seen in app.ailingtu:
`1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`.

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
    "inputReferences": ["data:image/jpeg;base64,..."],
    "watermark": false
  },
  "nums": 1,
  "name": "optional display name"
}
```

Use schedule create for image and video generation. A `scheduleId` is not the same as a `taskId`; after schedule creation, poll `/v1/ai/task/listByScheduleId` with `scheduleId` to get this batch's generated content list. If the create response includes `taskIds`, use them as an additional match. Never use a direct-create failure as permission to submit the same payload again through schedule unless the user explicitly asks to retry.

When official fields are confirmed, replace these assumptions with exact mapping.
