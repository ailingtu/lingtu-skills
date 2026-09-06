# Lingtu Social Monitor

灵途 Social Monitor 是一个可复用的社媒达人监控和视频素材数据技能包：解析输入 → 按平台调用灵途接口拉达人最近视频或单条素材数据 → 写入群级监控列表 → 按"昨日 vs 今日"出每日中文日报。

当前版本：`0.7.3`。远端安装器可读取 [`SKILL.md`](./SKILL.md) frontmatter 的 `version` 字段决定是否更新。

## 能力

- 解析 TikTok 主页链接 / `@用户名` / 裸名 → uniqueId。
- 解析 Instagram 主页链接 / `@用户名` / 裸名，并通过 `--platform instagram` 拉取账号视频列表。
- 调真实接口拉取最近视频（默认 40），落本地快照（按 `group_id / platform / creator_id / 日期` 隔离）。
- 维护群级监控列表，每个群独立；支持 `daily_enabled` 订阅开关。
- 即时账号分析：发布频率、爆款 Top3、内容方向、开头钩子、hashtag 线索、内容结构、账号价值判断。
- 每日日报（昨日 vs 今日）：涨粉 Top、新爆款 Top、播放量增长 Top、停更/高频发布预警、逐账号速览。
- 获取单条视频素材实时数据：播放、点赞、评论、分享、收藏、视频地址、封面、发布时间等。
- 提供 `tutorial` 子命令输出"如何添加监控"的中文教程文本，供 bot 直接贴回群里。

## 环境

认证只使用 `LINGTU_API_KEY` 环境变量。请在自己的电脑上执行对应命令，不要把真实 Key 发到聊天中。

macOS：

```bash
export LINGTU_API_KEY='your-api-key'
```

Windows PowerShell：

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

永久配置时，macOS 把 export 加入 `~/.zshrc`；Windows 执行 `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")` 后重新打开终端。

可选：

```bash
export LINGTU_SOCIAL_MONITOR_STORE="~/.lingtu/social-monitor/monitors.json"
export LINGTU_SOCIAL_MONITOR_SNAPSHOTS="~/.lingtu/social-monitor/snapshots"
```

请求头 `x-api-key`。请勿提交密钥或私有数据。

## 命令一览

| 命令 | 用途 |
|------|------|
| `tutorial` | 输出添加监控的中文教程 |
| `add` | 加入监控列表 + 即时分析 + 落今日快照 |
| `batch-add` | 批量加入监控列表（支持超时/临时失败重试和过程进度提示） |
| `list` | 列出群内监控（`--daily-only` 仅每日订阅） |
| `enable-daily` / `disable-daily` | 开启/关闭某达人的每日订阅 |
| `remove` | 从监控列表中移除 |
| `snapshot` | 拉取并落盘当日快照（每日 8 点编排循环用，支持超时/临时失败重试） |
| `digest` | 生成某群的每日日报 |
| `videos` | 直接拉视频（`--raw` 输出原始响应） |
| `material` | 获取单条视频素材实时数据 |
| `analyze` | 分析一份 fetchPosts JSON 文件 |

需要平台数据的命令使用 `--platform tiktok|instagram`，默认 `tiktok`。TikTok 和 Instagram 的账号视频列表及单条视频素材数据均已接入。评论下载请使用 `packages/social-comments`。

详细参数与流程见 [`SKILL.md`](./SKILL.md)，接口字段见 [`references/api.md`](./references/api.md)。
