---
name: lingtu-video-publish
slug: lingtu-video-publish
version: 0.4.1
auth: lingtu-api-key
displayName: "TikTok 视频与图文批量发布 By 灵途 AI"
summary: 从素材文件夹生成可审核的发布方案，确认后提交并查询 TikTok 发布结果。
description: "灵途视频/图文发布 — 从素材文件夹生成发布方案、自动分配素材和排期，审核确认后向 TikTok Shop / TikTok 账号提交任务并查询结果。支持带货视频/图文、普通及高级版视频/图文、选曲收藏、音量、封面、地域、发布配置、任务管理、云草稿接口、CSV/XLSX与重复提交保护。 也用于“更新灵途 Skills”“升级灵途技能”或更新指定灵途技能。"
license: Apache-2.0
homepage: https://ailingtu.com/skills/video-publish
---

# TikTok 视频与图文批量发布 By 灵途 AI

## 更新灵途 Skills

用户说“更新灵途 Skills”“更新灵途的 skills”“升级灵途技能”或要求更新某个灵途技能时，优先执行此流程，不启动本技能的业务任务。无需 API Key；无需先安装其他技能。只需由一个已加载的灵途技能统一处理，避免多个技能重复更新。

1. 读取 https://ailingtu.com/install/skills.md 和实时索引 https://cdn.ailingtu.cn/skills/packages/index.json 。更新所有技能时，在当前 Agent 实际启用的用户级与项目级 Skills 目录中查找已安装的灵途技能；指定技能时只处理匹配项。不扫描其他应用，不安装尚未安装的技能。
2. 用本地 SKILL.md 的 name/slug 精确匹配索引，按 SemVer 比较 version（数字比较，不按字符串排序）。同版跳过，本地更高版本保留，不自动降级；版本缺失、格式不明或索引无匹配时单独报告，不猜测下载地址。重复目录解析真实路径去重；确有多个启用副本时逐个报告路径并更新。忽略备份目录。
3. 对有新版的技能逐包下载，核对索引 SHA-256、大小及包内 name/version，验证 ZIP 路径不越界且不含符号链接，再在暂存目录解压。备份旧目录到 Agent 不会扫描的目录，保留用户配置和任务输出，然后完整替换包文件，避免覆盖解压留下旧脚本。失败恢复原目录，其余包可继续；不读取或修改密钥。
4. 汇报各包旧版→新版、已是最新、跳过或失败原因、实际安装与备份位置。宿主不支持热加载时提示重启。官方文档或索引不可访问时明确说明，保留本地版本。

用户已明确要求更新时直接执行；仅在路径歧义无法自行确定或宿主权限要求时再询问。不要将本次更新请求理解为自动定时更新或发布授权。

## 安装与升级

按照 https://ailingtu.com/install/skills.md 操作，不要从 GitHub 安装或升级本 Skill。

## 网页发布能力迁移

先读 [迁移工作流](references/migrated-workflow.md) 和 [接口合同](references/api.md)。统一 `/v1`，只用 API Key，不使用网页登录令牌。支持5种场景；选曲、封面、地域及平台设置进入同一份发布方案审核。服务端未开放的迁移路径报告404/403，不回退admin。

## 默认工作流：素材 → 发布方案 → 确认提交 → 查询结果

用户给出素材文件夹及发布目标即可开始。CSV 是可选编辑入口，不要求用户逐行填写文件名或把素材搬到新文件夹。旧排期表继续支持。

### 1. 理解需求并查看素材

复用用户已经提供的素材、达人、商品、日期、频率、语言和时区，不重复收集。先查看文件夹中的媒体和已有文案，并查询授权达人；只有缺失信息会影响实际发布时才追问。

- 视频默认一条文件对应一条内容。支持子目录递归扫描，按自然文件名排序。
- 图文每个直接子文件夹对应一篇，图片按自然文件名排序。根目录散图不能猜分组；先展示图片，让用户确认分篇和顺序，再整理子目录。不要更改原素材，必要时在新目录准备副本。
- 多达人必须明确是“每份素材分配给一个达人”，还是“每个达人都发全部素材”。先说明两种方案的条数和重复内容，不能默认全账号重复发布。
- 只有一个符合需求的账号或用户已指定账号时直接选入草稿。不要默认全授权账号发布。
- 带货达人可按地区筛选，普通 TikTok 达人不按地区筛选。带货图文只选 TikTok Shop 授权且有 `PHOTO_SHOPPABLE_PERMISSION_PRODUCT` 的账号；不带货图文使用高级版 Business 账号。
- 无达人或未授权：引导 https://app.ailingtu.com/video-post 。无店铺或商品：引导 https://app.ailingtu.com/teamshop 。

查询命令：

```bash
python3 scripts/lingtu_video_publish.py creators --platform tiktok_shop --region US
python3 scripts/lingtu_video_publish.py creators --platform tiktok_shop --has-photo-permission
python3 scripts/lingtu_video_publish.py creators --platform tiktok
python3 scripts/lingtu_video_publish.py products search --creator-username alice --source shop
```

