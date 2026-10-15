# AI 视频拆解与复刻提示词 By 灵途 AI

将视频转换为自然语言复刻提示词，输出包含标题、主体、场景、分镜脚本和制作说明的 Markdown 内容，可用于后续视频生成、内容理解和打标。

当前版本以 [`SKILL.md`](./SKILL.md) 文件头部的 `version` 字段为准，安装器可据此判断是否需要升级。

## 主要能力

- 支持 TikTok、抖音、小红书、视频号、YouTube、Instagram 的公开视频链接、本地视频文件，以及灵途素材或文件引用（`businessId` + `businessType`）。
- 本地文件通过 `POST /v1/file/presign` → `PUT` 到 `data.uploadUrl` → `POST /v1/file/confirm` 上传，将返回的 `data.fileId` 作为 `businessId`，并设置 `businessType: "FILE"`。
- 通过 `POST /v1/material/analysisTask/stream` 流式获取复刻提示词（`type: "REPLICATION"`）。
- 校验流式响应后输出完整提示词；`--json` 包含来源和任务 ID，`--raw` 输出用于诊断的 SSE 原始行，并报告校验失败。
- 分析 TikTok 或 Instagram 视频时，可通过 `packages/social-monitor` 获取实时指标；通过 `packages/social-comments` 获取 TikTok、Instagram、抖音、视频号或小红书的评论，再结合复刻提示词分析。

本技能目前仅发送 `type: "REPLICATION"`，`ANALYSIS` 模式暂为保留项。

## 使用要求

所有认证请求仅从环境变量 `LINGTU_API_KEY` 读取密钥，并通过 `x-api-key` 请求头发送。缺少密钥时，引导用户前往 https://ailingtu.com/api-keys 创建或管理密钥，在运行技能的环境中配置后重试。不要将密钥粘贴到聊天中，也不要将密钥、私人媒体或经营数据提交到仓库。

独立安装包内置 `shared/scripts`，认证、HTTP 请求和上传与其他灵途技能使用相同的运行时。

## 脚本用法

解析支持平台的公开视频链接（TikTok、抖音、小红书、视频号、YouTube、Instagram）：

```bash
python3 scripts/lingtu_video_understand.py replicate --url "https://www.tiktok.com/@user/video/1234567890"
python3 scripts/lingtu_video_understand.py replicate --url "https://www.douyin.com/video/7123456789012345678"
python3 scripts/lingtu_video_understand.py replicate --url "https://www.xiaohongshu.com/explore/64abcdef0123456789abcdef"
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

仅上传文件：

```bash
python3 scripts/lingtu_video_understand.py upload ./clip.mp4
```

输出原始 SSE 流：

```bash
python3 scripts/lingtu_video_understand.py replicate --url "..." --raw
```

## 批量处理

每次复刻分析会占用数十秒的流式连接，不要无限并发调用。并发数最多为 **10**，常规批量任务建议使用 3–5。

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

## 接口参考

修改接口路径、请求字段、响应字段或流式解析前，先阅读 [`references/api.md`](./references/api.md)。
