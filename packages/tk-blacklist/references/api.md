# Lingtu TK Blacklist API

## Shared Configuration

- Base URL: `https://api.ailingtu.com`
- Authentication header: `x-api-key: <LINGTU_API_KEY>`
- Content type: `application/json`
- Do not commit API keys.

## Blacklist Search

Use this endpoint to query blacklist records for one or more TikTok creator unique IDs.

```http
POST /web/influencerBlack/search
Content-Type: application/json

{
  "uniqueIds": ["vexbolts", "xochitlklepper"]
}
```

Request fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `uniqueIds` | `array[string]` | Yes | TikTok creator unique IDs to query. |

Successful response envelope:

```json
{
  "code": 0,
  "message": "成功",
  "data": {
    "list": [
      {
        "uniqueId": "vexbolts",
        "region": "US",
        "nickname": "Vexbolts",
        "count": 3,
        "feedbackAt": "2025-03-01 21:37:12",
        "feedbackReason": "bbbb"
      }
    ],
    "pageNumber": 1,
    "pageSize": 10,
    "total": 1,
    "totalPages": 1
  },
  "timestamp": 1740836909452
}
```

Response fields used by the script:

| Field | Description |
| --- | --- |
| `data.list[].uniqueId` | Creator unique ID returned by the blacklist service. |
| `data.list[].region` | Creator region, nullable. |
| `data.list[].nickname` | Creator nickname, nullable. |
| `data.list[].count` | Number of feedback records. |
| `data.list[].feedbackAt` | Latest feedback time, nullable. |
| `data.list[].feedbackReason` | Latest feedback reason, nullable. |
| `data.pageNumber`, `data.pageSize`, `data.total`, `data.totalPages` | Pagination metadata from the backend. |

Status handling:

- Treat `code == 0` as success.
- For any other `code`, surface `message` and the full JSON response.
- HTTP errors should include the response body when available.