### 2. 自动准备草稿

已有文案优先沿用。没有文案时，根据能确认的素材内容、商品卖点和目标语言生成草稿，不编造折扣或功效，不把文件名当发布文案。通过 `fill` 写入，随方案供用户审核。文案保留标点、表情和hashtag，带货≤4000字符、非带货≤2000；购物车标题仍需去标点和表情并限制30字符。

商品有明确 ID 时自动查找对应标题并预填购物车标题；查不到时保持草稿并说明，不猜商品对应关系。不同素材挂不同商品时通过逐行填值实现。不要随机将多商品分配给素材。

```bash
python3 scripts/lingtu_video_publish.py plan \
  --media-folder /path/to/videos --output-dir /path/to/batch \
  --platform tiktok_shop --creators alice,bob \
  --distribution distribute --date 2026-10-12 --count 2 \
  --product-id PRODUCT_ID --title "Reviewed caption #product"
```

- `--distribution distribute`：按顺序轮流分配，每份素材只发一次。
- `--distribution all`：每个达人发全部素材，方案明确提示重复发布。
- `--count`：每达人每天 1～7 条，素材多时自动延伸日期，不循环复用素材。
- 图文加 `--media-type photo`，支持 `tiktok_shop` 带货或 `tiktok_business` 不带货图文。
- 普通视频用 `--platform tiktok`，不需要商品。
- 日期和时区应按目标市场解释，明确展示当地日期。时区优先按目标市场推断，美国默认美西；用户指定覆盖用 `--timezone EST` 或 IANA。
- `plan` 保存 `schedule.csv`、`plan.json`、`发布方案.md`，引用原素材绝对路径，不复制媒体。已有方案目录不能覆盖。
- 留空文案或商品字段的方案是草稿，不能提交。

用户希望每天不同条数或已经有排期表时，仍可使用旧 `gen-csv`、`fill` 流程。Agent 可以直接编辑 CSV 的素材映射和具体时间，不要求用户操作表格。

```bash
python3 scripts/lingtu_video_publish.py fill --folder /path/to/batch --col title --row 0 --value "Caption A"
python3 scripts/lingtu_video_publish.py fill --folder /path/to/batch --col product_title --auto-product-title
python3 scripts/lingtu_video_publish.py fill --folder /path/to/batch --col product_id --row 1 --value PRODUCT_B
```

`fill` 可按 `--row`（0 为第一条）、`--creator` 或全表填值。CSV 自动商品标题按商品 ID 精确匹配，支持 SHOP/SHOWCASE 分页，查不到保持原值并报告实际更新数。

### 3. 展示可直接确认的方案

```bash
python3 scripts/lingtu_video_publish.py publish --folder /path/to/batch
```

dry-run 不上传素材、不创建发布任务；带货图文会查询达人权限，普通与高级版查询账号当前发布配置；文件夹方案核对账号身份及定时时间。非带货视频需要ffprobe检查账号时长限制。成功校验保存 `review.json`，包含方案内容、素材内容指纹及达人 ID。

向用户展示：

- 总素材数、总任务数、达人分配规则、每人条数、日期范围、当地时区、商品。
- 每条的素材预览（视频或图片）、达人、实际文案、商品/购物车标题、当地时间、校验结果。
- 缺字段、失效账号、错误图片等以“需修改”说明。默认整批阻止；用户明确选择先发可用部分时，准备独立方案再确认，不能静默丢弃错误行。

用户可直接说“第二条换达人”“晚上发”“文案短一点”。Agent 修改 CSV 后重新运行校验，更新并展示方案。确认的是具体内容和数量，不是抽象的“允许发布”。

### 4. 用户确认后提交

```bash
python3 scripts/lingtu_video_publish.py publish --folder /path/to/batch --confirm
```

- 新方案要求先成功预览；内容、媒体内容或账号 ID 变化时拒绝提交，需重新校验并确认。旧 CSV 保持兼容，但 Agent 必须先预览并取得用户确认。
- 同一方案目录加进程锁，防止并发提交。
- 每条提交结果即时保存在 `publish-journal.json`。原方案重跑时跳过已有提交或状态不明的条目。
- 上传/账号等提交前失败可使用 `--confirm --retry-failed` 重试。已提交的任务不会因重复执行而重发。
- 创建请求超时、响应无 postId 或中断，标记为状态不明并阻止自动重发；先核实发布记录，不能将查不到记录等同于未提交。
- 不删除提交记录，不移到新目录绕过去重。去重范围是该方案目录，不保证跨目录或跨设备。
- 方案改变不是修改已经创建的服务端任务。已提交条目的调整必须说明会产生新任务，先处理旧任务；使用 posts detail/update/cancel 管理服务端旧任务，先展示变更再确认。

