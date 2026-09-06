---
name: lingtu-video-publish
slug: lingtu-video-publish
version: 0.2.0
displayName: 灵途批量视频发布
summary: 按 CSV 排期批量发布 TikTok Shop 带货视频、图文和养号内容。
description: 灵途批量视频/图文发布 — 从 CSV 排期表批量向 TikTok Shop / TikTok 养号账号发布视频或带货图文。支持生成 CSV 模板（达人/时间/产品预填）、已授权达人查询、产品搜索、CSV/XLSX 通用读取、dry-run 预览。
license: Apache-2.0
homepage: https://ailingtu.com/skills/video-publish
---

# 灵途批量视频 / 带货图文发布

## 适用场景

当用户在群里说"帮我发布带货视频"、"批量发布视频"、"我要发视频"、"发布图文"、"带货图文"、"多图带货"、"生成排期表"等需求时调用本技能。

## Bot 调用指南

当用户触发关键词（帮我发布视频 / 我要发视频 / 发布带货视频 / 批量发布）时，先查询当前用户的已授权达人列表，并从返回结果里取 2-3 个真实用户名作为示例；不要在话术里写死示例达人。

如果用户说要绑定 TikTok 店铺，或查询 TikTok Shop 店铺商品时发现没有店铺/没有店铺商品，让用户打开 https://app.ailingtu.com/teamshop 完成 TikTok Shop 店铺绑定。

如果查询 TikTok Shop 带货达人或普通 TikTok 发布达人时发现没有已授权达人、达人未找到或未授权，让用户打开 https://app.ailingtu.com/video-post 完成达人授权。授权完成后再回来继续生成排期或发布。

美国带货视频示例查询：

```bash
python3 scripts/lingtu_video_publish.py creators \
  --platform tiktok_shop \
  --region US
```

仅可发带货图文的达人（服务端 `hasPhotoPermission=true`）：

```bash
python3 scripts/lingtu_video_publish.py creators \
  --platform tiktok_shop \
  --region US \
  --has-photo-permission
```

普通视频 / 养号视频示例查询：

```bash
python3 scripts/lingtu_video_publish.py creators \
  --platform tiktok
```

拿到列表后再**一次性引导**收集信息：

```
收到，生成发布排期表需要以下信息：

① 发布类型
   A. TikTok 带货视频   B. TikTok 不带货视频   C. TikTok Shop 带货图文（多图挂车）

② 要发布的达人名字，以及带货的话每个达人带什么产品
   示例：达人 <从你的授权列表里取 2-3 个用户名> 带产品 176118111232433423
   （不写达人 = 拉取全部已授权达人）
   发布美国带货视频时，不写达人可直接筛选带货达人列表里的美国达人。
   发布美国普通视频 / 养号视频 / 不带货视频时，达人列表不能按国家筛选；不需要产品 ID，地区只用于默认时区。

③ 时区（可选）
   默认按达人授权区域自动选择：美国达人默认美西 America/Los_Angeles。
   用户可指定覆盖，例如美东时间（EST / America/New_York）。

④ 发布频率：每天发几条、发哪几天
   示例：每天 2 条，7 月 5 号开始发 3 天
   如果不同日期条数不同，也要生成同一个排期文件夹，不要拆多个文件夹。
   示例：7 月 6 号各发 2 条，7 月 7 号各发 3 条

发布时间不用让用户指定。默认按早上 / 中午 / 晚上三档分配，并按达人错开分钟，避免完全重合；用户后续可在 CSV 的「发布时间」列自行修改。

⑤ 产品信息（选 ①-A 的话需要产品 ID）
   如果你给我产品 ID，我可以搜到产品标题帮你预填。
   购物车标题也可以你自己后续在 CSV 里补充。

你可以直接这样告诉我：
"带货，达人 <授权列表里的达人A>、<授权列表里的达人B> 带产品 176118111232433423，
 每天 2 条，7 月 5 号起 3 天"
```

用户补齐信息后调用 gen-csv（不足的用默认值：每达人每天 3 条、全部已授权达人）：

```bash
# 带货视频
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok_shop \
  --region US \
  --creators "<授权列表里的达人A>,<授权列表里的达人B>" \
  --date 2026-07-05 \
  --days 3 \
  --count 2 \
  --product-id 176118111232433423

# 带货图文（多图挂车）
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok_shop \
  --media-type photo \
  --region US \
  --creators "<授权列表里的达人A>" \
  --date 2026-07-05 \
  --count 1 \
  --product-id 176118111232433423
```

