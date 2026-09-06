# Lingtu Social Monitor API

## Shared Configuration

- Base URL: `https://api.ailingtu.com`
- Authentication header: `x-api-key: <api-key>`
- Do not commit API keys or private monitoring data.

## Platform Status

| Platform | Creator video list | Single video data |
|----------|--------------------|-------------------|
| TikTok | Implemented | Implemented |
| Instagram | Implemented | Implemented |

Before implementing a new platform endpoint, document its path, request fields, response envelope, field semantics, pagination, and error codes here first. Script output should normalize platform-specific responses into the shared shape used by `scripts/lingtu_social_monitor.py`.

## Shared Normalized Shape

Creator video-list commands should output:

```ts
interface NormalizedCreatorVideos {
  creator: {
    platform: "tiktok" | "instagram";
    creator_id: string;
    username: string;
    nickname: string;
    profile_url: string;
    signature?: string;
    follower_count?: number;
    following_count?: number;
    aweme_count?: number;
    total_favorited?: number;
  };
  videos: Array<{
    video_id: string;
    video_url: string;
    caption: string;
    publish_time: string | null; // ISO UTC
    duration: number;            // seconds
    is_ad?: boolean;
    views: number;
    likes: number;
    comments: number;
    shares: number;
    saves: number;
    cover_url: string;
    play_url?: string;
    hashtags: string[];
  }>;
  cursor?: string | number | null;
  has_more: boolean;
}
```

Single-video material commands should normalize to the same metric field names under `video`.

## Local Output Shapes (Digest / Alerts)

These are produced locally by the script (no remote API). Document them here so consumers do not have to read source.

`digest --format json` (and `build_digest()` return value):

```ts
interface DigestOutput {
  group_id: string;
  platform: "tiktok" | "instagram" | null;
  date: string;            // YYYY-MM-DD
  previous_date: string;   // YYYY-MM-DD (date - 1)
  summary: {
    monitors_total: number;
    fetched: number;
    missing: number;
    new_videos_total: number;
    with_yesterday: number;
  };
  highlights: {
    follower_gainers: Array<{ username, nickname, follower_delta, follower_today }>;
    new_viral: Array<{
      username; nickname; video_id; video_url; caption;
      views; likes; comments; cover_url; publish_time;
    }>;
    biggest_view_jumps: Array<{
      username; nickname; video_id; video_url; caption;
      views_today; views_yesterday; views_delta;
    }>;
    stalled: Array<{ username, nickname, days_since_last_post }>;
    surged: Array<{ username, nickname, last_7_days_posts }>;
  };
  creators: Array<{
    username; nickname; remark;
    follower_today; follower_delta; new_videos;
    top_today: { video_id, video_url, caption, views } | null;
    biggest_view_jump; status: "ok" | "stall" | "surge"; has_yesterday;
  }>;
  alerts: Alert[];
  missing: Array<{ username, nickname, remark }>;
  reply_text: string;      // localized digest body for chat reply
}

type Alert =
  | {
      type: "new_viral";
      severity: "high" | "medium";
      username: string;
      platform: string;
      video_id: string;
      video_url: string;
      caption: string;
      views: number;
      likes: number;
      cover_url: string;
      publish_time: string | null;
      triggered_at: number;          // unix ms
    }
  | {
      type: "stopped_posting";
      severity: "medium";
      username: string;
      platform: string;
      days_since_last_post: number;
      last_post_date: string;        // YYYY-MM-DD
      triggered_at: number;
    }
  | {
      type: "high_frequency";
      severity: "low";
      username: string;
      platform: string;
      posts_last_7_days: number;
      triggered_at: number;
    }
  | {
      type: "follower_drop";
      severity: "high" | "medium";
      username: string;
      platform: string;
      follower_delta: number;        // negative
      follower_today: number;
      triggered_at: number;
    };
```

Threshold constants live in `lib/config.py`: `VIRAL_VIEWS_HIGH=1_000_000` / `VIRAL_VIEWS_MEDIUM=100_000` / `FOLLOWER_DROP_HIGH=10_000` / `FOLLOWER_DROP_MEDIUM=1_000` / `STALL_DAYS=7` / `SURGE_WEEK_THRESHOLD=3`.

`alerts check` output:

```ts
interface AlertsCheckOutput {
  group_id: string;
  platform: string | null;
  date: string;
  username: string | null;       // null when scanning whole group
  alerts: Alert[];
}
```

`snapshot-get` output:

- Single day (`--date` or default today) → returns the snapshot JSON directly:
  ```ts
  interface CreatorSnapshot {
    captured_at: string;           // ISO UTC
    date: string;                  // YYYY-MM-DD
    group_id: string;
    creator: { ... };              // same shape as NormalizedCreatorVideos.creator
    videos: Array<{ ... }>;        // same shape as NormalizedCreatorVideos.videos
  }
  ```
- Range (`--from` / `--to`) → `{ group_id, platform, username, creator_id, from, to, snapshots: CreatorSnapshot[] }`.
- `--latest-only` → `{ group_id, platform, latest_only: true, creators: Array<{ platform, creator_id, latest_date, snapshot_count }> }`.

`monitors.json` entry shape (see `SKILL.md` § Monitor Metadata Schema for the full TypeScript definition).

## TikTok Fetch Recent Posts

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


## Instagram Fetch Recent Posts

Endpoint: `GET /v1/influencer/ins/fetchPosts`

Query parameters:

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `uniqueId` | yes | - | Instagram handle, i.e. the `xxx` in `https://www.instagram.com/xxx/`. |
| `count` | no | 40 | Number of recent posts to return. |

