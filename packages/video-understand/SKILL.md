---
name: lingtu-video-understand
slug: lingtu-video-understand
version: 0.8.1
displayName: 灵途视频拆解分析
summary: 分析多平台视频，生成脚本结构、卖点和复刻提示词。
description: 视频理解、视频内容分析与复刻提示词生成。任何关于"一个视频/一条视频/这个视频/这条 TikTok/这条抖音/这条 Douyin/这条小红书/这条视频号/这条 YouTube/这条 Instagram"的内容性问题——包括"分析这个视频"、"这个视频讲了什么/在讲什么/在干嘛"、"这条视频内容是什么"、"看一下这个视频"、"理解视频"、"视频拆解"、"视频复刻"、"爆款复刻"、"视频打标"、"把视频改写成提示词"、"二创这个视频"——都用本技能。把一个本地视频文件、已上传的素材，或一个 TikTok/抖音/小红书/视频号/YouTube/Instagram 链接交给灵途 AI 解析，流式返回一段自然语言的视频复刻提示词（标题、主体、场景、分镜脚本、制作笔记）；再根据用户的问题在该提示词之上做相应解读（概括/打标/二创建议），用户只要"复刻提示词"时则原样返回。本地文件会先经 /v1/file/upload 上传再复刻。批量任务并发上限为 10。处理时只调脚本，不抓视频链接的网页/搜索引擎快照。
license: Apache-2.0
homepage: https://ailingtu.com/skills/video-understand
---

# 视频理解与复刻提示词生成

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Overview

Use this skill to turn a video into a natural-language replication prompt.

Supported inputs:

- A public TikTok, Douyin (抖音), Xiaohongshu (小红书), WeChat Channels (视频号), YouTube, or Instagram URL.
- A local video file (the script uploads it through `/v1/file/upload` first, then replicates by file id).
- A material/file already uploaded to Lingtu, referenced by `businessId` + `businessType`.

Supported API flows:

- File upload: `POST /v1/file/upload`, multipart/form-data with form field `file`.
- Replication prompt: `POST /v1/material/analysisTask/stream`, server-sent events.

Read `references/api.md` before changing endpoint paths, request fields, response fields, or streaming parsing. Use `scripts/lingtu_video_understand.py` for deterministic calls.

## Configuration

Authentication uses the `LINGTU_API_KEY` environment variable. When it is missing, give the user the command for their operating system and ask them to run it locally. Do not ask them to paste the real key into chat.

macOS (current Terminal session):

```bash
export LINGTU_API_KEY='your-api-key'
```

For persistent macOS configuration, add the same line to `~/.zshrc`, then run `source ~/.zshrc`.

Windows PowerShell (current session):

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

For persistent Windows configuration, run `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")`, then open a new terminal.

The key is sent as the `x-api-key` header. Do not commit API keys.

Use `https://api.ailingtu.com` as the default base URL unless a future API reference specifies another host.

The package is self-contained when installed as a single skill directory. In a full
repository installation it reuses `shared/scripts`; otherwise it automatically
falls back to the bundled `scripts/lingtu_standalone.py` runtime.

## Do Not

- **Do not** call WebFetch / WebSearch / `curl` against the user-provided video URL (TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram / etc.) to pull web snapshots, search-engine cached pages, OG meta, or third-party metadata sites. The replication endpoint already ingests the source video; adding a web lookup just adds latency and is the wrong data path.
- Exception: only fetch external pages when the user explicitly asks ("先去搜一下这个视频的背景再分析" / "go look up the background first").

## Interpreting the output

The replication prompt the script returns is the source of truth for what's in the video. Read it and answer the user's actual question on top of it — do not just dump the raw English prompt and walk away.

