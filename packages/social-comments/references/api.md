# Lingtu Social Comments API

## Shared configuration

- Base URL: `https://api.ailingtu.com`
- Authentication: `x-api-key: <LINGTU_API_KEY>`
- Content type: `application/json`

All endpoints use `POST` and return `{ code, message, data, timestamp }`. Treat only `code == 0` with an object `data` value as success.

Treat every `cursor` as an opaque string: omit it or send `null` on the first request, then return the response cursor exactly as received. Do not decode, parse, escape, or rebuild it.

## TikTok comments

```http
POST /v1/material/tiktok/fetchComments
```

```ts
export interface Request {
  /** First request: omit or null. Later requests: return the cursor unchanged. */
  cursor?: string | null;
  videoUrl: string;
}
```

## Instagram comments

```http
POST /v1/material/ins/fetchComments
```

```ts
export interface Request {
  /** First request: omit. Later requests: return the cursor unchanged. */
  cursor?: string;
  /** popular = popular comments (default); newest = latest comments. */
  sortOrder: "popular" | "newest";
  videoUrl: string;
}
```

## Douyin comments

```http
POST /v1/material/douyin/fetchComments
```

```ts
export interface Request {
  /** First request: omit or null. Later requests: return the cursor unchanged. */
  cursor?: string | null;
  videoUrl: string;
}
```

## WeChat Channels comments

```http
POST /v1/material/wechatChannel/fetchComments
```

```ts
export interface Request {
  cursor?: string;
  videoUrl: string;
}
```

## Xiaohongshu comments

```http
POST /v1/material/xhs/fetchComments
```

```ts
export interface Request {
  cursor?: string;
  videoUrl: string;
}
```

## Response and pagination

The downloader expects comments under `data.comments`, the next cursor under `data.cursor` (or top-level `cursor` for compatibility), and the continuation flag under `data.hasMore` (or top-level `hasMore`). If `hasMore` is absent, a non-empty new cursor indicates another page.

Pagination stops on `hasMore == false`, an empty or repeated cursor, `--first-page`, `--max-pages`, or `--max-comments`. The aggregated data includes `pages`, `duplicateCount`, and `stoppedReason`. By default, comment IDs are deduplicated across pages, successful page requests are spaced by 500ms, and HTTP 429/5xx plus network errors are retried twice with exponential backoff. Cursors remain byte-for-byte opaque throughout retries and pagination.

`--max-comments` limits saved comments, not the number fetched from the API: the final API page is fetched in full and the aggregate is then truncated. Its returned cursor points after that complete page, so resuming from it can skip comments removed by the truncation. Use `--max-pages` or an explicit cursor workflow when lossless continuation matters.

TikTok currently exposes fields such as `aweme_id`, `text`, `comment_language`, `create_time`, `digg_count`, pin/creator-like flags, reply fields, and `user`.

Instagram currently exposes fields such as `text`, `createdAt`, `createdAtUtc`, `commentLikeCount`, `childCommentCount`, `previewChildComments`, `isLikedByMediaOwner`, and `user`.

Observed Douyin responses expose camel-case fields such as `cid`, `awemeId`, `text`, `createTime`, `diggCount`, `replyId`, `replyToReplyId`, `replyCommentTotal`, `isAuthorDigged`, `isHot`, `isFolded`, `ipLabel`, `contentType`, `imageList`, and nested `user` fields. These are mapped into common normalized fields.

Observed WeChat Channels responses expose `commentId`, `nickname`, `username`, `content`, `likeCount`, `replyCount`, `createTime`, `headUrl`, and `ipRegion`. These are also mapped into common normalized fields.

Observed Xiaohongshu responses expose `id`, `noteId`, `content`, `time`, `likeCount`, `liked`, `hidden`, `invalid`, `ipLocation`, `commentType`, `subCommentCount`, `subCommentCursor`, `subComments`, and nested `user` fields including `userid`, `nickname`, `redId`, and `images`. Its normalizer also accepts common camel-case and snake-case variants.

Xiaohongshu, Douyin, and WeChat Channels records retain every source record under `comment.raw` so newly added source fields are not lost. Use `--raw` to retain the complete aggregated response envelope.

## Normalized output

```json
{
  "platform": "tiktok",
  "video_url": "...",
  "comments": [],
  "summary": {
    "comment_count": 0,
    "page_count": 0,
    "next_cursor": null,
    "has_more": false,
    "duplicate_count": 0,
    "stopped_reason": "no_more",
    "top_languages": [],
    "top_liked_comments": []
  },
  "timestamp": null
}
```

Each normalized comment contains common text, time, likes, creator-interaction, reply, and author fields when the source provides them.
