# Lingtu Video Understand API

## Shared Configuration

- Base URL: `https://api.ailingtu.com`
- Authentication header: `x-api-key: <api-key>`
- Do not commit API keys.

## File Upload

Upload a local video before replicating, when no public URL is available.

```http
POST /v1/file/upload
Content-Type: multipart/form-data
```

Form field: `file` (single binary part).

Response:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 765307,
    "url": "https://static.ailingtu.com/file/2026-06-14/<hash>.mp4",
    "isNew": true
  },
  "timestamp": 1781437383620
}
```

- `data.id` is the file id. Pass it as `businessId` with `businessType: "FILE"` to the replication endpoint.
- `data.url` is the CDN URL of the stored file.
- `data.isNew` is `false` when the same file content was already uploaded; the API returns the previously stored id instead of duplicating storage.
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
  url?: string;               // public TikTok / Douyin / YouTube / Instagram URL when no businessId
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
- No explicit `[DONE]` sentinel and no terminal `status: "done"` event has been observed; do not rely on one.
- The `id` stays constant across chunks for a single request and identifies the analysis task.

To assemble the final prompt, concatenate `result` from every `streaming` event in arrival order. The full prompt is a Markdown-style document containing sections like `**Video Script Title**`, `**Characters / Main Subjects**`, `**Scene / Environment**`, `**Script**` (with timestamps), and `**Notes**`.

### Errors

HTTP errors are returned with a JSON body and no SSE frames. Surface the status code and body verbatim.
