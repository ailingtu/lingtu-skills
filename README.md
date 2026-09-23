# 灵途 AI 能力套件

将灵途 AI 的能力封装为可独立安装的技能包。每项能力分别发布、分别安装，Skill 本身保持模型无关。

灵途 AI 官网：[www.ailingtu.com](https://www.ailingtu.com)。

源码仓库：[coss/ailingtu/skills](https://codeup.aliyun.com/coss/ailingtu/skills)，仅用于开发和发布。用户安装与升级统一使用[灵途 Skills 官方安装文档](https://ailingtu.com/install/skills.md)，不要从 Codeup 或 GitHub 安装。

## 包含哪些能力

<!-- skills-table:start -->
| 能力包 | 能力说明 | 版本号 | 更新时间（北京时间） | 负责人 |
| --- | --- | --- | --- | --- |
| [`openapi-guide`](packages/openapi-guide/) | 面向开发者查询灵途 OpenAPI 文档、说明 API Key 的获取与安全使用方式、选择接口、生成或审查接入代码和排查脱敏错误；Skill 本身不持有 API Key，也不调用线上业务接口。 | 0.1.3 | 2026-09-22 20:06:42 | 许强强 |
| [`content-create`](packages/content-create/) | 灵途 AI 带货视频和商品图片生成。根据商品素材和提示词生成带货视频、UGC 短视频、商品主图和场景图。 | 0.4.4 | 2026-09-22 20:06:42 | 许强强 |
| [`tkshop-query`](packages/tkshop-query/) | 查询 TK 店铺数据：日报、店铺列表、AI 经营问答。 | 0.2.3 | 2026-09-22 20:06:43 | 许强强 |
| [`tk-blacklist`](packages/tk-blacklist/) | 按 TikTok uniqueId 批量查询达人黑名单记录、反馈次数、最近反馈时间和原因。 | 0.1.3 | 2026-09-22 20:06:43 | 许强强 |
| [`social-monitor`](packages/social-monitor/) | TikTok / Instagram 达人竞品监控、账号视频列表、单条视频素材数据和近期视频情报报告。 | 0.9.3 | 2026-09-22 20:06:43 | 许强强 |
| [`social-comments`](packages/social-comments/) | 下载和导出 TikTok、Instagram、抖音、视频号及小红书单条视频评论，支持自动分页和 JSON 保存。 | 0.1.3 | 2026-09-22 20:06:42 | 许强强 |
| [`video-understand`](packages/video-understand/) | 视频理解与内容分析：将本地视频或 TikTok/抖音/小红书/视频号/YouTube/Instagram 链接解析为自然语言的复刻提示词，可用于二创、打标、参考结构生成和视频拆解。 | 0.9.4 | 2026-09-22 20:06:43 | 许强强 |
| [`video-remake`](packages/video-remake/) | 爆款复刻：源视频转写、15秒内语义切片、Wan3.0逐段重绘确认和合成；发行包独立运行。参考结构与商品改编生成属于 `packages/content-create`。 | 0.2.6 | 2026-09-22 20:06:43 | 许强强 |
| [`video-publish`](packages/video-publish/) | TikTok Shop / TikTok 普通视频批量发布、CSV 排期生成、达人/商品查询和 dry-run 校验。 | 0.2.3 | 2026-09-22 20:06:43 | 许强强 |
| [`tiktok-carousel`](packages/tiktok-carousel/) | TikTok 爆款带货图文创作 By 灵途 AI：围绕商品真实卖点策划逐页方案，确认后生成图片与发布文案。 | 0.1.5 | 2026-09-22 19:57:40 | 郑丹 |
| [`xhs-remake`](packages/xhs-remake/) | 参考一篇小红书图文的内容结构和视觉方式，用自有素材重新创作非挂车种草图文、标题、正文与标签。 | 0.1.5 | 2026-09-23 18:54:48 | jasonxu591-cmd |
| [`video-download`](packages/video-download/) | 根据 TikTok、抖音、视频号和小红书公开链接获取播放与互动数据，并下载无水印视频。 | 0.1.1 | 2026-09-22 18:55:34 | 许强强 |
| [`skillhub-publish`](packages/skillhub-publish/) | 把 AI Skill 发布到灵途 SkillHub 或腾讯 WorkBuddy（skillhub.cn）。 | 0.1.0 | 2026-09-22 15:29:08 | jasonxu591-cmd |
| [`skill-finder`](packages/skill-finder/) | 根据自然语言需求查询实时官方目录，推荐适合的灵途技能并按需安装。 | 0.1.0 | 2026-09-23 13:54:01 | jasonxu591-cmd |
<!-- skills-table:end -->

版本号来自各包的 `SKILL.md`；更新时间记录最近一次成功打包的时间，历史打包时间未记录。
打包时自动同步对应行，可通过 `--owner "负责人"` 指定负责人。

## 目录结构 

```text
packages/
  skill-finder/     # 实时查询官方目录，按自然语言需求推荐与安装技能
  openapi-guide/    # OpenAPI 文档查询与开发者接入指导
  content-create/   # 图片与视频生成
  tkshop-query/     # TK 店铺数据查询
  tk-blacklist/     # TK 达人黑名单查询
  social-monitor/   # 社媒达人/竞品监控、素材数据
  social-comments/  # 社交媒体视频评论下载
  video-understand/ # 视频理解与复刻提示词生成
  video-remake/     # 爆款复刻：分段重绘、确认与合成
  video-publish/    # 批量视频发布和排期
  xhs-remake/       # 小红书图文结构与视觉复刻、逐页种草创作
  video-download/   # 公开视频无水印下载与数据获取
  skillhub-publish/ # 把 AI Skill 发布到灵途 SkillHub 或腾讯 WorkBuddy
shared/scripts/     # 构建时复制进每个业务 API Skill 的公共运行时
scripts/            # 单 Skill 构建工具
docs/               # CDN 单包发布说明
```

## API Key 配置

安装 Skill 不要求预先提供密钥。执行灵途任务且缺少 `LINGTU_API_KEY` 时，
请前往 <https://ailingtu.com/api-keys> 创建或管理密钥，并在运行 Skill 的环境中
配置 `LINGTU_API_KEY` 后重试。不再生成账号绑定授权 URL。
不要在聊天中发送、展示或保存 API Key。

所有需要认证的灵途请求只读取 `LINGTU_API_KEY`，并通过 `x-api-key`
请求头发送。每个会调用灵途业务 API 的独立分发包都内置
`shared/scripts/lingtu_auth.py`，不依赖本仓库的根目录。

`openapi-guide` 仅访问公开文档，不执行账号绑定，也不读取或使用 API Key。开发者可在 <https://ailingtu.com/api-keys> 登录后创建和管理 API Key；实际运行接入代码时，应在自己的服务端环境中配置凭据。

`skillhub-publish` 不读取 `LINGTU_API_KEY`。发布到灵途 SkillHub 使用后台发布密钥 `LINGTU_SKILLHUB_TOKEN`；发布到腾讯 WorkBuddy（skillhub.cn）使用 `SKILLHUB_KEY`。两把密钥不能混用。

如果用户需要绑定 TikTok Shop 店铺，或店铺/店铺商品列表为空，让用户打开以下链接完成店铺绑定/授权后再继续：

https://app.ailingtu.com/teamshop

如果发布视频时没有已授权达人，或达人未找到/未授权，让用户打开以下链接完成达人授权后再继续：

https://app.ailingtu.com/video-post

## 安装与升级

`skill-finder` 通过官网公开目录实时推荐技能，不内置能力清单，也不需要 API Key。安装后可以说“帮我找一个能完成这项任务的灵途技能”；明确要求安装时，再按官方流程执行。

把下面这句话发给 Agent 即可：

> 根据 [https://ailingtu.com/install/skills.md](https://ailingtu.com/install/skills.md) 安装灵途 Skills。

Agent 会实时读取灵途官方索引，根据任务选择所需 Skill，并从灵途 TOS/CDN
逐个下载、校验和安装。升级也使用同一文档；不要通过 GitHub 或其他技能商店安装。

已安装带更新入口的任一灵途 Skill 后，可以直接说：

> 更新灵途的 skills。

这会检查当前 Agent 已安装的灵途技能，只更新有新版的包；也可说“更新灵途的视频理解技能”只更新一项。同版跳过，本地更高版本保留，更新前保留备份。安装和升级不需要 API Key。自动识别依赖宿主支持并启用技能；旧版用户可先按上面的官方文档升级一次。

## 分别发布到灵途 CDN

新建 Skill 时先用脚手架生成符合认证与分发规范的目录：

```bash
python3 scripts/create_package.py creator-insights \
  --display-name "灵途达人洞察" \
  --summary "分析达人数据并生成可执行的洞察建议。" \
  --description "通过灵途 AI 业务接口查询达人数据并生成分析结果。"
```

默认生成 `auth: lingtu-api-key`；只读公开资料、不调用业务 API 的 Skill
显式传入 `--auth none`。每个 `SKILL.md` 都必须声明其 `auth` 模式。

为每项能力生成一个自包含目录和一个 ZIP：

```bash
python3 scripts/build_package.py content-create
```

产物位于 `dist/packages/`。每个 ZIP 解压后的根目录直接包含
`SKILL.md`，可分别上传；不要把整个仓库作为一个 Skill 上传。详细结构和检查方式见
[`docs/distribution-packaging.md`](docs/distribution-packaging.md)。

## 快速开始

### 内容生成（Content Create）

```bash
cd packages/content-create

# 生成商品图
python3 scripts/lingtu_content_task.py \
  --kind image \
  --prompt "一张白色背景的产品主图" \
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
  --group-id local_default \
  --operator-id user_001 \
  --format text
```

`group_id` 是隔离键：飞书可用群 ID；本地 / Cursor / Codex 可用 `local_default` 等稳定标识。

### 社交媒体评论下载（Social Comments）

```bash
cd packages/social-comments

python3 scripts/lingtu_social_comments.py download \
  --video-url "https://www.tiktok.com/@user/video/1234567890" \
  --output ./comments.json
```

### 视频理解（Video Understand）

```bash
cd packages/video-understand

# 解析 TikTok / 抖音 / 小红书 / 视频号 / YouTube / Instagram 链接，流式返回复刻提示词
python3 scripts/lingtu_video_understand.py replicate \
  --url "https://www.tiktok.com/@user/video/1234567890"
# 抖音 / 小红书 / 视频号示例：
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://www.douyin.com/video/7123456789012345678"
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://www.xiaohongshu.com/explore/64abcdef0123456789abcdef"
# python3 scripts/lingtu_video_understand.py replicate \
#   --url "https://channels.weixin.qq.com/web/pages/feed?eid=..."

# 解析本地视频文件（自动上传后再复刻）
python3 scripts/lingtu_video_understand.py replicate --file ./clip.mp4

# 仅上传文件，返回文件 id 和 CDN 地址
python3 scripts/lingtu_video_understand.py upload ./clip.mp4
```

### 爆款复刻（Video Remake）

参考结构的视频生成使用 `packages/content-create/references/viral-remake-workflow.md`，先分析源视频，再适配商品并生成。爆款复刻使用 `packages/video-remake/references/long-video-workflow.md`，执行语义分段、逐段重绘确认与合成，下面是该流程的命令示例。

```bash
cd packages/video-remake

# 导入带时间戳字幕，完成语义切片和消音
python3 scripts/lingtu_video_remake.py prepare ./source.mp4 \
  --transcript ./source.srt \
  --job-dir ./remake-job

# 每次只生成一段，用户确认后再生成下一段
python3 scripts/lingtu_video_remake.py generate --job-dir ./remake-job
python3 scripts/lingtu_video_remake.py approve \
  --job-dir ./remake-job --segment segment-001

# 所有片段确认后合成
python3 scripts/lingtu_video_remake.py merge \
  --job-dir ./remake-job --output ./final-remake.mp4
```

### 批量视频发布（Video Publish）

```bash
cd packages/video-publish

# 生成 CSV 排期模板
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok_shop \
  --region US \
  --date 2026-07-05 \
  --product-id pid_001234

# 模拟执行预览（编辑 schedule.csv 并放入视频后）
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05

# 确认发布
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05 \
  --confirm
```

## 交付方式

- **灵途 TOS/CDN**：每个 `packages/*` 分别构建、发布和安装。
- **安装入口**：<https://ailingtu.com/install/skills.md>。
- **版本发布**：版本号维护在各自 `SKILL.md` 的 frontmatter 中。
- **GitHub**：公开仓库保留源码、测试和发布工具。

## 开发说明

- 核心逻辑放在 `packages/` 中；不要恢复跨平台适配器或批量安装层。
- API 变更时，先更新对应包的 `references/api.md`，再更新脚本。
- 每个发布物必须自包含，不得依赖安装目录外的文件。
- 不要向客户暴露 API 密钥。

完整配置步骤（含 Mac / Windows 打开终端、命令和重启说明）：[API Key 配置指南](shared/references/api-key-setup.md)。
