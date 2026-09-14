---
name: lingtu-video-understand
slug: lingtu-video-understand
version: 0.9.0
auth: lingtu-api-key
displayName: 灵途视频拆解分析
summary: 分析多平台视频，生成脚本结构、卖点和复刻提示词。
description: 视频理解、内容分析与复刻提示词生成。用户要分析、总结、打标、拆解视频或只提取复刻提示词时使用。支持本地文件、已上传素材和 TikTok/抖音/小红书/视频号/YouTube/Instagram 链接，返回自然语言脚本结构并按问题解读。参考视频结构生成新视频时使用 lingtu-content-create；爆款复刻（分段重绘与合成）使用 lingtu-video-remake。处理时只调用脚本，不抓视频网页或搜索引擎快照；批量并发上限为10。
license: Apache-2.0
homepage: https://ailingtu.com/skills/video-understand
---

# 视频理解与复刻提示词生成

## Installation and upgrades

Follow https://ailingtu.com/install/skills.md. Do not install or upgrade this Skill from GitHub.

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

All authenticated requests use only `LINGTU_API_KEY` and send it as `x-api-key`.
Installation does not require authentication. If `LINGTU_API_KEY` is missing when
running a task, ask the user to create or manage a key at https://ailingtu.com/api-keys
and configure `LINGTU_API_KEY` in the environment running the Skill before retrying.
Never ask for, display, or store their API key in chat. Do not generate account-binding URLs.

缺少密钥时，读取 `shared/references/api-key-setup.md`，向用户展示其操作系统对应的完整步骤（如何打开终端、可复制命令、粘贴密钥、重启应用及生效范围），不要只说“配置环境变量”。已知系统时只展示对应部分；未知时同时提供 Mac 和 Windows。配置由用户在自己电脑上完成，不代为读取或填入真实密钥。

Use `https://api.ailingtu.com` as the default base URL unless a future API reference specifies another host.

The independently installed package includes `shared/scripts`, so authentication,
HTTP and upload behavior use the same runtime as the other Lingtu Skills.

## Do Not

- **Do not** call WebFetch / WebSearch / `curl` against the user-provided video URL (TikTok / Douyin / Xiaohongshu / WeChat Channels / YouTube / Instagram / etc.) to pull web snapshots, search-engine cached pages, OG meta, or third-party metadata sites. The replication endpoint already ingests the source video; adding a web lookup just adds latency and is the wrong data path.
- Exception: only fetch external pages when the user explicitly asks ("先去搜一下这个视频的背景再分析" / "go look up the background first").

## Interpreting the output

The replication prompt is a model-generated description, not verified footage or a verbatim transcript. Answer the user's question using it, distinguish the returned description from your own inference, and do not invent missing information. Generated dialogue and timestamps must not be presented as confirmed original speech or frame-accurate timing. If details are absent or uncertain, say so. Stream validation checks transport and content shape; it does not verify factual accuracy or completeness of the generated description.

- If the user asks "这个视频讲了什么 / 在讲什么 / 内容是什么 / 在干嘛"，用 2–4 句中文概括已有信息（主体、场景、钩子、结尾）；不强行补齐不存在的卖点或 CTA。默认不附完整英文提示词，用户需要时再提供。
- 用户要求详细拆解时，按“内容概述、钩子、分镜与节奏、卖点与 CTA、可借鉴做法、不确定信息”组织已有信息；没有依据的部分省略或注明未知。“为什么爆”只能提出假设，结合实际指标和评论再判断。
- If the user asks for tags / 关键词 / 选题归类，从提示词里提取并整理。
- If the user asks "怎么二创 / 怎么改成我的版本"，基于提示词给改写建议；需要生成改编视频时使用 `lingtu-content-create`。
- If the user only说"给我复刻提示词 / 给我提示词"，那就原样返回提示词，不需要总结。
- 默认语言跟随用户：用户用中文提问就用中文解读，提示词原文（通常英文）保留不翻译。

## Workflow

1. Decide the input shape.
   - If the user provides a TikTok, Douyin, Xiaohongshu, WeChat Channels, YouTube, or Instagram URL, send `{ type: "REPLICATION", url }`. Accept full share links and short links (e.g. `v.douyin.com`, `www.douyin.com`, `xhslink.com`, `www.xiaohongshu.com`, `channels.weixin.qq.com`).
   - If the user provides a local video file path, upload it first through `POST /v1/file/upload` (form field `file`), then send `{ type: "REPLICATION", businessId: <data.id>, businessType: "FILE" }`.
   - If the user references an already-uploaded material/file, send `{ type: "REPLICATION", businessId, businessType }` where `businessType` is `MATERIAL` or `FILE`.
2. Always send `type: "REPLICATION"` for now. The `ANALYSIS` mode is reserved and not used by this skill.
3. Use the script to validate SSE data and concatenate streaming results. A non-zero exit means the result is unusable; do not interpret raw diagnostic fragments as a completed analysis.
4. Echo the source (URL, local path, or business id) so the data origin is clear, then respond to the user's actual question per the *Interpreting the output* rules — summarize when they asked "讲了什么", extract tags when they asked for tagging, return the prompt as-is when they asked for "复刻提示词 / 给我提示词".
5. Downstream usage:
   - For 二创/参考结构生成, use `lingtu-content-create` with the existing analysis brief; do not repeat completed analysis. For 爆款复刻, use `lingtu-video-remake` for timestamped transcription, semantic cuts, per-segment redrawing and approval, then merging; a structure brief does not replace timestamped transcription.
   - For 打标/检索, keep the prompt as-is or extract tags from it.
   - For “结合数据分析这个 TikTok/Instagram 视频” / “为什么爆”, call `lingtu-social-monitor material` for real-time metrics. For “看评论区反馈”, call `lingtu-social-comments download` on TikTok, Instagram, Douyin, WeChat Channels, or Xiaohongshu. Then combine those results with this skill's replication prompt.

## Batch / Concurrency Limit

Do **not** fan out unbounded parallel calls. Each replication holds an SSE connection until generation finishes (tens of seconds), and uploads consume bandwidth.

- **Hard cap: at most 10 concurrent in-flight `replicate` (or `upload`) invocations**, regardless of input shape (URL, local file, or business id).
- For batch jobs of >10 items, run a worker pool with concurrency ≤ 10 and queue the rest. Default to a smaller pool (3–5) when the user has not asked for "as fast as possible" — it is gentler on the server and on the user's bandwidth.
- Do not retry tighter than once every few seconds on transient failures; if the server returns 429 / 5xx, back off before resuming.
- When the user pastes a long list of videos, confirm the batch size with them before kicking off, and surface progress (e.g. "12 / 100 done") rather than running silently.

Use the built-in batch command (default concurrency: 3):

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
