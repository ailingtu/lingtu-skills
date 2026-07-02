---
name: lingtu-video-publish
version: 0.1.0
description: 灵途批量视频发布 — 从 Excel 排期表批量向 TikTok Shop / TikTok 养号账号发布视频。支持生成 Excel 模板（达人/时间/产品预填）、已授权达人查询、产品搜索、XLSX/CSV 通用读取、dry-run 预览。
---

# 灵途批量视频发布

## 适用场景

当用户在群里说"帮我发布带货视频"、"批量发布视频"、"我要发视频"、"生成排期表"等需求时调用本技能。

## Bot 调用指南

当用户触发关键词（帮我发布视频 / 我要发视频 / 发布带货视频 / 批量发布）时，**一次性引导**收集信息：

```
收到，生成视频发布排期表需要以下信息：

① 发布类型
   A. TikTok 带货视频   B. TikTok 不带货视频

② 要发布的达人名字，以及带货的话每个达人带什么产品
   示例：达人 vacbirdusa、vacbird.life 带产品 176118111232433423
   （不写达人 = 拉取全部已授权达人）

③ 发布时间和时区
   示例：美西时间（PST）、美东时间（EST）、北京时间（CN）

④ 发布频率：每天发几条、发哪几天
   示例：每天 2 条，7 月 5 号开始发 3 天

⑤ 产品信息（选 ①-A 的话需要产品 ID）
   如果你给我产品 ID，我可以搜到产品标题帮你预填。
   购物车标题也可以你自己后续在 Excel 里补充。

你可以直接这样告诉我：
"带货，达人 vacbirdusa、vacbird.life 带产品 176118111232433423，
 美西时间，每天 2 条，7 月 5 号起 3 天"
```

用户补齐信息后调用 gen-csv（不足的用默认值：每达人每天 3 条、全部已授权达人）：

```bash
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok_shop \
  --creators "vacbirdusa,vacbird.life" \
  --date 2026-07-05 \
  --days 3 \
  --count 2 \
  --product-id 176118111232433423 \
  --timezone PST
```

**生成结果返回给用户：**

```
已在桌面生成排期文件夹：视频发布_2026-07-05_to_2026-07-07/
  ├── schedule.xlsx  ← 排期表，达人/产品/时间已填好
  └── （请把视频文件拖进这个文件夹）

打开 schedule.xlsx，你只需要填：
  · 购物车标题 — 产品展示名（不填也行，我帮你从产品信息里取）
  · 视频文案内容 — 视频的 caption
  · 视频文件名 — 拖进来的视频文件名，如 video1.mp4

然后我帮你填表，不用自己打开 Excel 改。
```

### 第三步：自动填表

用户确认预览后，调用 gen-csv 生成 Excel。然后主动帮用户填：

**1. 购物车标题 — 自动从产品信息填入：**

```bash
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/视频发布_2026-07-05_to_2026-07-07 \
  --col product_title --auto-product-title
```

告知用户：
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
  --folder ~/Desktop/... --col title --creator vacbirdusa --value "文案A"

# 指定某行
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col title --row 0 --value "第一条文案"
```

**3. 视频文件名 — 用户告知后填：**

```
视频文件拖进文件夹了吗？告诉我文件名对应哪行就行。
```

```bash
# 按达人填
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col video_file --creator vacbirdusa --value "bird1.mp4"

# 按行填
python3 scripts/lingtu_video_publish.py fill \
  --folder ~/Desktop/... --col video_file --row 0 --value "video1.mp4"
```

全部填完后展示最终排期表，用户确认即发布。

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

---

## 命令参考

### gen-csv — 生成排期模板

在桌面创建文件夹，内含 `schedule.xlsx`（达人/产品/时间预填），用户只需补「购物车标题」「视频文案内容」「视频文件名」三列。

```
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform {tiktok_shop,tiktok} \
  --date YYYY-MM-DD \
  --timezone EST|PST|CN|... \
  [--creators "@a,@b"] \
  [--days 1] \
  [--count 3] \
  [--product-id xxx] \
  [--output-dir /custom/path]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| --platform | 是 | tiktok_shop（带货）或 tiktok（养号） |
| --date | 是 | 起始日期 YYYY-MM-DD |
| --timezone | 是 | 时区短码或 IANA |
| --creators | 否 | 逗号分隔达人，不传=全部已授权 |
| --days | 否 | 连续发布天数，默认 1 |
| --count | 否 | 每达人每日条数，默认 3 |
| --product-id | 仅带货 | 产品 ID |
| --output-dir | 否 | 自定义输出目录，默认桌面 |

### creators — 查看已授权达人

```
python3 scripts/lingtu_video_publish.py creators \
  [--platform tiktok_shop|tiktok] \
  [--username keyword] \
  [--format json|text]
```

### fill — 更新 Excel 单元格

用于 bot 根据对话自动填表，用户无需手动编辑 Excel。

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
  --folder ~/Desktop/... --col title --creator vacbirdusa --value "文案A"

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

## Excel 排期表格式

| 列 | 预填 | 用户操作 |
|----|------|----------|
| 达人用户名 | 达人用户名 | 不改 |
| 平台 | tiktok_shop/tiktok | 可改 |
| 产品ID | 产品 ID | 可改 |
| 购物车标题 | 空 | **用户填** |
| 视频文案内容 | 空 | **用户填** |
| 时区 | 如 America/Los_Angeles | 可改 |
| 发布时间 | YYYY-MM-DD HH:MM | 可改 |
| 视频文件名 | 空 | **用户填** |

---

## 配置

单用户模式绑定管理员：

```bash
python3 shared/scripts/user_keys.py single bind
```

环境变量：

| 变量 | 含义 | 默认 |
|------|------|------|
| LINGTU_AI_BASE_URL | API base URL | https://api.ailingtu.com |

多用户 bot 模式，传入 `--channel feishu|wechat --user-id <external-user-id>`。

## 依赖

- Python 3.9+
- openpyxl（~249KB）

安装：`pip install openpyxl`

## 时区

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
