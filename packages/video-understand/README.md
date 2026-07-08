# Video Understand

Video Understand turns a video into a natural-language replication prompt. The output is a Markdown-style brief (title, subjects, scene, scripted shots, production notes) that can feed downstream video generation or be used as a tagging/understanding source.

Current package version: `0.6.0`. Remote installers can compare the `version` field in [`SKILL.md`](./SKILL.md) frontmatter to decide whether an installed copy needs updating.

## What It Does

- Accepts a public TikTok, YouTube, or Instagram URL, a local video file path, or a Lingtu material/file reference (`businessId` + `businessType`).
- Local files are uploaded through `POST /v1/file/upload` (multipart form field `file`); the returned `data.id` is reused as `businessId` with `businessType: "FILE"`.
- Streams a replication prompt from `POST /v1/material/analysisTask/stream` (`type: "REPLICATION"`).
- Prints the assembled prompt to stdout, or raw SSE lines with `--raw` for debugging.
- For TikTok/Instagram video analysis that needs real-time metrics or comment context, fetch those first with `packages/social-monitor` `material` / `comments`, then combine them with this replication prompt.

This skill currently only sends `type: "REPLICATION"`. The `ANALYSIS` mode is reserved.

## Requirements

Authentication uses the `LINGTU_API_KEY` environment variable. OpenClaw injects it automatically. For standalone CLI use:

```bash
export LINGTU_API_KEY=xxx
```

If you don't have an API key yet, generate a `/binduser` URL:

```bash
python3 ../../shared/scripts/user_keys.py single bind
```

Open the returned link, complete the binding on the website, then set `LINGTU_API_KEY`. The key is sent as `x-api-key: <key>`. Do not commit API keys.

## Script Usage

Parse a TikTok, YouTube, or Instagram URL:

```bash
python3 scripts/lingtu_video_understand.py replicate --url "https://www.tiktok.com/@user/video/1234567890"
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
cat urls.txt | xargs -I{} -P 5 \
  python3 scripts/lingtu_video_understand.py replicate --url "{}"
```

## API Reference

Read [`references/api.md`](./references/api.md) before changing endpoint paths, request fields, response fields, or streaming parsing.