Response envelope: `{ code, message, data, timestamp }`.

### Success response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "author": {
      "id": "26669533",
      "username": "neymarjr",
      "fullName": null,
      "biography": "@santosfc & Brazil 🇧🇷 10",
      "edgeFollowedBy": null,
      "edgeFollow": null,
      "edgeOwnerToTimelineMedia": null,
      "isPrivate": null,
      "isVerified": null
    },
    "posts": [
      {
        "postId": "3921102472295741720",
        "shortCode": "DZqjex1F_kY",
        "displayUrl": "https://...",
        "thumbnailSrc": "https://...",
        "isVideo": false,
        "videoUrl": null,
        "videoViewCount": null,
        "videoPlayCount": null,
        "videoDuration": null,
        "caption": "Renovando energias ♥️",
        "likeCount": null,
        "commentCount": 95,
        "takenAtTimestamp": 1781651861
      }
    ],
    "endCursor": "QVFD...",
    "hasMore": true
  },
  "timestamp": 1781750400000
}
```

### Field semantics

`author`:

| Field | Maps to | Notes |
|-------|---------|-------|
| `id` | `creator.creator_id` | Stable Instagram user id. |
| `username` | `creator.username` | Profile handle. |
| `fullName` | `creator.nickname` | May be `null`; falls back to `username`. |
| `biography` | `creator.signature` | |
| `edgeFollowedBy` / `edgeFollow` / `edgeOwnerToTimelineMedia` | `follower_count` / `following_count` / `aweme_count` | Legacy edge counters; each is either `null`, a number/string, or an object with a `count` field. |
| `followerCount` / `followersCount` / `followers` / `follower_count` | `follower_count` | Direct follower counter variants. Prefer the first non-null value. |
| `followingCount` / `followCount` / `following` / `following_count` | `following_count` | Direct following counter variants. Prefer the first non-null value. |
| `postCount` / `postsCount` / `mediaCount` / `awemeCount` / `aweme_count` | `aweme_count` | Direct post/media counter variants. Prefer the first non-null value. |

`posts[]`:

| Field | Maps to | Notes |
|-------|---------|-------|
| `postId` | `video.video_id` | |
| `shortCode` | — | Used to build `https://www.instagram.com/p/{shortCode}/`. |
| `caption` | `video.caption` | Hashtags parsed via regex. |
| `takenAtTimestamp` | `video.publish_time` | Unix seconds, UTC. |
| `videoDuration` | `video.duration` | Seconds (already in seconds, not ms). `null` for non-video posts. |
| `isVideo` | `video.is_video` | |
| `videoPlayCount` / `videoViewCount` | `video.views` | Only present on video posts; `null` on photo/carousel posts. |
| `likeCount` | `video.likes` | Often `null` in this list endpoint; use `material` for accurate per-video metrics. |
| `commentCount` | `video.comments` | |
| `displayUrl` / `thumbnailSrc` | `video.cover_url` | |
| `videoUrl` | `video.play_url` | Signed and short-lived; `null` on non-video posts. |

`endCursor` / `hasMore` drive pagination. `endCursor` is a base64 string passed back unchanged.

> The list endpoint returns sparse metrics on Instagram. `likeCount` and view counters are routinely `null`; rely on `POST /v1/material/ins/fetch` for any per-video metric refresh or virality analysis.

## Instagram Fetch Material

Endpoint: `POST /v1/material/ins/fetch`

Request body:

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `videoUrl` | yes | string | Public Instagram reel/post/video URL. |

Response envelope: `{ code, message, data, timestamp }`.

### Success response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "postId": "3909950218073505565",
    "shortCode": "DZC7wHtu38d",
    "displayUrl": "https://...",
    "thumbnailSrc": "https://...",
    "isVideo": true,
    "videoUrl": "https://...mp4",
    "videoViewCount": 14976543,
    "videoPlayCount": 46653732,
    "videoDuration": 66.965,
    "caption": "link up play at 15m high 🤝 ... #redbull #football",
    "likeCount": 1874906,
    "commentCount": 8752,
    "takenAtTimestamp": 1780322411,
    "owner": {
      "id": "476322",
      "username": "redbull",
      "fullName": "Red Bull",
      "isVerified": true
    },
    "musicInfo": {
      "artistName": "redbull",
      "songName": "Original audio",
      "audioId": "27057480790573274",
      "usesOriginalAudio": true
    },
    "comments": [ /* preview list */ ]
  },
  "timestamp": 1781771400583
}
```

### Field semantics

| Field | Maps to | Notes |
|-------|---------|-------|
| `postId` | `video.video_id` | |
| `shortCode` | — | Used to rebuild the canonical `https://www.instagram.com/p/{shortCode}/`. |
| `caption` | `video.caption` | Hashtags parsed via regex. |
| `takenAtTimestamp` | `video.publish_time` | Unix seconds, UTC. |
| `videoDuration` | `video.duration` | Seconds. |
| `videoPlayCount` / `videoViewCount` | `video.views` | Prefer `videoPlayCount` when both present. |
| `likeCount` | `video.likes` | |
| `commentCount` | `video.comments` | |
| `displayUrl` / `thumbnailSrc` | `video.cover_url` | |
| `videoUrl` | `video.play_url` | Signed and short-lived. |
| `owner.username` | `video.username` | |
| `musicInfo.audioId` / `musicInfo.songName` | `video.music_id` / `video.music_title` | |

`shares`, `saves`, `downloads`, `forwards` are not exposed by Instagram — the normalized output sets them to `0` for shape compatibility with TikTok.
