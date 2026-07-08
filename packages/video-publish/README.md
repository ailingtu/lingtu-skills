# 灵途批量视频发布

从 CSV 排期表批量向 TikTok Shop / TikTok 养号账号发布视频。

## 快速开始

```bash
# 1. 生成 CSV 排期模板（在桌面创建文件夹）
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok_shop \
  --region US \
  --date 2026-07-05 \
  --product-id pid_001234

# 2. 编辑 schedule.csv（填 title + video_file），视频拖入文件夹

# 3. dry-run 预览
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05

# 4. 确认发布
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05 \
  --confirm
```

不传 `--timezone` 时会按达人授权区域自动推断时区；美国达人默认美西。需要美东等指定时区时再传 `--timezone EST`。`--region US` 对带货达人列表生效；普通 TikTok / 养号视频不按国家筛选列表，且不需要产品 ID。

不同日期发布条数不同时，仍生成一个排期文件夹和一份 CSV：

```bash
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok \
  --region US \
  --date 2026-07-06 \
  --daily-counts 2026-07-06=2,2026-07-07=3
```

## 命令

| 命令 | 说明 |
|------|------|
| gen-csv | 生成 CSV 排期模板 |
| creators | 列出已授权达人 |
| publish | 执行发布 |
| products search | 搜索商品 |

## 依赖

- Python 3.9+

默认 CSV 流程不需要第三方依赖；只有读取或编辑旧版 `schedule.xlsx` 时才需要 `openpyxl`。

## 配置

认证通过 `LINGTU_API_KEY` 环境变量，OpenClaw 自动注入。本地 CLI 自行 export：

```bash
export LINGTU_API_KEY=xxx
```

没有 API Key 时生成绑定链接：

```bash
python3 shared/scripts/user_keys.py single bind
```
