# 灵途批量视频发布

从 Excel 排期表批量向 TikTok Shop / TikTok 养号账号发布视频。

## 快速开始

```bash
# 1. 生成排期模板（在桌面创建文件夹）
python3 scripts/lingtu_video_publish.py gen-csv \
  --platform tiktok_shop \
  --date 2026-07-05 \
  --timezone EST \
  --product-id pid_001234

# 2. 编辑 schedule.xlsx（填 title + video_file），视频拖入文件夹

# 3. dry-run 预览
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05

# 4. 确认发布
python3 scripts/lingtu_video_publish.py publish \
  --folder ~/Desktop/视频发布_2026-07-05 \
  --confirm
```

## 命令

| 命令 | 说明 |
|------|------|
| gen-csv | 生成 Excel 排期模板 |
| creators | 列出已授权达人 |
| publish | 执行发布 |
| products search | 搜索商品 |

## 依赖

- Python 3.9+
- openpyxl

## 配置

```bash
python3 shared/scripts/user_keys.py single bind
```
