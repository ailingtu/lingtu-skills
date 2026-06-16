# Lingtu TikTok Monitor API

## Shared Configuration

- Base URL: `https://api.ailingtu.com`
- Authentication header: `x-api-key: <LINGTU_API_KEY>`
- Do not commit API keys or private monitoring data.

## Fetch Recent Posts

Endpoint: `GET /v1/influencer/fetchPosts`

Query parameters:

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `uniqueId` | yes | - | TikTok handle, i.e. the `xxx` in `https://www.tiktok.com/@xxx`. |
| `count`    | no  | 40    | Number of recent posts to return. |

Response envelope: `{ code, message, data, timestamp }`.

| `code` | Meaning |
|--------|---------|
| `0`    | Success. `data` is populated. |
| `-1`   | No data. The user does not exist, has no public videos, or the upstream returned empty. `data` is `null`. The Chinese `message` (e.g. `未获取到达人视频数据`) should be surfaced to the user. |
| `-2`   | Wrong HTTP method. Use `GET`, not `POST`. |

### Success response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "authorInfo": {
      "id": "6614519312189947909",
      "nickname": "MrBeast",
      "uniqueId": "mrbeast",
      "signature": "Watch my latest video! 👇",
      "secUid": "MS4wLjAB...",
      "awemeCount": 446,
      "followingCount": 351,
      "followerCount": 128299196,
      "favoritingCount": 1498,
      "totalFavorited": 1308284378
    },
    "authorStats": null,
    "posts": [
      {
        "videoId": "7642346910266739999",
        "desc": "Thanks for the help boys 🫡",
        "createTime": 1779372563,
        "isAd": false,
        "stats": {
          "collectCount": 118474,
          "commentCount": 59984,
          "diggCount": 2505820,
          "playCount": 44552638,
          "shareCount": 32003,
          "repostCount": 0
        },
        "cover": "https://p16-common-sign.tiktokcdn-eu.com/...",
        "duration": 34620,
        "playAddr": "https://api16-normal-no1a.tiktokv.eu/aweme/v1/play/?..."
      }
    ],
    "cursor": 1779372563000,
    "hasMore": true
  },
  "timestamp": 1781175993834
}
```

### Field semantics

`authorInfo` (creator profile):

| Field | Meaning |
|-------|---------|
| `id` | Stable creator id assigned by TikTok. Use as `creator_id`. |
| `uniqueId` | The `@handle` shown in profile URLs. Use as `username`. |
| `nickname` | Display name. |
| `signature` | Profile bio. |
| `awemeCount` | Total public video count. |
| `followerCount` / `followingCount` / `favoritingCount` / `totalFavorited` | Standard TikTok counters. |

`posts[]` (recent videos, newest first):

| Field | Meaning | Notes |
|-------|---------|-------|
| `videoId` | Per-video id. | The shareable URL is `https://www.tiktok.com/@{uniqueId}/video/{videoId}` (the API does not return it directly). |
| `desc` | Caption. | Hashtags must be parsed from this string with a `#xxx` regex; there is no separate hashtags field. |
| `createTime` | Publish time. | **Unix seconds, UTC.** |
| `duration` | Video length. | **Milliseconds.** Divide by 1000 for seconds. |
| `isAd` | Sponsored flag. | |
| `cover` | Cover image URL. | Signed; expires (`x-expires` query) — re-fetch when stale. |
| `playAddr` | Direct play URL. | Signed and short-lived. |
| `stats.playCount` | Views. | |
| `stats.diggCount` | Likes. | |
| `stats.commentCount` | Comments. | |
| `stats.shareCount` | Shares. | |
| `stats.collectCount` | Saves / favorites. | |
| `stats.repostCount` | Reposts. | |

`cursor` is a millisecond timestamp aligned to the oldest post in the page; `hasMore` indicates whether earlier posts exist. Pagination is not currently exposed by the script.

### Error response