如果用户指定了不同日期的不同条数，优先用 `--daily-counts` 生成一份 CSV：

```bash
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok \
  --region US \
  --creators "<授权列表里的达人A>,<授权列表里的达人B>" \
  --date 2026-07-06 \
  --daily-counts 2026-07-06=2,2026-07-07=3
```

如果用户明确指定美东、美西或其他时区，再传 `--timezone EST|PST|IANA` 覆盖自动推断。

**生成结果返回给用户：**

```
已在桌面生成排期文件夹：视频发布_2026-07-05_to_2026-07-07/
  ├── schedule.csv  ← 排期表，达人/时间已填好
  └── （请把视频文件拖进这个文件夹）

如果是 TikTok 不带货视频，打开 schedule.csv，只需要填：
  · 视频文案内容 — 视频的 caption，最多 4000 字符，不支持表情、标点或特殊符号；`#` 可用于 hashtag
  · 视频文件名 — 拖进来的视频文件名，如 video1.mp4

如果是 TikTok Shop 带货视频，打开 schedule.csv，你需要填：
  · 购物车标题 — 产品展示名，最多 30 字符，不支持表情、标点或特殊符号
  · 视频文案内容 — 视频的 caption，最多 4000 字符，不支持表情、标点或特殊符号；`#` 可用于 hashtag
  · 视频文件名 — 拖进来的视频文件名，如 video1.mp4

如果是 TikTok Shop 带货图文，打开 schedule.csv，你需要填：
  · 购物车标题 — 产品展示名，最多 30 字符
  · 视频文案内容 — caption，最多 4000 字符；`#` 可用于 hashtag
  · 图片文件名 — 多图用英文逗号分隔，如 a.jpg,b.jpg,c.png（顺序即发布顺序）
  · 图片约束 — 1～15 张；单张 ≤10MB；JPG/JPEG/PNG/WEBP/HEIC/BMP；宽高比 9:16～16:9
  · 音乐（可选）— 音乐ID / 音乐标题 / 音乐作者 / 音乐时长

然后我帮你填表，不用自己手动改 CSV。
```

### 第三步：自动填表

用户确认预览后，调用 gen-csv 生成 CSV。然后主动帮用户填。

不带货视频的 CSV 不应出现「产品ID」「购物车标题」「商品来源」三列；只需要填视频文案和视频文件名。

**1. 购物车标题 — 仅带货视频需要，自动从产品信息填入：**

```bash
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/视频发布_2026-07-05_to_2026-07-07 \
  --col product_title --auto-product-title
```

带货视频填完后告知用户：
```
购物车标题已从产品信息自动填入 ✓
```

**2. 视频文案 — 问用户后批量填：**

```
视频文案内容要统一吗？
统一的话告诉我一句话（如 "Summer Sale 2026"），我帮你填到所有行。
```

用户回复后：

```bash
# 统一文案
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col title --value "Summer Sale 2026"

# 按达人不同文案
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col title --creator <授权列表里的达人A> --value "文案A"

# 指定某行
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col title --row 0 --value "第一条文案"
```

**3. 媒体文件名 — 用户告知后填：**

```
视频/图片拖进文件夹了吗？告诉我文件名对应哪行就行。
图文多图用逗号：a.jpg,b.jpg
```

```bash
# 视频：按达人填
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col video_file --creator <授权列表里的达人A> --value "video1.mp4"

# 视频：按行填
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col video_file --row 0 --value "video1.mp4"

# 图文：按行填多图
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col image_files --row 0 --value "a.jpg,b.jpg"
```

全部填完后展示最终排期表，用户确认即发布。

用户编辑 CSV 时可能新增或删除行。行数变化本身不算失败；如果新增行缺字段或格式不对，dry-run / confirm 阶段只提示「需修改」，让用户补齐或删除该行后再确认发布，不要把它表述为发布失败。

### 第四步：执行发布

用户说"发布"或"确认发布"，先 dry-run 校验：

```bash
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05_to_2026-07-07
```

校验结果贴给用户。无问题后加 `--confirm`：

```bash
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05_to_2026-07-07 \
  --confirm
