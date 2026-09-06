---
name: lingtu-video-remake
slug: lingtu-video-remake
version: 0.1.0
displayName: 灵途长视频分段复刻
summary: 转写长视频，按语义切成15秒内片段，经Wan3.0逐段重绘确认后合成。
description: 长视频分段复刻与重绘。将本地长视频识别为带时间戳文字，按语义边界切成不超过15秒的片段，消除原音频，逐段上传给 Wan3.0 生成；每一段都必须由用户预览确认或明确跳过，全部处理完成后再合成为最终视频。用户提到“长视频复刻”“分段重绘”“识别文字后切片生成”“Wan3.0逐段生成并合成”时使用。不用于普通文生视频、视频内容总结或仅提取字幕。
license: Apache-2.0
homepage: https://ailingtu.com/skills/video-remake
---

# 长视频分段复刻

## 安装与升级

按照 https://ailingtu.com/install/skills.md 操作，不要从 GitHub 或其他技能商店安装或升级本 Skill。

使用 `scripts/lingtu_video_remake.py` 完成转写、语义切片、消音、Wan3.0 逐段生成、人工确认和最终合成。此 Skill 完全自包含，不调用或导入其他 Skill。

## 前置条件

- Python 3.10 或更高版本。
- `ffmpeg` 与 `ffprobe` 必须在 `PATH` 中。
- Wan3.0 生成使用 `LINGTU_API_KEY`。缺少时从本 Skill 根目录运行 `python3 shared/scripts/user_keys.py single bind`，把生成的授权链接交给用户打开；不要索取、展示或保存用户的 API Key。
- 转写需要带时间戳的数据。优先使用用户提供的 JSON、SRT 或 VTT；也可使用本机已安装的 Whisper CLI，或用户配置的 HTTP ASR 服务。

修改 Lingtu 接口路径、任务字段或状态映射前，先读取 `references/api.md`。处理或恢复任务状态前，读取 `references/job-schema.md`。

## 工作流

1. 使用 `prepare` 创建任务。它取得带时间戳转写、规划不超过15秒的连续片段，并通过 FFmpeg 生成无音轨参考视频。
2. 向用户展示片段数量、时间范围与对应文字。转写明显错误或切点不合理时先停止，不提交付费生成。
3. 使用 `generate` 只生成当前一段。不要并行提交后续片段，也不要在用户确认当前结果前自动生成下一段。
4. 展示生成视频、片段编号、原始时间范围、对应文字和尝试次数，等待用户选择：
   - 满意：运行 `approve`。
   - 不满意：运行 `reject --note ...`，得到明确修改意见后才运行 `regenerate`。
   - 不需要：只有用户明确要求时运行 `skip`。
5. 当前段 `approved` 或 `skipped` 后，才处理下一段。
6. 所有片段均为 `approved` 或 `skipped` 后运行 `merge`。脚本会统一编码、分辨率、帧率和音轨，再按原顺序合成。

任何创建响应已返回 `schedule_id` 的任务都必须通过 `poll` 恢复。轮询超时、网络中断或脚本退出不代表生成失败，不得因此创建新任务。只有 API 明确返回失败且用户要求重做时，才运行 `regenerate`。

## 常用命令

从带时间戳 JSON、SRT 或 VTT 开始：

```bash
python3 scripts/lingtu_video_remake.py prepare ./source.mp4 \
  --transcript ./source.json \
  --job-dir ./remake-job
```

使用本机 Whisper CLI：

```bash
python3 scripts/lingtu_video_remake.py prepare ./source.mp4 \
  --whisper \
  --whisper-model small \
  --job-dir ./remake-job
```

使用自定义 HTTP ASR 服务：

```bash
python3 scripts/lingtu_video_remake.py prepare ./source.mp4 \
  --asr-url "$LINGTU_ASR_URL" \
  --job-dir ./remake-job
```

逐段生成和确认：

```bash
python3 scripts/lingtu_video_remake.py generate --job-dir ./remake-job
python3 scripts/lingtu_video_remake.py approve --job-dir ./remake-job --segment segment-001
python3 scripts/lingtu_video_remake.py generate --job-dir ./remake-job
```

拒绝并明确重做：

```bash
python3 scripts/lingtu_video_remake.py reject \
  --job-dir ./remake-job --segment segment-002 \
  --note "人物动作不连贯，保持参考视频的动作节奏"

python3 scripts/lingtu_video_remake.py regenerate \
  --job-dir ./remake-job --segment segment-002
```

恢复已有生成任务：

```bash
python3 scripts/lingtu_video_remake.py poll \
  --job-dir ./remake-job --segment segment-002
```

检查状态并合成：

```bash
python3 scripts/lingtu_video_remake.py status --job-dir ./remake-job
python3 scripts/lingtu_video_remake.py merge \
  --job-dir ./remake-job --output ./final-remake.mp4
```

默认仅消除上传给 Wan3.0 的原视频音轨，最终合成会保留生成视频的音频。用户要求最终静音时给 `merge` 加 `--final-mute`。

## 输出要求

- `prepare` 后报告任务目录、转写来源、片段总数和片段表。
- `generate` 或 `poll` 完成后，优先用本地绝对路径渲染生成视频，并清楚标明等待确认的片段。
- `merge` 后返回最终视频的本地绝对路径。
- API 明确失败时报告服务端状态和错误。未知错误时附上：`生成失败或遇到未知问题，请联系开发者：微信 yh8000m`。
