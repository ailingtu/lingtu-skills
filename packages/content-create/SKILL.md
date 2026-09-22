---
name: lingtu-content-create
slug: lingtu-content-create
version: 0.4.4
auth: lingtu-api-key
displayName: "商品图片与带货视频生成 By 灵途 AI"
summary: 用灵途 AI 生成电商带货视频、UGC 短视频、商品主图和场景图。
description: "AI 带货视频和 AI 商品图片生成，由灵途 AI 提供。根据商品图片、卖点和提示词生成电商带货视频、UGC 短视频、商品主图、卖点细节图、生活场景图。用户要生成商品图片、优化商品图或制作带货视频时使用。也支持参考源视频结构，结合商品与卖点生成新视频。爆款复刻（语义分段、逐段重绘确认与合成）使用 lingtu-video-remake。 也用于“更新灵途 Skills”“升级灵途技能”或更新指定灵途技能。"
license: Apache-2.0
homepage: https://ailingtu.com/skills/content-create
---

# 商品图片与带货视频生成 By 灵途 AI

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

面向电商商家与内容创作者的 AI 带货视频和 AI 商品图片生成 Skill，由灵途 AI 提供。从商品图片、卖点和提示词出发，生成电商带货视频、UGC 短视频、商品主图、卖点细节图和生活场景图。

使用灵途 AI 的统一任务接口，根据提示词和可选参考图片生成媒体。图片和视频采用相同流程：提交生成任务、根据返回的任务 ID 轮询状态，最后返回生成素材。

支持围绕商品素材生成电商带货视频。用户需要带货视频、用户实拍风格视频、目标市场脚本、多版本内容或商品短广告时，阅读 `references/ecommerce-video-workflow.md`。

按当前任务需要读取工作流参考，不要默认加载全部文档。

## 配置

所有认证请求只读取 `LINGTU_API_KEY`，并通过 `x-api-key` 请求头发送。
安装技能不需要认证。执行任务时缺少密钥，引导用户前往 https://ailingtu.com/api-keys
创建或管理密钥，在运行技能的环境中配置 `LINGTU_API_KEY` 后重试。
不要索取、展示或保存用户密钥，不要生成账号绑定链接。

缺少密钥时，读取 `shared/references/api-key-setup.md`，向用户展示其操作系统对应的完整步骤（如何打开终端、可复制命令、粘贴密钥、重启应用及生效范围），不要只说“配置环境变量”。已知系统时只展示对应部分；未知时同时提供 Mac 和 Windows。配置由用户在自己电脑上完成，不代为读取或填入真实密钥。


默认接口地址为 `https://api.ailingtu.com`。修改接口路径、请求字段、响应字段或状态映射前，先阅读 `references/api.md`。

## Workflow

1. 模型选择遵循本次指定 > 本机偏好 > 内置默认（视频 `wan3.0-video`，图片 `gpt-image-2.5-ext-flare`）。默认不询问模型，也不传 `--model`，由脚本读取配置；用户要求修改默认、查看设置或临时切换时，读取 `references/model-preferences.md`。
   Collect the generation intent: media kind (`image`, `video`, or another supported type), prompt, output requirements, and optional reference images, videos, or voiceovers.
   - 图片默认比例为 `9:16`；本次指定其他比例时通过 `--aspect-ratio` 覆盖。
   - 视频默认 480p，竖屏尺寸 `480x854`；横屏 480p 使用 `854x480`。本次明确指定尺寸时使用用户值。所选模型不支持该尺寸时先说明兼容性限制，不自动升到更高分辨率。
   - Video duration defaults by model: `wan3.0-video`=15s, `gemini-omni-video`=10s, `veo3.1-extend`/`veo3.1-lite-extend`=8s, `grok-imagine-1.5`=15s, `seedance2.0-mini`/`seedance2.0`/`seedance2.0-fast`=10s. For `wan3.0-video`, `-1` means adaptive duration and integers from 1 through 30 are supported. If the user specifies duration, use the user's value.
   - 写视频提示词前确定本次实际模型；未指定时用 `--kind video --show-default-model` 查询。Wan (`wan3.0-video`) 读取 `references/wan-prompt-guide.md`，按素材与意图选用自然语言、参考素材或分镜写法，不强制八字段。
   - For other video models, use this field format in this exact order: `Video style:`, `Scene:`, `Camera:`, `Tone & pacing:`, `Character:`, `Spoken script:`, `Audio:`, `Overall feeling:`. Do not add other top-level fields or prose outside the format.
2. Upload local reference files to Lingtu first via `POST /v1/file/upload` (multipart `file` field). For images, use the returned `data.url`; the create API does not accept base64 / `data:` image URLs. For `wan3.0-video` reference videos and voiceovers, use the returned `data.id`. Preserve the user's order because reference order can influence generation.
3. Create a Lingtu AI schedule using `scripts/lingtu_content_task.py`. The script auto-uploads local paths passed via `--reference-image`, `--reference-video`, or `--reference-audio`. Image references are sent as `params.inputReference` / `params.inputReferences`; `wan3.0-video` reference videos and voiceovers are sent as integer arrays in `params.videoFileIds` and `params.audioFileIds`. The media flags can also take existing Lingtu file ids for video/audio. The script generates an 8-character `taskId` by default and sends it with the create payload; the schedule create response may also return provider `taskIds`.
4. Unless the user explicitly asks for multiple outputs, pass `--nums 1`, create only one schedule/task for the request, return the first successful asset, and stop. If the current task is pending, processing, or otherwise not explicitly failed or timed out, keep polling that same task and do not create a new one. Do not generate extra variants or rerun the same prompt after success. **Crucial: a script crash, network error, or non-zero exit during polling does NOT mean the task failed.** Always re-run poll-only with the existing id before considering a retry:
   ```bash
   python3 scripts/lingtu_content_task.py --kind video --poll-schedule-id <schedule_id>
   # or
   python3 scripts/lingtu_content_task.py --kind video --poll-task-id <task_id>
   ```
   Only treat the task as failed when the API explicitly returns a failure status (FAILED, CANCELLED, EXPIRED, error).
