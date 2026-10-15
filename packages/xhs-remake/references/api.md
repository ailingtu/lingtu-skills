# 接口与脚本约定

## 公共配置

- Base URL：`https://api.ailingtu.com`
- 认证：`x-api-key: <LINGTU_API_KEY>`
- 成功：HTTP 2xx，响应 `code === 0`
- 本技能只从环境读取 `LINGTU_API_KEY`

## 下载小红书图文

调用 `POST /v1/material/fetch`：

```json
{"videoUrl": "https://www.xiaohongshu.com/explore/..."}
```

图文响应使用 `data.imageList`，按原顺序保存每个 `url`；列表为空且没有视频地址时可保存 `coverUrl`。若 `materialType` 为 `VIDEO` 或只返回视频直链，停止并说明首版不支持视频笔记。图片 CDN 地址短时有效，立即下载；下载时不携带 `x-api-key`。

```bash
python3 scripts/lingtu_video_download.py download \
  --video-url 'XIAOHONGSHU_URL' \
  --photo-only \
  --output /absolute/path/to/work-dir/reference \
  --metadata /absolute/path/to/work-dir/reference/metadata.json
```

脚本名称沿用共享下载运行时；本技能只接受小红书图文链接，不因脚本支持其他平台而扩大范围。

## 建立素材清单

```bash
python3 scripts/lingtu_xhs_manifest.py \
  --material /absolute/path/to/material-folder \
  --material /absolute/path/to/selected-image.jpg \
  --output /absolute/path/to/work-dir/assets-manifest.json
```

支持 JPG、PNG、WebP、GIF、HEIC、HEIF 和 AVIF。脚本记录绝对路径、字节数、SHA-256、可读取的尺寸及内容重复项；语义描述必须在实际查看图片后补入 `assets-analysis.json`。

## 图片生成

本包自带 `scripts/lingtu_content_task.py`。本地参考图先通过 `POST /v1/file/presign` → `PUT` 原始字节到 `data.uploadUrl`（不携带 `x-api-key`）→ `POST /v1/file/confirm` 上传（`isNew=false` 时复用已有文件，跳过 PUT 和 confirm），使用返回的 `data.url`；生成调用 `POST /v1/ai/schedule/create`：

```json
{
  "type": "IMAGE_GENERATION",
  "params": {
    "prompt": "...",
    "model": "gpt-image-2.5-ext-flare",
    "aspectRatio": "3:4",
    "size": "1920x1080",
    "inputReferences": ["https://static.ailingtu.com/..."]
  },
  "nums": 1
}
```

`gpt-image-2.5-ext-*` 必须同时传清晰度对应的具体 `size`：1080P 为
`1920x1080`、2K 为 `2560x1440`、4K 为 `3840x2160`。画面比例仍由
`aspectRatio` 决定。脚本用 `--image-quality 1080P|2K|4K` 选择，默认 1080P。

创建后通过 `GET /v1/ai/task/listByScheduleId?scheduleId=...` 轮询。`scheduleId` 与 `taskId` 不可混用。同一请求遇到未知响应或超时不能自动改走另一创建路径再次提交。

接口发生供应商失败、超时、未知响应或意外错误时，向用户显示：`生成失败或遇到未知问题，请联系开发者：微信 yh8000m`，并保留已成功页面。
