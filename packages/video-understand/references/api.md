# Lingtu Video Understand API

## Shared Configuration

- Base URL: `https://api.ailingtu.com`
- Authentication header: `x-api-key: <api-key>`
- Do not commit API keys.

## File Upload

Upload a local video before replicating, when no public URL is available. The upload has three steps; file bytes go straight to object storage instead of the API gateway.

Step 1 — presign:

```http
POST /v1/file/presign
Content-Type: application/json
x-api-key: <api-key>
```

Request body: `fileName`, `contentType`, `size` and `hash`. `hash` is the Java-compatible content hash `sha256(hex(raw_bytes).encode("utf-8"))`; files larger than 300M are rejected.

Response:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "fileId": 765307,
    "uploadUrl": "https://<bucket>.tos-.../...&X-Tos-Signature=...",
    "url": "https://static.ailingtu.com/file/2026-06-14/<hash>.mp4",
    "expiresAt": "2026-06-14T10:20:00",
    "isNew": true
  },
  "timestamp": 1781437383620
}
```

Step 2 — `PUT` the raw bytes to `data.uploadUrl` with the same `Content-Type` and no `x-api-key`. Skip PUT and confirm when `data.isNew` is `false`: the same content was uploaded before and the previously stored file is reused.

Step 3 — `POST /v1/file/confirm` with `x-api-key` and body `{"fileId": <data.fileId>}`. It marks the file as usable; without it the file stays unconfirmed and cannot be analysed.

- `data.fileId` is the file id. Pass it as `businessId` with `businessType: "FILE"` to the replication endpoint.
- `data.url` is the CDN URL of the stored file.
- A non-zero `code` indicates an error; surface `message` to the caller.

## Replication Prompt (streaming)

```http
POST /v1/material/analysisTask/stream
Content-Type: application/json
Accept: text/event-stream
```

Request body:

```ts
interface Request {
  businessId?: string;        // material/file id when parsing an uploaded asset
  businessType?: "FILE" | "MATERIAL"; // pair with businessId
  type: "ANALYSIS" | "REPLICATION";   // this skill only sends "REPLICATION"
  url?: string;               // public TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram URL when no businessId
}
```

Send exactly one of:

- `{ type: "REPLICATION", url: "<public video url>" }`
- `{ type: "REPLICATION", businessId: "<id>", businessType: "FILE" | "MATERIAL" }`

The skill currently never sends `type: "ANALYSIS"`. If a future caller needs it, document the exact differences here before wiring it up.

### Streaming response

Server-sent events. Each event line is `data:<json>` (no space after the colon in observed responses, but the script tolerates `data: <json>` too). Each JSON has the shape:

```json
{
  "status": "streaming",
  "result": "<incremental text chunk>",
  "thinking": null,
  "id": 2066122904659169280
}
```

Stream completion:

- The server closes the connection when finished.
- A terminal `status: "done"` event was observed in live testing on 2026-09-16. Accept it as completion; do not append its result again. The client also accepts `[DONE]` and legacy EOF completion.
- The `id` stays constant across chunks for a single request and identifies the analysis task.

To assemble the final prompt, concatenate `result` from every `streaming` event in arrival order. The full prompt is a Markdown-style document containing sections like `**Video Script Title**`, `**Characters / Main Subjects**`, `**Scene / Environment**`, `**Script**` (with timestamps), and `**Notes**`.

### Errors

HTTP errors are returned with a JSON body and no SSE frames. Surface the status code and body verbatim.


### Client validation and output

The client ignores SSE comments and `event`/`id`/`retry` metadata, accepts `data:`
with or without a space and multiline JSON, and supports consecutive JSON data lines
without blank separators as observed on this endpoint. Only `status: "streaming"`
contributes text. Empty prompts, malformed JSON/UTF-8, non-SSE content types,
non-text results, changed task ids, unexpected statuses and non-zero error codes
fail with a non-zero exit. Error-status checks are defensive, not a claim that the
server currently emits those events. Timeout and connection failures also fail;
requests are not automatically replayed.

An explicit `done` event completes the stream after error, task-id and result-type
validation. A non-empty streamed prompt is still required. EOF remains supported
for older responses. A clean early EOF after valid text
cannot be distinguished from normal completion without a server-side completion
marker or task-status contract. The client does not invent a terminal event requirement.
Normal text and JSON are buffered until validation passes; raw output is diagnostic.