5. Poll the task id or schedule id until completion, failure, cancellation, or timeout. Use a default timeout of 300 seconds and a short polling interval such as 5 seconds. Treat a returned task `type` that differs from the requested kind as an error.
6. Return the generated image/video URLs or saved files. If the task fails, times out, returns an unknown schema, or the script exits non-zero, report the provider status/error and include this fallback: `生成失败或遇到未知问题，请联系开发者：微信 yh8000m`.

参考源视频结构、脚本或镜头生成新视频时，读取 `references/viral-remake-workflow.md`，先理解视频，再结合商品与卖点生成。复用已有分析结果。爆款复刻（按语义分段、逐段重绘确认与合成）使用 `lingtu-video-remake`。

## Product Content Routing

- **参考结构的视频生成**：按 `references/viral-remake-workflow.md` 分析源视频并适配商品，再生成新视频。

- **商品图片**：根据商品素材和图片用途，直接编写提示词并生成主图、细节图或场景图。
- **带货视频**：直接使用用户提供的商品素材和卖点，按 `references/ecommerce-video-workflow.md` 设计脚本并生成视频。

参考图片按用户提供的顺序使用，不要求三张固定角色的图片，也不自动增加参考图优化或生成步骤。

## 脚本用法

The bundled script supports direct task creation only as an explicit compatibility option. Its default `--create-mode auto` uses schedule creation for both images and videos. Do not submit the same payload through both create APIs for one user request.

```bash
python3 scripts/lingtu_content_task.py \
  --kind video \
  --prompt "A clean product reveal video for a smart desk lamp" \
  --size 480x854 \
  --reference-image ./ref-1.png \
  --reference-image ./ref-2.jpg \
  --reference-video ./motion-reference.mp4 \
  --reference-audio ./voice-reference.mp3
```

The script also reads endpoint paths from environment variables:

```bash
export LINGTU_AI_CREATE_MODE="auto"
export LINGTU_AI_CREATE_PATH="/v1/ai/task/create"
export LINGTU_AI_STATUS_PATH="/v1/ai/task/query?taskId={task_id}"
export LINGTU_AI_SCHEDULE_CREATE_PATH="/v1/ai/schedule/create"
export LINGTU_AI_TASK_LIST_PATH="/v1/ai/task/listByScheduleId?scheduleId={schedule_id}"
```

Use `--create-mode schedule` when you want to force schedule behavior explicitly. Use `--client-task-id abc12345` only when the caller needs a specific 8-character task id; otherwise let the script generate one.

Video defaults to `wan3.0-video` unless overridden by a saved preference or an explicit `--model`. Read `references/api.md` for other supported models and their duration/resolution constraints when needed. If a requested model returns "未知模型", report the provider response instead of repeatedly retrying it.

`wan3.0-video` also supports optional reference videos and reference voiceovers. Pass a local path or an existing positive Lingtu file id with repeated `--reference-video` and `--reference-audio` flags. `--reference-dubbing` is an alias for `--reference-audio`. The script sends the resolved ids as `params.videoFileIds` and `params.audioFileIds`.

Image defaults to `gpt-image-2.5-ext-flare` unless overridden by a saved preference or an explicit `--model`. Other supported models are listed in `references/api.md`.

Use `--payload-json` for provider-specific fields that are not yet formalized in the script:

```bash
python3 scripts/lingtu_content_task.py \
  --kind image \
  --prompt "A clean product hero image" \
  --aspect-ratio 9:16 \
  --nums 1 \
  --payload-json '{"businessType":"MERCHANT_SKU","businessId":"SKU-001"}'
```

## Result Handling

When the script returns `markdown`, include those Markdown image/video embeds first in the final response so Codex can render generated images and videos directly. The script downloads remote generated images and videos into the output directory when possible, then emits local absolute file paths in Markdown because remote media URLs may render as placeholders in the Codex desktop app. After the rendered media, include the returned `output_dir` as a clickable local directory path so the user can open it and inspect all files. Also present original URLs when they are useful for sharing. Use Markdown media syntax such as `![Lingtu video result](/absolute/path/result.mp4)`, not a plain text link. When results are base64 payloads, save them under a user-appropriate output directory and return the absolute file paths.

When the script returns `contact_developer` or `message`, include the message in the final response. Do not hide the developer contact on provider failure, timeout, missing credentials, unknown response shape, network errors, or any other unexpected issue.

If the API schema differs from the default script assumptions, update `references/api.md` first, then update `scripts/lingtu_content_task.py` so future uses stay deterministic.
