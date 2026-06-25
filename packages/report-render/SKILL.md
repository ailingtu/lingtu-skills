---
name: lingtu-report-render
version: 0.2.0
description: 报告 JSON 转长图分享。把灵途各类结构化报告（店铺日报、流量分析、达人/竞品监控、异常预警等）渲染成可直接发飞书/微信的 PNG 长图。在其他技能返回 JSON 后调用，或用户提到"图片版"/"日报图"/"长图"/"截图"/"分享图"/"导出图片"/"做张卡片"时使用。
---

# 报告 JSON 转长图分享

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Overview

Turns a structured JSON payload (or just a few fields) into a single PNG long-image suitable for sharing in Feishu, WeChat, or DMs.

Two render modes:

- **`fill`** (default): plug data into a placeholder template (`<id>.template.html`) using a tiny stdlib engine. No AI call — fast, deterministic, free. Best when you already know the field names.
- **`ai`**: send a reference template (`<id>.example.html`) plus the data to `POST /v1/ai/chat/complete` (`roleId=html_design`, `promptId=html_design_basic`). The model emits a full HTML document modelled after the reference. Slower, more flexible when the data shape is still moving.

Both modes flow through the same pipeline:

```
data → render (fill | ai) → sanitize HTML → number-fidelity check → Playwright screenshot → PNG
```

If anything fails — backend down, malformed HTML, missing numbers — the renderer falls back to a minimal white-card view and still produces a PNG. Calling skills never need to handle errors themselves.

Read `references/api.md` before changing endpoint paths or response parsing. Read `references/design_system.md` before changing visual rules. Read `templates/<id>.example.html` and `templates/<id>.template.html` before changing per-template layout.

## When to invoke

Invoke this skill **after** a business skill (tkshop-query, social-monitor, content-create, …) has produced structured JSON, OR when the user just wants to drop a few fields into a card. Pass the JSON via `--data`. The agent picks the matching `--template`.

| Template id        | Use case                                        | fill | ai      |
|--------------------|-------------------------------------------------|------|---------|
| `daily_report`     | Shop daily report from tkshop-query             | ✓    | ✓       |
| `creator_monitor`  | Creator / competitor monitoring summary         | —    | planned |
| `traffic_analysis` | Shop traffic analysis                           | —    | planned |
| `alert`            | Anomaly / threshold alert                       | —    | planned |

When in doubt, default to `daily_report` + `fill`.

## Template files

Per template id, the package may carry up to two files:

- `<id>.template.html` — placeholder template for `fill` mode. Uses `{{ var }}`, `{{ var.sub }}`, `{% if var %}…{% endif %}`, `{% for x in xs %}…{% endfor %}`. Auto HTML-escapes substitutions.
- `<id>.example.html` — reference HTML for `ai` mode. A hand-tuned, complete document with realistic example data so the model can mimic it.

If only one of the two exists, the renderer falls back to whichever is available. Both should reflect the same visual design from `references/design_system.md`.

## Fill-mode schema for `daily_report`

All fields are optional — sensible defaults fill in. Any section without data is hidden, so you can pass as little as `{"title":"今日小报"}` and still get a clean image.

```json
{
  "title": "🛒 店铺日报",
  "subtitle": "2026-06-09 · 灵途旗舰店",
  "summary_emoji": "🚀",
  "summary": "昨日 GMV 环比上升 18.4%，主要由直播间转化拉动。",
  "metrics_title": "核心指标",
  "metrics": [
    {"label": "GMV",   "value": "¥128,450", "delta": "↑ 18.4%", "trend": "up"},
    {"label": "订单数", "value": "1,284",   "delta": "↑ 12.1%", "trend": "up"},
    {"label": "客单价", "value": "¥99.9",   "delta": "→ 0.3%",  "trend": "flat"},
    {"label": "退款率", "value": "4.7%",    "delta": "↓ 0.6pp", "trend": "down"}
  ],
  "insights_title": "今日洞察",
  "insights": [
    "直播间「夏日清凉套装」点击率达 7.8%。",
    "SKU-2384 库存仅剩 3 天用量，建议补单。"
  ],
  "footer": "Powered by Lingtu · 2026-06-10 09:12"
}
```

`trend` accepts `up | down | flat` (controls color). 2/3/4-column grids are picked automatically by metric count.

## Configuration

Same authentication pattern as the other Lingtu skills. Only `ai` mode needs the key — `fill` mode runs offline.

Single-user mode uses a configured administrator binding. Generate the administrator `/binduser` URL before using `ai` mode:

```bash
python3 shared/scripts/user_keys.py single bind
```

Open the returned link to bind the administrator's key.

For multi-user bot mode, pass `--channel feishu|wechat --user-id <external-user-id>` when using `--mode ai`. The script resolves the user's key from `~/.lingtu-skills/config.json`, or calls the backend binding check endpoint if the local key is missing. Use `shared/scripts/user_keys.py bind` to generate the `/binduser` URL.

## Install (one-time)

The renderer needs Playwright with the bundled Chromium:

```bash
pip install playwright
playwright install chromium
```

About 300MB the first time, once per machine.

## CLI Usage

Minimal — just a few words, no AI:

```bash
python3 scripts/lingtu_report_render.py \
  --template daily_report \
  --data '{"title":"今日小报","summary":"一切正常"}'
```

Full daily-report fill mode:

```bash
python3 scripts/lingtu_report_render.py \
  --template daily_report \
  --data daily.json
```

Pipe from another skill:

```bash
python3 packages/tkshop-query/scripts/lingtu_shop_data.py \
  daily-report --date 2026-06-09 \
| python3 packages/report-render/scripts/lingtu_report_render.py \
    --template daily_report \
    --data - \
    --out /tmp/shop-2026-06-09.png
```

Switch to AI mode (after backend is wired up):

```bash
python3 scripts/lingtu_report_render.py \
  --template daily_report \
  --mode ai \
  --data daily.json
```

Useful flags:

- `--mode {fill,ai}`: render path. Defaults to `fill`. Override globally with `LINGTU_REPORT_MODE`.
- `--out <path>`: explicit output PNG path. Default `output/<template>-<timestamp>.png`.
- `--strict-numbers`: fall back if any numeric value from `data` is missing from the rendered HTML. Off by default — warns instead.
- `--debug-html <path>`: dump the final HTML to disk before screenshot.

## Output

The script prints a single JSON to stdout:

```json
{
  "success": true,
  "image": "/abs/path/to/output.png",
  "mode": "fill",
  "fallback": null,
  "elapsed_seconds": 0.42
}
```

`fallback` is `null` on the happy path or a short reason string when fallback rendering kicked in.

## Adding a new template

1. Decide which modes you need:
   - For `fill`, write `templates/<id>.template.html` using the placeholder syntax above.
   - For `ai`, write `templates/<id>.example.html` — a hand-tuned, complete document with realistic example data.
2. Both files should reflect the same design system tokens (`references/design_system.md`).
3. If your template has unusual fields, extend `apply_defaults()` in `scripts/lingtu_report_render.py` so callers can pass tiny payloads without errors.
4. Add a row to the template table above.
