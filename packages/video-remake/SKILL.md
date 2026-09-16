---
name: lingtu-video-remake
slug: lingtu-video-remake
version: 0.2.5
auth: lingtu-api-key
displayName: 灵途爆款复刻
summary: 将源视频按语义分段，用 Wan3.0 逐段重绘、确认并合成爆款复刻视频。
description: "爆款复刻：保留源视频顺序，有台词时转写并按语义切片，明确无台词时直接按最多15秒切片，用 Wan3.0 逐段重绘，经用户逐段确认或跳过后合成。用户要求爆款复刻、视频分段重绘或长视频复刻时使用。参考源视频的脚本、镜头、节奏，结合商品和卖点生成新视频属于 lingtu-content-create；仅分析视频或提取提示词使用 lingtu-video-understand。 也用于“更新灵途 Skills”“升级灵途技能”或更新指定灵途技能。"
license: Apache-2.0
homepage: https://ailingtu.com/skills/video-remake
---

# 灵途爆款复刻

## 更新灵途 Skills

用户说“更新灵途 Skills”“更新灵途的 skills”“升级灵途技能”或要求更新某个灵途技能时，优先执行此流程，不启动本技能的业务任务。无需 API Key；无需先安装其他技能。只需由一个已加载的灵途技能统一处理，避免多个技能重复更新。

1. 读取 https://ailingtu.com/install/skills.md 和实时索引 https://cdn.ailingtu.cn/skills/packages/index.json 。更新所有技能时，在当前 Agent 实际启用的用户级与项目级 Skills 目录中查找已安装的灵途技能；指定技能时只处理匹配项。不扫描其他应用，不安装尚未安装的技能。
2. 用本地 SKILL.md 的 name/slug 精确匹配索引，按 SemVer 比较 version（数字比较，不按字符串排序）。同版跳过，本地更高版本保留，不自动降级；版本缺失、格式不明或索引无匹配时单独报告，不猜测下载地址。重复目录解析真实路径去重；确有多个启用副本时逐个报告路径并更新。忽略备份目录。
3. 对有新版的技能逐包下载，核对索引 SHA-256、大小及包内 name/version，验证 ZIP 路径不越界且不含符号链接，再在暂存目录解压。备份旧目录到 Agent 不会扫描的目录，保留用户配置和任务输出，然后完整替换包文件，避免覆盖解压留下旧脚本。失败恢复原目录，其余包可继续；不读取或修改密钥。
4. 汇报各包旧版→新版、已是最新、跳过或失败原因、实际安装与备份位置。宿主不支持热加载时提示重启。官方文档或索引不可访问时明确说明，保留本地版本。

用户已明确要求更新时直接执行；仅在路径歧义无法自行确定或宿主权限要求时再询问。不要将本次更新请求理解为自动定时更新或发布授权。

## 安装与认证

按照 https://ailingtu.com/install/skills.md 安装或升级。
所有认证请求只读取 `LINGTU_API_KEY`，通过 `x-api-key` 发送。任务需要认证但缺少 Key 时，引导用户前往 https://ailingtu.com/api-keys 创建或管理密钥，并在运行 Skill 的环境中配置 `LINGTU_API_KEY` 后重试；不要索取、展示或保存 API Key。

缺少密钥时，读取 `shared/references/api-key-setup.md`，向用户展示其操作系统对应的完整步骤（如何打开终端、可复制命令、粘贴密钥、重启应用及生效范围），不要只说“配置环境变量”。已知系统时只展示对应部分；未知时同时提供 Mac 和 Windows。配置由用户在自己电脑上完成，不代为读取或填入真实密钥。


## 工作流与边界

- **爆款复刻**：读取 `references/long-video-workflow.md`，明确无台词时使用 `prepare --no-speech` 按最多15秒切片，跳过转写；短视频已有完整台词时直接准备整段；其余需要切片或提取台词时自动转写，再按语义切片，使用 Wan3.0 逐段重绘，最后按原顺序合成。每段不超过15秒，生成结果须由用户逐段确认或明确跳过后才处理下一段。此流程也适用于短视频，不按源视频时长切换到视频生成。
- **参考结构的视频生成**：参考源视频的脚本、镜头或节奏，结合自己的商品和卖点生成新视频，使用 `lingtu-content-create` 的 `references/viral-remake-workflow.md`。
- **只要视频分析、总结、打标或提示词**：使用 `lingtu-video-understand`。

人物照片、音色参考与指定台词可按流程文档“组合照片、声音与台词”接入，生成时支持 `--reference-image`、`--reference-audio`、`--seconds -1` 和 `--prompt`。

本包自带分段重绘脚本和认证运行时，无需另装其他 Skill。前置依赖、转写来源、逐段确认和恢复规则见流程文档。修改接口前读取 `references/api.md`；恢复任务状态前读取 `references/job-schema.md`。

不默认要求用户上传时间戳文件。完整台词且视频不超过单段上限时使用 `prepare --script-file` 或 `--script-text`，无须 ASR。明确无台词时使用 `--no-speech`；不能将“用户未提供台词”视为“视频无台词”。其余情况默认检测本机 Whisper，再使用已配置的 HTTP ASR；没有可用方式时说明缺失能力，不虚构时间戳。模拟任务禁止启动 ASR、下载模型或调用在线接口。
