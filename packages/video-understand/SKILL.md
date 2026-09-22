---
name: lingtu-video-understand
slug: lingtu-video-understand
version: 0.9.4
auth: lingtu-api-key
displayName: "AI 视频拆解与复刻提示词 By 灵途 AI"
summary: 分析多平台视频，生成脚本结构、卖点和复刻提示词。
description: "视频理解、内容分析与复刻提示词生成。用户要分析、总结、打标、拆解视频或只提取复刻提示词时使用。支持本地文件、已上传素材和 TikTok/抖音/小红书/视频号/YouTube/Instagram 链接，返回自然语言脚本结构并按问题解读。参考视频结构生成新视频时使用 lingtu-content-create；爆款复刻（分段重绘与合成）使用 lingtu-video-remake。处理时只调用脚本，不抓视频网页或搜索引擎快照；批量并发上限为10。 也用于“更新灵途 Skills”“升级灵途技能”或更新指定灵途技能。"
license: Apache-2.0
homepage: https://ailingtu.com/skills/video-understand
---

# AI 视频拆解与复刻提示词 By 灵途 AI

## 更新灵途 Skills

用户说“更新灵途 Skills”“更新灵途的 skills”“升级灵途技能”或要求更新某个灵途技能时，优先执行此流程，不启动本技能的业务任务。无需 API Key；无需先安装其他技能。只需由一个已加载的灵途技能统一处理，避免多个技能重复更新。

1. 读取 https://ailingtu.com/install/skills.md 和实时索引 https://cdn.ailingtu.cn/skills/packages/index.json 。更新所有技能时，在当前 Agent 实际启用的用户级与项目级 Skills 目录中查找已安装的灵途技能；指定技能时只处理匹配项。不扫描其他应用，不安装尚未安装的技能。
2. 用本地 SKILL.md 的 name/slug 精确匹配索引，按 SemVer 比较 version（数字比较，不按字符串排序）。同版跳过，本地更高版本保留，不自动降级；版本缺失、格式不明或索引无匹配时单独报告，不猜测下载地址。重复目录解析真实路径去重；确有多个启用副本时逐个报告路径并更新。忽略备份目录。
3. 对有新版的技能逐包下载，核对索引 SHA-256、大小及包内 name/version，验证 ZIP 路径不越界且不含符号链接，再在暂存目录解压。备份旧目录到 Agent 不会扫描的目录，保留用户配置和任务输出，然后完整替换包文件，避免覆盖解压留下旧脚本。失败恢复原目录，其余包可继续；不读取或修改密钥。
4. 汇报各包旧版→新版、已是最新、跳过或失败原因、实际安装与备份位置。宿主不支持热加载时提示重启。官方文档或索引不可访问时明确说明，保留本地版本。

用户已明确要求更新时直接执行；仅在路径歧义无法自行确定或宿主权限要求时再询问。不要将本次更新请求理解为自动定时更新或发布授权。

## 安装与升级

按照 https://ailingtu.com/install/skills.md 安装和升级，不要从源码仓库安装。

## 能力介绍

将视频解析为自然语言复刻提示词，用于内容理解、打标和后续视频生成。

支持的输入：

- TikTok、抖音、小红书、视频号、YouTube 或 Instagram 的公开视频链接。
- 本地视频文件（脚本先通过 `/v1/file/upload` 上传，再根据文件 ID 生成复刻提示词）。
- 已上传至灵途的素材或文件，通过 `businessId` + `businessType` 引用。

支持的接口流程：

- 文件上传：`POST /v1/file/upload`，使用 `multipart/form-data`，表单字段为 `file`。
- 复刻提示词：`POST /v1/material/analysisTask/stream`，通过服务器发送事件返回。

修改接口路径、请求字段、响应字段或处理逻辑前，先阅读 `references/api.md`。通过 `scripts/lingtu_video_understand.py` 执行调用。

## 配置

所有认证请求只读取 `LINGTU_API_KEY`，并通过 `x-api-key` 请求头发送。
安装技能不需要认证。执行任务时缺少密钥，引导用户前往 https://ailingtu.com/api-keys
创建或管理密钥，在运行技能的环境中配置 `LINGTU_API_KEY` 后重试。
不要索取、展示或保存用户密钥，不要生成账号绑定链接。

缺少密钥时，读取 `shared/references/api-key-setup.md`，向用户展示其操作系统对应的完整步骤（如何打开终端、可复制命令、粘贴密钥、重启应用及生效范围），不要只说“配置环境变量”。已知系统时只展示对应部分；未知时同时提供 Mac 和 Windows。配置由用户在自己电脑上完成，不代为读取或填入真实密钥。

默认接口地址为 `https://api.ailingtu.com`，后续接口文档明确指定其他地址时以文档为准。

独立安装包内置 `shared/scripts`，认证、HTTP 请求和上传与其他灵途技能使用相同的运行时。

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
# 保留成功结果，仅重试失败项：
python3 scripts/lingtu_video_understand.py batch --urls urls.txt --output-dir results --workers 3 --resume
```

`urls.txt` 每行一个链接，重复链接会自动去重。每个链接生成独立的 JSON 文件，
包含来源、状态、任务 ID 和成功时的提示词，失败时记录错误。
进度输出到标准错误，批量汇总输出到标准输出。存在失败项时命令返回非零退出码。
并发数必须为 1–10，不自动重试请求；临时失败后等待数秒再显式恢复。

单个输入可通过 `replicate --url "..." --json` 获取结构化输出。
`--json` 与 `--raw` 不能同时使用。`--timeout 300` 设置套接字超时时间，而非任务总时限。
正常文本或 JSON 仅在流式校验通过后输出；`--raw` 用于诊断，可能包含不完整或失败内容。

## 脚本用法

解析支持平台的公开视频链接（TikTok、抖音、小红书、视频号、YouTube、Instagram）：

```bash
python3 scripts/lingtu_video_understand.py replicate --url "https://www.tiktok.com/@user/video/1234567890"
# Douyin example:
python3 scripts/lingtu_video_understand.py replicate --url "https://www.douyin.com/video/7123456789012345678"
# Xiaohongshu example:
python3 scripts/lingtu_video_understand.py replicate --url "https://www.xiaohongshu.com/explore/64abcdef0123456789abcdef"
# WeChat Channels example:
python3 scripts/lingtu_video_understand.py replicate --url "https://channels.weixin.qq.com/web/pages/feed?eid=..."
```

解析本地视频文件（自动上传并生成复刻提示词）：

```bash
python3 scripts/lingtu_video_understand.py replicate --file ./clip.mp4
```

解析已上传的素材或文件：

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
