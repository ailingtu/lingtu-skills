# Lingtu Video Remake API

本文件仅记录此 Skill 自己使用的接口，不依赖其他 Skill 的文档或脚本。

## 通用配置

- Base URL：`https://api.ailingtu.com`
- 认证头：`x-api-key: <LINGTU_API_KEY>`
- 文件上传：`POST /v1/file/upload`
- 任务创建：`POST /v1/ai/schedule/create`
- 按排期查询：`GET /v1/ai/task/listByScheduleId?scheduleId={schedule_id}`

以上路径可分别通过 `LINGTU_AI_BASE_URL`、`LINGTU_FILE_UPLOAD_PATH`、`LINGTU_AI_SCHEDULE_CREATE_PATH` 和 `LINGTU_AI_TASK_LIST_PATH` 覆盖。

## 文件上传

使用 `multipart/form-data`，字段名为 `file`。成功响应需要包含正整数 `data.id`：

```json
{
  "code": 0,
  "data": {
    "id": 1710086,
    "url": "https://static.ailingtu.com/file/example.mp4"
  }
}
```

上传的是已经通过 FFmpeg 移除音轨、时长不超过15秒的片段。

## Wan3.0 排期创建

```json
{
  "taskId": "a1b2c3d4",
  "type": "VIDEO_GENERATION",
  "params": {
    "prompt": "全局复刻要求",
    "model": "wan3.0-video",
    "seconds": 15,
    "size": "720x1280",
    "videoFileIds": [1710086],
    "watermark": false
  },
  "nums": 1,
  "name": "remake-job-segment-001-attempt-1"
}
```

- `seconds` 为片段实际时长向上取整，范围为 1–15。
- 每个任务只传一个消音参考片段。
- 每次只创建一个结果。
- 成功响应通常包含 `data.scheduleId`，也可能包含 `data.taskIds`。

## 查询与恢复

查询响应中的任务列表可能位于 `list`、`records`、`items` 或对应的 `data.*` 字段。处理状态包括 `WAITING_SUBMIT`、`SUBMITTING`、`PENDING`、`PROCESSING`；成功状态包括 `COMPLETED`、`SUCCESS`、`DONE`；失败状态包括 `FAILED`、`CANCELLED`、`EXPIRED`、`ERROR`。

生成成功后从 `customResult.videoUrl`、`result.videoUrl`、`result.url`、`videoUrl` 或 `resultUrl` 提取视频地址。

轮询超时或网络错误时保留 `schedule_id` 和 `task_ids`，任务状态保持 `generating`，通过 `poll` 继续查询。只有服务端明确返回失败状态时才标记为 `failed`。

## HTTP ASR 适配

此仓库目前没有确认的 Lingtu ASR 固定路径，因此不虚构默认端点。`prepare --asr-url` 接受用户明确提供的完整 HTTP 地址：

- 请求：`POST multipart/form-data`，视频字段为 `file`，可选字段为 `model`、`language`。
- 认证：优先使用 `ASR_API_KEY`，否则使用 `LINGTU_API_KEY`，请求头同为 `x-api-key`。
- 响应：JSON，时间戳数组可位于根数组、`segments`、`data.segments`、`result.segments` 或 `data.result.segments`。
- 每项需要 `start`、`end`、`text`；时间单位为秒。