```

返回每条结果：成功 → postId + status，失败 → 原因。

发布完成后必须给用户这段信息，并且必须包含发布记录链接：

```
发布完成，发布 X 条 XX 视频/图文。
发布基本信息：类型、达人、发布时间范围、成功/失败数量。
请前往发布记录确认发布内容：
https://app.ailingtu.com/video-center?tab=records
```

---

## 命令参考

### gen-csv — 生成排期模板

在桌面创建文件夹，内含 `schedule.csv`。
`tiktok_shop` 带货视频会生成带货字段，用户需补「购物车标题」「视频文案内容」「视频文件名」。
`tiktok_shop --media-type photo` 带货图文会生成「图片文件名」与可选音乐列，用户需补「购物车标题」「视频文案内容」「图片文件名」。
`tiktok` 不带货视频不会生成「产品ID」「购物车标题」「商品来源」三列，用户只需补「视频文案内容」「视频文件名」。
购物车标题最多 30 字符，不支持表情、标点或特殊符号；视频文案内容最多 4000 字符，不支持表情、标点或特殊符号，但 `#` 可用于 hashtag。

```
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform {tiktok_shop,tiktok} \
  [--media-type video|photo] \
  --date YYYY-MM-DD \
  [--timezone EST|PST|CN|...] \
  [--region US|GB|JP|...] \
  [--creators "@a,@b"] \
  [--days 1] \
  [--count 3] \
  [--daily-counts YYYY-MM-DD=N,YYYY-MM-DD=N] \
  [--product-id xxx] \
  [--output-dir /custom/path]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| --platform | 是 | tiktok_shop（带货）或 tiktok（养号） |
| --media-type | 否 | video（默认）或 photo（带货图文，仅 tiktok_shop） |
| --date | 是 | 起始日期 YYYY-MM-DD |
| --timezone | 否 | 时区短码或 IANA。不传则按达人授权区域推断；美国默认美西 |
| --region / --country | 否 | 目标地区。`tiktok_shop` 且不指定达人时用于筛选带货达人列表；`tiktok` 普通/养号视频不筛选列表，仅用于默认时区 |
| --creators | 否 | 逗号分隔达人，不传=全部已授权 |
| --days | 否 | 连续发布天数，默认 1 |
| --count | 否 | 每达人每日条数，默认 3 |
| --daily-counts | 否 | 按日期指定每达人条数，如 `2026-07-06=2,2026-07-07=3`；传入后生成同一个文件夹和一份 CSV |
| --product-id | 仅带货 | 产品 ID |
| --output-dir | 否 | 自定义输出目录，默认桌面 |

### creators — 查看已授权达人

```
python3 scripts/lingtu_video_publish.py creators \
  [--platform tiktok_shop|tiktok] \
  [--region US] \
  [--username keyword] \
  [--format json|text]
```

`creators --region` 仅对 `--platform tiktok_shop` 生效；普通 TikTok / 养号达人列表当前不支持按国家筛选。

### fill — 更新 CSV 单元格

用于 bot 根据对话自动填表，用户无需手动编辑 CSV。

```
# 自动从产品 API 搜索并填入购物车标题
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... \
  --col product_title --auto-product-title

# 所有行统一值
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col title --value "Summer Sale"

# 按达人筛选填充
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col title --creator <授权列表里的达人A> --value "文案A"

# 指定行填充（--row 0 = 第一行数据）
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col video_file --row 0 --value "video1.mp4"
```

| 参数 | 说明 |
|------|------|
| --folder | 排期文件夹路径 |
| --col | 列名（英文 key 或中文名均可） |
| --value | 填充的值 |
| --auto-product-title | 自动搜产品填购物车标题 |
| --creator | 只填充指定达人的行 |
| --row | 只填充指定行（0=第一行数据） |

### publish — 执行发布

```
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05_to_2026-07-07 \
  [--date YYYY-MM-DD] \
  [--confirm] \
  [--sleep-ms 500] \
  [--format json|text]
```

**安全机制**：不加 `--confirm` 为 dry-run 模式，只校验不发请求。

### products search — 搜索商品

```
python3 scripts/lingtu_video_publish.py products search \
  --creator-username @daren \
  [--source shop|showcase] \
  [--keyword "关键词"] \
  [--format json|text]
```

---

## CSV 排期表格式

### TikTok 不带货视频

| 列 | 预填 | 用户操作 |
|----|------|----------|
| 达人用户名 | 达人用户名 | 不改 |
| 平台 | tiktok | 不改 |
| 视频文案内容 | 空 | **用户填**；最多 4000 字符，不支持表情、标点或特殊符号，`#` 可用于 hashtag |
| 时区 | 如 America/Los_Angeles | 可改 |
| 发布时间 | YYYY-MM-DD HH:MM；默认早/中/晚并按达人错峰 | 可改 |
| 视频文件名 | 空 | **用户填** |

### 媒体类（可写）

排期表列名：**媒体类**（兼容旧表头 **媒体类型**）。