- If the user asks "这个视频讲了什么 / 在讲什么 / 内容是什么 / 在干嘛"，先用 2–4 句中文概括（主体、场景、卖点/钩子、结尾 CTA），再附完整复刻提示词供他们查证。
- If the user asks for tags / 关键词 / 选题归类，从提示词里提取并整理。
- If the user asks "怎么二创 / 怎么改成我的版本"，基于提示词给改写建议或交给 `lingtu-content-create`。
- If the user only说"帮我复刻这个视频 / 给我提示词"，那就原样返回提示词，不需要总结。
- 默认语言跟随用户：用户用中文提问就用中文解读，提示词原文（通常英文）保留不翻译。

## Workflow

1. Decide the input shape.
   - If the user provides a TikTok, Douyin, Xiaohongshu, WeChat Channels, YouTube, or Instagram URL, send `{ type: "REPLICATION", url }`. Accept full share links and short links (e.g. `v.douyin.com`, `www.douyin.com`, `xhslink.com`, `www.xiaohongshu.com`, `channels.weixin.qq.com`).
   - If the user provides a local video file path, upload it first through `POST /v1/file/upload` (form field `file`), then send `{ type: "REPLICATION", businessId: <data.id>, businessType: "FILE" }`.
   - If the user references an already-uploaded material/file, send `{ type: "REPLICATION", businessId, businessType }` where `businessType` is `MATERIAL` or `FILE`.
2. Always send `type: "REPLICATION"` for now. The `ANALYSIS` mode is reserved and not used by this skill.
3. Stream the response. Concatenate every `data:` line's `result` field in order to assemble the final prompt.
4. Echo the source (URL, local path, or business id) so the data origin is clear, then respond to the user's actual question per the *Interpreting the output* rules — summarize when they asked "讲了什么", extract tags when they asked for tagging, return the prompt as-is when they asked for "复刻 / 给我提示词".
5. Downstream usage:
   - For 二创/生成/爆款复刻, hand the prompt to `lingtu-content-create` (see `packages/content-create/references/viral-remake-workflow.md`).
   - For 打标/检索, keep the prompt as-is or extract tags from it.
   - For “结合数据分析这个 TikTok/Instagram 视频” / “为什么爆”, call `lingtu-social-monitor material` for real-time metrics. For “看评论区反馈”, call `lingtu-social-comments download` on TikTok, Instagram, Douyin, WeChat Channels, or Xiaohongshu. Then combine those results with this skill's replication prompt.

## Batch / Concurrency Limit

Do **not** fan out unbounded parallel calls. Each replication holds an SSE connection until generation finishes (tens of seconds), and uploads consume bandwidth.

- **Hard cap: at most 10 concurrent in-flight `replicate` (or `upload`) invocations**, regardless of input shape (URL, local file, or business id).
- For batch jobs of >10 items, run a worker pool with concurrency ≤ 10 and queue the rest. Default to a smaller pool (3–5) when the user has not asked for "as fast as possible" — it is gentler on the server and on the user's bandwidth.
- Do not retry tighter than once every few seconds on transient failures; if the server returns 429 / 5xx, back off before resuming.
- When the user pastes a long list of videos, confirm the batch size with them before kicking off, and surface progress (e.g. "12 / 100 done") rather than running silently.

Recommended shell pattern for ad-hoc batches (caps concurrency at 5):

```bash
cat urls.txt | xargs -I{} -P 5 \
  python3 scripts/lingtu_video_understand.py replicate --url "{}"
```

## Script Usage

Parse a supported public video URL (TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram):

```bash
python3 scripts/lingtu_video_understand.py replicate --url "https://www.tiktok.com/@user/video/1234567890"
# Douyin example:
python3 scripts/lingtu_video_understand.py replicate --url "https://www.douyin.com/video/7123456789012345678"
# Xiaohongshu example:
python3 scripts/lingtu_video_understand.py replicate --url "https://www.xiaohongshu.com/explore/64abcdef0123456789abcdef"
# WeChat Channels example:
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

Upload only (returns the file id and CDN url, no replication):

```bash
python3 scripts/lingtu_video_understand.py upload ./clip.mp4
```

Print the raw stream (for debugging):

```bash
python3 scripts/lingtu_video_understand.py replicate --url "..." --raw
```
