# 爆款复刻：分段重绘与合成

使用 `scripts/lingtu_video_remake.py` 完成转写、切片、逐段生成确认和合成。以下规则仅适用于此流程。

## 前置条件

- Python 3.10 或更高版本。
- `ffmpeg` 与 `ffprobe` 必须在 `PATH` 中。
- Wan3.0 生成和 HTTP ASR 认证都只使用 `LINGTU_API_KEY`，并通过 `x-api-key` 请求头发送。缺少时引导用户前往 https://ailingtu.com/api-keys 创建或管理密钥，并在运行 Skill 的环境中配置 `LINGTU_API_KEY` 后重试；不要索取、展示或保存用户的 API Key。
- 时间戳由自动转写获得，不默认要求用户提供。已有 JSON/SRT/VTT 可复用。短视频已有完整台词且不超过单段上限时，直接使用整段区间，无需逐句时间戳。

修改 Lingtu 接口路径、任务字段或状态映射前，先读取 `api.md`。处理或恢复任务状态前，读取 `job-schema.md`。

## 工作流

1. 使用 `prepare` 创建任务。明确无台词时按固定时长切片；短视频已有完整台词时直接准备整段；其余情况自动转写并规划不超过15秒的连续片段，再通过 FFmpeg 生成无音轨参考视频。
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

## 组合照片、声音与台词

`generate` 和 `regenerate` 支持重复传入 `--reference-image`（本地图片或 HTTP(S) URL）、`--reference-audio`（本地音频或正整数文件 ID），保持用户提供的顺序。显式用 `--prompt` 指定人物替换、音色、该段台词和口型要求；纯台词 TXT 可用于短视频整段准备，但不会自动注入生成提示词；Agent 应把本段台词写入 `--prompt`。

```bash
python3 scripts/lingtu_video_remake.py generate --job-dir ./remake-job \
  --reference-image ./portrait.jpg \
  --reference-audio ./voice.mp3 \
  --seconds -1 --size 480x854 \
  --prompt '将 @视频1 中的人物替换为 @图1 中的人物，保持场景、构图、动作和镜头运动，清除画面文字。人物用 @音频1 的音色说：「本段台词」，匹配嘴型。'
```

默认生成时长仍为片段实际时长向上取整。`--seconds -1` 请求自适应时长；它可能改变最终时长和节奏，不表示将输出强制限制为15秒。多段任务逐段提供适用的参考素材与台词，不把整篇台词重复用于每段。音频作为音色/配音参考上传，不自动裁切、变速或替换最终音轨，不保证精确口型与人物一致性。

同一片段 `regenerate` 未传图片、音频或时长时复用上一 attempt 的对应值；显式参数覆盖对应类型的整个列表。后续新片段不自动继承上一片段的参考素材。`poll` 只恢复已有请求，不重新上传或提交生成。


## 自动准备台词

短视频已有完整台词（包括前文用户已提供的台词），使用：

```bash
python3 scripts/lingtu_video_remake.py prepare ./source.mp4 --script-file ./台词.txt --job-dir ./remake-job
# 也支持 --script-text '完整台词' 或 --transcript ./台词.txt
```

视频不超过 `--max-seconds`（默认15秒）时，记录 `[0, 视频时长]` 的整段台词区间，来源为 `provided-text-whole-clip`，不声称已逐句对齐。无需调用 ASR。需要生成口播时由 Agent 将台词与换人、音色要求组合进生成提示词。

未声明无台词，且没有完整台词或视频超过单段上限时，`prepare` 默认自动选择本机 Whisper CLI，其次使用 `LINGTU_ASR_URL`。显式 `--whisper` 或 `--asr-url` 优先于自动选择；已有时间戳文件直接复用。长视频提供纯文本时仍转写原视频取得真实时间戳，不均分文字伪造时间；提供的纯文本不自动用于改写或校正 ASR 结果。

没有可用转写方式时才说明缺失的工具或服务，时间戳文件只是可选替代。显式选择的转写失败时报告失败，不暗中切换在线服务。Whisper 首次运行可能下载模型；用户只要模拟或禁止请求时，不执行转写或下载，只预览计划。


## 明确无台词的视频

用户明确说明视频没有台词时，直接运行：

```bash
python3 scripts/lingtu_video_remake.py prepare ./source.mp4 --no-speech --job-dir ./remake-job
```

跳过本机 Whisper 与 HTTP ASR，不读取台词文件或生成虚构台词。按 `--max-seconds` 固定间隔切片（默认15秒，最大15秒），最后一段保留实际剩余时长。例如38秒切为15、15、8秒；不足15秒保留整段。片段覆盖完整原视频时间线。

`--no-speech` 与 `--transcript`、`--script-file`、`--script-text`、`--whisper`、`--asr-url` 互斥。未提供台词不等于无台词；转写失败也不能自动切换到无台词模式。

状态中 `transcription.source` 为 `no-speech`，`transcript.json` 的 `segments` 为空数组，片段 `text` 为空。展示片段表时标记“无台词”，不因此判为转写错误。逐段生成、确认和最终合成流程不变。无台词不代表没有音乐或环境声，仍按现有规则消除参考片段的原音轨，最终是否静音由 `merge --final-mute` 单独控制。
