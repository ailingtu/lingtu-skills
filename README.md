# 灵途 AI 能力套件

[English Version](README.en.md)

将灵途 AI 的能力封装为可复用的技能包，适配 Codex、Claude Code、Cursor、OpenClaw、Dify、OpenAI 等不同智能体和平台。核心包与模型无关，适配器仅做薄层翻译。

灵途 AI 官网：[www.ailingtu.com](https://www.ailingtu.com)。

仓库地址：[ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills)。需要更新时，从该 GitHub 仓库拉取最新版本。

## 简介

将灵途 AI 的能力封装为可复用的技能包，适配以下平台：

| 适配器 | 目标 |
|--------|------|
| Codex | 安装为 Codex Skills |
| Claude Code | 注入 CLAUDE.md |
| Cursor | 注入 AGENTS.md |
| OpenClaw | 注入 AGENTS.md |
| Dify | 导出工作流配置 |
| OpenAI | 导出 GPT 提示词 |

## 包含哪些能力

- **`packages/content-create`** — 生成商品图、AI 视频参考图、电商卖货视频、爆款复刻视频等。
- **`packages/tkshop-query`** — 查询 TK 店铺数据：日报、店铺列表、AI 经营问答。
- **`packages/social-monitor`** — TikTok / Instagram 达人竞品监控、账号视频列表、单条视频素材数据、评论导出和近期视频情报报告。
- **`packages/video-understand`** — 视频理解与内容分析：将本地视频或 TikTok/YouTube/Instagram 链接解析为自然语言的复刻提示词，可用于二创、打标和视频拆解。
- **`packages/tk-blacklist`** — 按 TikTok uniqueId 批量查询 TK 达人黑名单记录。
- **`packages/report-render`** — 将结构化报告 JSON 渲染为可分享的 PNG 长图（开发中，暂未支持安装）。

## 目录结构

```text
packages/
  content-create/   # 图片与视频生成
  tkshop-query/     # TK 店铺数据查询
  social-monitor/   # 社媒达人/竞品监控、素材数据、评论导出
  video-understand/ # 视频理解与复刻提示词生成
  tk-blacklist/ # TK 达人黑名单查询
  report-render/    # 报告 JSON 转分享长图
adapters/
  codex/            # Codex 技能安装
  claude/           # Claude Code 适配
  cursor/           # Cursor 适配
  openclaw/         # OpenClaw 适配
  dify/             # Dify 工作流导出
  openai/           # OpenAI GPT 适配
install.sh          # 一键安装脚本
```

## 环境准备

单用户模式使用前需先绑定一个管理员。单用户模式仍然是多人共用同一个付费主体，但本地会记住这个管理员身份，并通过同一套 `/binduser` 流程取回该管理员的 key：

```bash
python3 shared/scripts/user_keys.py single bind
```

命令会自动生成并保存一个稳定的本地用户 id，使用 `LOCAL` 平台完成绑定。需要把飞书/微信里的某个人明确记为管理员时，也可以传入身份：

```bash
python3 shared/scripts/user_keys.py single bind --channel feishu --user-id ou_admin_xxx --remark "单用户模式管理员"
```

打开命令返回的 `/binduser` 链接完成绑定后，业务脚本在 `single` 模式下无需传 `--channel` 和 `--user-id`。请求通过请求头 `x-api-key` 传递密钥。切勿将密钥或业务数据提交到 Git。

多用户 bot 模式不要让用户在聊天里发送 API Key。绑定页固定使用 `https://app.ailingtu.com/binduser`。部署 bot 时由管理员设置一次多用户模式；业务请求执行过程中不要自动切换认证模式。每次生成绑定链接时，skills 都会自动生成一个唯一 session `token`，主站据此保存/校验用户绑定关系。

```bash
python3 shared/scripts/user_keys.py mode set multi
python3 shared/scripts/user_keys.py bind --channel feishu --user-id ou_xxx --remark "机器人备注"
```

默认认证模式是 `single`，业务脚本使用已绑定的单用户管理员 key。部署切到 `multi` 后，业务脚本必须传入 `--channel` 和 `--user-id`，并始终走多用户认证；切换命令会尽量清理本地单用户 key：当前进程环境、单用户管理员的本地 key、旧版顶层本地配置字段，以及 macOS `launchctl` 应用环境。如果用户未绑定，返回 `/binduser` 链接让用户绑定，不要临时切回单用户模式。本地没有该用户 key 时，会调用固定后端绑定查询接口 `https://api.ailingtu.com/v1/apiKeyBind/check` 取回并保存；飞书、微信、本地单用户身份分别使用 `FEISHU`、`WEIXIN`、`LOCAL` 平台值。配置文件权限写入为 `0600`。

```bash
python3 packages/tkshop-query/scripts/lingtu_shop_data.py list-shops --channel feishu --user-id ou_xxx
python3 shared/scripts/user_keys.py unbind --channel feishu --user-id ou_xxx
```

用户级 session `token` 是必需绑定凭证，但默认由 `bind` 命令自动生成并保存到本地配置。同一用户重复生成绑定链接也会得到新的 token，并覆盖本地保存的旧 token；旧链接自然失效。调用 `/v1/apiKeyBind/check` 取回 key 时只使用最新 token，成功后清理该 token。需要调试或复用外部 token 时，也可以在生成单个链接时临时传 `--token`：

```bash
python3 shared/scripts/user_keys.py bind --channel feishu --user-id ou_xxx --token "..."
```

## 安装

```bash
git clone https://github.com/ailingtu/lingtu-skills.git
cd lingtu-skills
./install.sh                               # 自动识别平台，然后引导选择要安装的能力
```

也可手动指定目标平台和能力包：

```bash
./install.sh codex all
./install.sh codex content-create tkshop-query social-monitor video-understand tk-blacklist
./install.sh claude /path/to/project content-create
./install.sh cursor /path/to/project all
./install.sh openclaw /path/to/project all
./install.sh openai /path/to/export/dir tkshop-query
./install.sh dify /path/to/export/dir all
```

不指定能力包时，安装脚本会显示选择引导。客户可以输入 `all`、能力包名称，或输入 `1,2` 这样的编号多选。

## 快速开始

### 内容生成（Content Create）

```bash
cd packages/content-create

# 生成商品图
python3 scripts/lingtu_content_task.py \
  --kind image \
  --prompt "一张白色背景的产品主图" \
  --model gpt-image-2 \
  --aspect-ratio 1:1 \
  --nums 3 \
  --reference-image /path/to/product.png

# 生成电商视频
python3 scripts/lingtu_content_task.py \
  --kind video \
  --prompt "一个简洁的产品展示视频" \
  --model gemini-omni-video \
  --seconds 10 \
  --size 720x1280 \
  --reference-image /path/to/ref-1.png \
  --reference-image /path/to/ref-2.png
```

### 店铺查询（TKShop Query）

```bash
cd packages/tkshop-query

# 查看店铺列表
python3 scripts/lingtu_shop_data.py list-shops

# 获取默认店铺日报
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09

# 获取指定店铺日报
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09 --shop-name "店铺名称"

# 向 AI 提问经营问题
python3 scripts/lingtu_shop_data.py ask "店铺最近经营有什么问题？"
```

### 社媒达人/竞品监控（Social Monitor）

```bash
cd packages/social-monitor

# 添加达人/竞品账号，并生成最近 40 条视频分析
python3 scripts/lingtu_social_monitor.py add \
  --platform tiktok \
  --input "https://www.tiktok.com/@example" \
  --remark "竞品账号，主卖健身产品" \
  --source feishu_group \
  --group-id mock_group_001 \
  --operator-id user_001 \
  --format text
```

### 视频理解（Video Understand）

```bash
cd packages/video-understand

# 解析 TikTok / YouTube / Instagram 链接，流式返回复刻提示词
python3 scripts/lingtu_video_understand.py replicate \
  --url "https://www.tiktok.com/@user/video/1234567890"

# 解析本地视频文件（自动上传后再复刻）
python3 scripts/lingtu_video_understand.py replicate --file ./clip.mp4

# 仅上传文件，返回文件 id 和 CDN 地址
python3 scripts/lingtu_video_understand.py upload ./clip.mp4
```

### TK 达人黑名单（TK Blacklist）

```bash
cd packages/tk-blacklist

# 批量查询达人是否在黑名单中
python3 scripts/lingtu_tk_blacklist.py search vexbolts xochitlklepper --format text
```

## 交付方式

- **公开仓库**：GitHub 公开仓库 [ailingtu/lingtu-skills](https://github.com/ailingtu/lingtu-skills)，客户直接 `git clone` / `git pull` 拉取。
- **版本发布**：以版本号（如 `v1.0.0`）为交付契约，客户可回滚。
- **Zip 包**：从 Release Tag 导出压缩包分发。
- **服务部署**：需要隐藏实现细节时，以服务或 Docker 方式交付。

## 开发说明

- 核心逻辑放在 `packages/` 中，适配器保持轻量。
- API 变更时，先更新对应包的 `references/api.md`，再更新脚本和适配器。
- 不要向客户暴露 API 密钥。