提交成功只表示任务创建成功。向用户报告“已提交 X 个定时发布任务”、失败或状态不明数量、跳过数量、日期时区，并始终附：
https://app.ailingtu.com/video-center?tab=records

### 5. 查询结果与后续处理

```bash
# 本地记录，不联网
python3 scripts/lingtu_video_publish.py status --folder /path/to/batch
# 按保存的 postId 查询平台状态并保存
python3 scripts/lingtu_video_publish.py status --folder /path/to/batch --refresh
```

- `SUCCESS`、`COMPLETED`：平台成功；`PRE_CHECK_PASSED` 仅预检通过，不报已发布。
- `FAILED`、`SUBMIT_FAILED`、`PRE_CHECK_REJECTED`：报告服务端原因。
- `CANCELLED`：已取消；其他状态显示原始状态并说明仍在流程中。
- 查询失败或没查到记录保留上次状态，并明确本次未确认；没有 postId 的状态不明条目需用户核实发布记录，不能按相似文案猜匹配。
- 本地已提交的任务即使平台随后失败，也不能用 `--retry-failed` 新建重复任务；先审核原因，再通过 posts submit 或 posts reschedule 处理原服务端任务，保留记录。
- 用户问“昨天那批怎么样”时找到该批次目录刷新状态。没有目录上下文时询问批次位置，不猜账号全部记录。
- 用户要求完成提醒时再创建自动跟踪；默认不设定时任务。

## 旧 CSV / XLSX 入口

保留 `gen-csv`（默认每日 3 条，支持 `--daily-counts`）、`creators`、`fill`、`products search`、`publish`。

```bash
python3 scripts/lingtu_video_publish.py gen-csv --platform tiktok --creators alice --date 2026-10-12 --count 2
python3 scripts/lingtu_video_publish.py gen-csv --platform tiktok_shop --media-type photo --creators alice --date 2026-10-12 --product-id PRODUCT_ID
python3 scripts/lingtu_video_publish.py --help
python3 scripts/lingtu_video_publish.py plan --help
```

CSV 中文或英文表头均可，优先 `schedule.csv`，兼容 `schedule.xlsx`。带货表可混排视频与图文。

| 内容 | 字段 |
|---|---|
| 通用 | 达人用户名、平台、视频文案内容、时区、发布时间 |
| 带货 | 产品ID、购物车标题、商品来源（SHOP / SHOWCASE） |
| 视频 | 视频文件名（每行一个，支持绝对路径） |
| 图文 | 媒体类=photo、图片文件名（逗号分隔，顺序即发布顺序） |
| 音乐可选 | 音乐ID、音乐标题、音乐作者、音乐时长 |

图文 1～15 张，单张≤10MB，JPG/JPEG/PNG/WEBP/HEIC/BMP，宽高比 9:16～16:9。视频文件名列不能填图片。购物车标题≤30 字符；带货文案≤4000、非带货≤2000。高级版图文只支持JPG/JPEG/WEBP。非带货视频通过ffprobe校验账号时长，分辨率等其他限制仍由平台判定。

## 配置

所有需要认证的请求只使用 `LINGTU_API_KEY`，并通过 `x-api-key` 请求头发送。
安装不要求认证。执行任务时如果缺少 `LINGTU_API_KEY`，引导用户前往 https://ailingtu.com/api-keys 创建或管理密钥，并在运行 Skill 的环境中配置 `LINGTU_API_KEY` 后重试。不再生成账号绑定授权 URL。
不要索取、展示或保存用户的 API Key。

缺少密钥时，读取 `shared/references/api-key-setup.md`，向用户展示其操作系统对应的完整步骤（如何打开终端、可复制命令、粘贴密钥、重启应用及生效范围），不要只说“配置环境变量”。已知系统时只展示对应部分；未知时同时提供 Mac 和 Windows。配置由用户在自己电脑上完成，不代为读取或填入真实密钥。


环境变量：

| 变量 | 含义 | 默认 |
|------|------|------|
| LINGTU_AI_BASE_URL | API base URL | https://api.ailingtu.com |

## 依赖

- Python 3.9+
- 非带货视频时长检查需要 ffprobe（随 FFmpeg 安装）

默认 CSV 流程不需要第三方依赖。只有读取或编辑旧版 `schedule.xlsx` 时才需要 `openpyxl`。

## 时区

`gen-csv` 的 `--timezone` 可省略。省略时会读取达人授权信息里的 `oauthRegion` / `registerRegion` 推断时区；美国地区默认 `America/Los_Angeles`，如用户要美东则明确传 `--timezone EST` 或 `--timezone America/New_York`。

支持短码 → IANA 映射：

| 短码 | IANA |
|------|------|
| EST | America/New_York |
| PST | America/Los_Angeles |
| CN | Asia/Shanghai |
| JP | Asia/Tokyo |
| KR | Asia/Seoul |
| SG | Asia/Singapore |
| GB | Europe/London |

也可直接使用 IANA 时区字符串（如 `Asia/Bangkok`）。