```json
{ "code": -1, "message": "未获取到达人视频数据", "data": null, "timestamp": 1781176395 }
```

Surface `message` to the user verbatim — it is already a human-readable Chinese hint.

## Fetch TikTok Material

Endpoint: `POST /v1/material/tiktok/fetch`

Request body:

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `videoUrl` | yes | string | Public TikTok video URL. |

Response envelope: `{ code, message, data, timestamp }`.

### Success response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "videoId": "7624922739500993822",
    "uniqueId": "steamed.bun.siste",
    "playCount": 2109422,
    "diggCount": 143027,
    "commentCount": 1320,
    "shareCount": 36150,
    "collectCount": 17710,
    "downloadCount": 0,
    "forwardCount": 0,
    "secUid": "MS4wLjAB...",
    "playAddr": "https://api16-normal-no1a.tiktokv.eu/...",
    "downloadAddr": "https://api16-normal-no1a.tiktokv.eu/...",
    "coverUrl": "https://p16-common-sign.tiktokcdn-eu.com/...",
    "videoDesc": "Fun, love to have fun#pet #Cute #dog ",
    "descLanguage": "en",
    "duration": 6758,
    "isEcVideo": null,
    "isAds": null,
    "musicId": null,
    "musicTitle": null,
    "region": null,
    "releaseAt": 1775315687
  },
  "timestamp": 1781491163414
}
```

### Field semantics

| Field | Meaning | Notes |
|-------|---------|-------|
| `videoId` | Per-video id. | The normalized script output maps this to `video.video_id`. |
| `uniqueId` | TikTok creator handle. | The normalized script output maps this to `video.username`. |
| `playCount` / `diggCount` / `commentCount` / `shareCount` / `collectCount` | Views, likes, comments, shares, saves. | Use these for real-time video metric refreshes. |
| `downloadCount` / `forwardCount` | Downloads and forwards. | May be `0` depending on upstream availability. |
| `secUid` | TikTok secure creator id. | |
| `playAddr` / `downloadAddr` | Direct video URLs. | Signed and short-lived; re-fetch when stale. |
| `coverUrl` | Cover image URL. | Signed and short-lived. |
| `videoDesc` | Caption. | Hashtags must be parsed from this string with a `#xxx` regex. |
| `descLanguage` | Caption language. | |
| `duration` | Video length. | **Milliseconds.** Divide by 1000 for seconds. |
| `releaseAt` | Publish time. | **Unix seconds, UTC.** |

## Fetch TikTok Material Comments

Endpoint: `POST /v1/material/tiktok/fetchComments`

Request body:

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `videoUrl` | yes | string | Public TikTok video URL. |

Response envelope: `{ code, message, data, timestamp }`.

### Success response shape

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "comments": [
      {
        "author_pin": false,
        "aweme_id": "7624922739500993822",
        "collect_stat": 0,
        "comment_language": "en",
        "create_time": 1779085557,
        "digg_count": 28,
        "is_author_digged": false,
        "no_show": false,
        "reply_comment": null,
        "reply_id": "0",
        "text": "That dog is so patient",
        "user": {
          "nickname": "Mama_Caye",
          "uid": "6904573909506688001",
          "unique_id": "mama_caye.v",
          "user_tags": null
        },
        "user_digged": 0
      }
    ]
  },
  "timestamp": 1781491112143
}
```

### Field semantics

`data.comments[]`:

| Field | Meaning |
|-------|---------|
| `aweme_id` | TikTok video id. |
| `text` | Comment text. |
| `comment_language` | Detected comment language. |
| `create_time` | Comment publish time, Unix seconds UTC. |
| `digg_count` | Comment like count. |
| `author_pin` | Whether the creator pinned the comment. |
| `is_author_digged` | Whether the creator liked the comment. |
| `reply_id` / `reply_comment` | Reply relationship fields from upstream. |
| `no_show` | Hidden / not shown flag. |
| `user.uid` / `user.unique_id` / `user.nickname` | Comment author fields. |
