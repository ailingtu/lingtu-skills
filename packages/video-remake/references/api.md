# Lingtu Video Remake API

本文件仅记录此 Skill 自己使用的接口，不依赖其他 Skill 的文档或脚本。

## 通用配置

- Base URL：`https://api.ailingtu.com`
- 认证头：`x-api-key: <LINGTU_API_KEY>`
- 文件上传：`POST /v1/file/presign` + `POST /v1/file/confirm`
- 任务创建：`POST /v1/ai/schedule/create`
- 按排期查询：`GET /v1/ai/task/listByScheduleId?scheduleId={schedule_id}`

以上路径可分别通过 `LINGTU_AI_BASE_URL`、`LINGTU_FILE_PRESIGN_PATH`、`LINGTU_FILE_CONFIRM_PATH`、`LINGTU_AI_SCHEDULE_CREATE_PATH` 和 `LINGTU_AI_TASK_LIST_PATH` 覆盖。命令行的 `--presign-path` 与 `--confirm-path` 可覆盖上传路径，默认值为 `/v1/file/presign` 与 `/v1/file/confirm`。旧的 `--upload-path` 参数与 `LINGTU_FILE_UPLOAD_PATH` 环境变量已删除，请改用 `--presign-path`。

## 文件上传

分三步，文件字节直传对象存储，不经过 API 网关。单个文件不得超过 300M。

第 1 步：申请上传地址。

```json
{
  "code": 0,
  "data": {
    "fileId": 1710086,
    "uploadUrl": "https://<bucket>.tos-.../...&X-Tos-Signature=...",
    "url": "https://static.ailingtu.com/file/example.mp4",
    "expiresAt": "2026-06-14T10:20:00",
    "isNew": true
  }
}
```

`POST /v1/file/presign`，请求体 `{"fileName", "contentType", "size", "hash"}`；`hash` 为 `sha256(hex(原始字节).encode("utf-8"))`。

第 2 步：`PUT` 原始字节到 `data.uploadUrl`，`Content-Type` 与第 1 步一致，不带 `x-api-key`。`data.isNew` 为 `false` 时说明同内容已上传过，跳过本步与第 3 步。

第 3 步：`POST /v1/file/confirm`，请求体 `{"fileId": <data.fileId>}`。未确认的文件不能用于生成。

`data.fileId` 是文件 ID，`data.url` 是 CDN 地址。视频参考上传的是已经通过 FFmpeg 移除音轨、时长不超过15秒的片段。也可上传图片与音频参考，字段见下文。

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

- `seconds` 默认取片段实际时长向上取整（1–15），显式传 `-1` 时使用自适应时长。
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
- 认证：只使用 `LINGTU_API_KEY`，请求头为 `x-api-key`。不支持其他 Key 环境变量。
- 响应：JSON，时间戳数组可位于根数组、`segments`、`data.segments`、`result.segments` 或 `data.result.segments`。
- 每项需要 `start`、`end`、`text`；时间单位为秒。

## 人物与音色参考参数

Wan3.0 可在同一 `params` 中组合以下字段：

```json
{
  "prompt": "将 @视频1 中的人物替换为 @图1 中的人物，保持场景与动作，清除画面文字。人物用 @音频1 的音色说指定台词，匹配嘴型。",
  "model": "wan3.0-video",
  "seconds": -1,
  "size": "480x854",
  "inputReferences": ["https://static.ailingtu.com/file/example.png"],
  "videoFileIds": [1710086],
  "audioFileIds": [1710087]
}
```

- `inputReferences` 为有序图片 URL 数组；本地图片上传后取 `data.url`。
- `audioFileIds` 为有序音频文件 ID 数组；本地音频上传后取 `data.id`。
- 提示词的 `@图1`、`@视频1`、`@音频1` 分别对应各类素材的顺序；每段仍只传一个消音参考视频。
- `seconds: -1` 表示自适应生成时长，不保证与源片段等长；源视频切片仍不超过15秒。默认维持片段时长向上取整，可显式指定 1–15。
- 上述组合字段有用户提供的后台实际请求作为依据，公共接口文档亦列出对应字段；本次未在线验证生成效果。Skill 继续调用 `/v1/ai/schedule/create`，只使用 `x-api-key`，不使用后台 Bearer 令牌或公司请求头。
