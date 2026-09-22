# Public video fetch

## Shared configuration

- Base URL: `https://api.ailingtu.com`
- Authentication: `x-api-key: <LINGTU_API_KEY>`
- Content type: `application/json`
- Success: HTTP 2xx and response `code === 0` with an object `data`
- Operation: `fetchPublicVideoData`
- Source: <https://ailingtu.com/openapi/operations/fetchPublicVideoData.md>

This Skill calls only this endpoint. Do not switch to `/v1/material/tiktok/fetch`, `/v1/material/ins/fetch`, or the comment endpoints.

## POST /v1/material/fetch

Fetch public video views, engagement metrics, and any direct media URL included in `data`.

Supported page URLs: TikTok, Douyin, WeChat Channels, Xiaohongshu, Instagram, and YouTube. The request does not take a platform field.

```ts
export interface Request {
  /** Public http or https URL of the content. */
  videoUrl: string;
}
```

```json
{
  "videoUrl": "https://www.tiktok.com/@creator/video/7123456789012345678"
}
```

### Success response

`data.additionalProperties` is allowed. The published example contains these fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `videoId` | string | Platform video id |
| `uniqueId` | string | Creator handle, when the platform provides one |
| `playCount` | integer | Views |
| `diggCount` | integer | Likes |
| `commentCount` | integer | Comments |
| `shareCount` | integer | Shares |
| `collectCount` | integer | Saves |
| `coverUrl` | string(uri) | Cover image. Signed and short-lived |
| `imageList` | array | Photo-note images. Each item may be `{ url, width, height }`. Save every `url` in order |
| `videoDesc` | string | Caption |
| `releaseAt` | integer | Publish time, Unix seconds UTC |

```json
{
  "code": 0,
  "data": {
    "videoId": "7624922739500993822",
    "uniqueId": "creator",
    "playCount": 2109422,
    "diggCount": 143027,
    "commentCount": 1320,
    "shareCount": 36150,
    "collectCount": 17710,
    "coverUrl": "https://cdn.example.com/cover.jpg",
    "videoDesc": "caption #tag",
    "releaseAt": 1775315687
  },
  "message": "success"
}
```

### Direct video URL

For a photo note (`materialType` is `PHOTO`, or `imageList` is present and this is not a `VIDEO`), download each `imageList` URL in order. If that list is empty and there is no video address, save `coverUrl`. Do not save a video's `coverUrl` as a photo set. Image addresses are signed and short-lived. Do not attach the API key when downloading them.

When `data` also contains a direct video URL, download that file. Choose the first http(s) string in this order:

1. `downloadAddr`
2. `playAddr`
3. `videoUrl`, only when it differs from the page URL sent in the request

These addresses are signed and short-lived. Prefer `downloadAddr` for the watermark-free file. Send `x-api-key` only to the Lingtu API host. Do not attach the API key when downloading the media URL. A `VIDEO` response saves the video only. If neither a video address nor photo images are present, return the metrics and report that this response has no downloadable file.

### Errors

| HTTP | Meaning |
| --- | --- |
| 400 | Invalid request parameters or body |
| 401 | API key missing or invalid |
| 403 | API key lacks permission for this operation |
| 404 | The public work does not exist or has been deleted |
| 429 | Too many requests. Retry with exponential backoff |
| 500 | Unexpected server error. Retry transient failures with exponential backoff |