| 可写值 | 含义 |
|--------|------|
| `video` / `视频` / `带货视频` / 空 | 视频（默认） |
| `photo` / `图文` / `图片` / `带货图文` | 带货图文 |

同一张 `tiktok_shop` 表里可混排：某行写 `photo` + 图片文件名，某行写 `video` + 视频文件名。

规则（避免填错列却走错链路）：

- 图文：写 **媒体类=photo**（或只填 **图片文件名** 且媒体类为空），图片必须在「图片文件名」
- 视频：媒体类=video 或空，文件只写在「视频文件名」
- **不会**因为「视频文件名」是 `.jpg` 就自动当图文；会提示把图改到「图片文件名」并设媒体类

### TikTok Shop 带货视频

| 列 | 预填 | 用户操作 |
|----|------|----------|
| 达人用户名 | 达人用户名 | 不改 |
| 平台 | tiktok_shop | 不改 |
| 媒体类 | video | 可改为 photo |
| 产品ID | 产品 ID | 可改 |
| 购物车标题 | 空 | **用户填**；最多 30 字符，不支持表情、标点或特殊符号 |
| 商品来源 | SHOP | 可改为 SHOWCASE |
| 视频文案内容 | 空 | **用户填**；最多 4000 字符，不支持表情、标点或特殊符号，`#` 可用于 hashtag |
| 时区 | 如 America/Los_Angeles | 可改 |
| 发布时间 | YYYY-MM-DD HH:MM；默认早/中/晚并按达人错峰 | 可改 |
| 视频文件名 | 空 | **用户填** |

### TikTok Shop 带货图文（media-type=photo）

| 列 | 预填 | 用户操作 |
|----|------|----------|
| 达人用户名 | 达人用户名 | 不改 |
| 平台 | tiktok_shop | 不改 |
| 媒体类 | photo | 可改 |
| 产品ID | 产品 ID | 可改 |
| 购物车标题 | 空 | **用户填** |
| 商品来源 | SHOP | 可改为 SHOWCASE |
| 视频文案内容 | 空 | **用户填** caption |
| 时区 | 如 America/Los_Angeles | 可改 |
| 发布时间 | YYYY-MM-DD HH:MM | 可改 |
| 图片文件名 | 空 | **用户填**；多图逗号分隔，如 `a.jpg,b.jpg`；1～15 张 |
| 音乐ID | 空 | 可选 |
| 音乐标题 | 空 | 可选 |
| 音乐作者 | 空 | 可选 |
| 音乐时长 | 空 | 可选（秒） |

图片硬性约束（publish dry-run / confirm 会校验）：

- 张数：至少 1 张，最多 15 张
- 单张大小：≤ 10MB
- 格式：JPG, JPEG, PNG, WEBP, HEIC, BMP
- 宽高比：9:16 ～ 16:9（含边界）

达人资格（发图文必须同时满足）：

- 账号来自 **TikTok Shop** 授权（`authSource` 含 TIKTOK_SHOP），不能用 Login Kit 养号号发图文
- `permissions` 中包含 **`PHOTO_SHOPPABLE_PERMISSION_PRODUCT`**

`creators` 列表会标注是否可发图文；`gen-csv --media-type photo` 只排可发图文的达人。

API 映射（多图单挂车）：

- `businessId` = **首图** fileId（CSV `图片文件名` 逗号列表第 1 个）
- `tiktokShopPhoto.businessIds` = **全部**图片 fileId，**按用户填写/上传顺序**
- `tiktokShopPhoto.productLinks` = **有且仅有 1 个产品**（CSV 一行一个 product_id）
- `postType` = `MULTI_PHOTO_ONE_ANCHOR`
- 可选 `musicInfo`

---

## 配置

认证只使用 `LINGTU_API_KEY` 环境变量。缺少 Key 时，直接给用户对应系统的命令，让用户在自己的电脑上执行；不要要求用户把真实 Key 发到聊天中。

macOS（当前终端会话）：

```bash
export LINGTU_API_KEY='your-api-key'
```

macOS 如需永久生效，把同一行加入 `~/.zshrc`，然后执行 `source ~/.zshrc`。

Windows PowerShell（当前窗口）：

```powershell
$env:LINGTU_API_KEY = "your-api-key"
```

Windows 如需永久生效，执行 `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")`，然后重新打开终端。

环境变量：

| 变量 | 含义 | 默认 |
|------|------|------|
| LINGTU_AI_BASE_URL | API base URL | https://api.ailingtu.com |

## 依赖

- Python 3.9+

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
