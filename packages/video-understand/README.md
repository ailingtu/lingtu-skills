# Video Understand

Video Understand turns a video into a natural-language replication prompt. The output is a Markdown-style brief (title, subjects, scene, scripted shots, production notes) that can feed downstream video generation or be used as a tagging/understanding source.

Current package version: `0.9.1`. Remote installers can compare the `version` field in [`SKILL.md`](./SKILL.md) frontmatter to decide whether an installed copy needs updating.

## What It Does

- Accepts a public TikTok, Douyin (抖音), Xiaohongshu (小红书), WeChat Channels (视频号), YouTube, or Instagram URL, a local video file path, or a Lingtu material/file reference (`businessId` + `businessType`).
- Local files are uploaded through the presign flow (`POST /v1/file/presign` → `PUT` to `data.uploadUrl` → `POST /v1/file/confirm`); the returned `data.fileId` is reused as `businessId` with `businessType: "FILE"`.
- Streams a replication prompt from `POST /v1/material/analysisTask/stream` (`type: "REPLICATION"`).
- Validates the stream, then prints the assembled prompt; `--json` includes source and task id. `--raw` prints diagnostic SSE lines and still reports validation failures.
- For TikTok/Instagram video analysis, fetch real-time metrics with `packages/social-monitor`. Fetch comment context for TikTok, Instagram, Douyin, WeChat Channels, or Xiaohongshu with `packages/social-comments`, then combine it with this replication prompt.

This skill currently only sends `type: "REPLICATION"`. The `ANALYSIS` mode is reserved.

## Requirements

All authenticated requests use only the `LINGTU_API_KEY` environment variable and send it as `x-api-key`. If it is missing, ask the user to create or manage a key at https://ailingtu.com/api-keys and configure `LINGTU_API_KEY` in the environment running the Skill before retrying. Never paste the key into chat or commit it.

The independently installed package includes `shared/scripts`, so authentication,
HTTP and upload behavior use the same runtime as the other Lingtu Skills.

## Script Usage

Parse a supported public video URL (TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram):

```bash
python3 scripts/lingtu_video_understand.py replicate --url "https://www.tiktok.com/@user/video/1234567890"
python3 scripts/lingtu_video_understand.py replicate --url "https://www.douyin.com/video/7123456789012345678"
python3 scripts/lingtu_video_understand.py replicate --url "https://www.xiaohongshu.com/explore/64abcdef0123456789abcdef"
python3 scripts/lingtu_video_understand.py replicate --url "https://channels.weixin.qq.com/web/pages/feed?eid=..."
```

Parse a local video file (auto-upload + replicate):

```bash
python3 scripts/lingtu_video_understand.py replicate --file ./clip.mp4
```

Parse an uploaded material/file:

```bash
python3 scripts/lingtu_video_understand.py replicate --business-id 123456 --business-type MATERIAL
```

Upload only:

```bash
python3 scripts/lingtu_video_understand.py upload ./clip.mp4
```

Print the raw SSE stream:

```bash
python3 scripts/lingtu_video_understand.py replicate --url "..." --raw
```

## Batching

Each replication holds a streaming connection for tens of seconds, so do not fan out unbounded parallel calls. Cap concurrency at **10** at most; use 3–5 for routine batches.

```bash
python3 scripts/lingtu_video_understand.py batch --urls urls.txt --output-dir results --workers 3
# Retry failed items while preserving successful results:
python3 scripts/lingtu_video_understand.py batch --urls urls.txt --output-dir results --workers 3 --resume
```

`urls.txt` contains one URL per line. Duplicate URLs are deduplicated. Each URL gets
its own JSON file (source, status, task id and prompt on success, or error on failure).
Progress goes to stderr; stdout contains the batch summary. Any failed item makes
the command exit non-zero. Workers must be 1–10. No automatic request retry is performed;
after a transient failure, wait a few seconds before explicitly resuming.

For a single input, use `replicate --url "..." --json` for structured output.
`--json` and `--raw` are mutually exclusive. `--timeout 300` sets the socket timeout,
not a total task deadline. Normal text/JSON is emitted only after stream validation;
`--raw` is diagnostic and may contain incomplete or failed output.

## API Reference

Read [`references/api.md`](./references/api.md) before changing endpoint paths, request fields, response fields, or streaming parsing.
