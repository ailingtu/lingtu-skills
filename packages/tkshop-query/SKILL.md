---
name: lingtu-tkshop-query
version: 0.2.0
description: TK 店铺数据查询与日报。通过灵途 AI 接口查询 TK 店铺/商家/商品/订单/客户表现等经营数据，支持按日期或店铺名拉取单店日报、按日期拉取全部店铺汇总日报、列出店铺清单，以及向 AI 提问店铺经营相关问题。用户提到"店铺日报"、"店铺数据"、"经营情况"、"整体经营"、"全部店铺汇总"、"大盘"、"GMV/订单/客单价"等场景时使用。
---

# TK 店铺数据查询与日报

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Overview

Use this skill for TK shop/store data lookup and analysis requests.

Supported API flows:

- Shop daily report: `GET /v1/report/biz/detail?targetType=SHOP&targetId={shop_id}&reportDate={YYYY-MM-DD}`.
- All-shops summary report: `GET /v1/report/biz/summary?reportDate={YYYY-MM-DD}`.
- Shop list: `GET /v1/shop/list`.
- AI business question: `POST /v1/ai/chat/create`, streaming response.

Read `references/api.md` before changing endpoint paths, request fields, response fields, or streaming parsing. Use `scripts/lingtu_shop_data.py` for deterministic calls.

## Configuration

Use the same authentication pattern as `lingtu-content-create`.

Single-user mode uses a configured administrator binding. Generate the administrator `/binduser` URL before making requests:

```bash
python3 shared/scripts/user_keys.py single bind
```

Open the returned link to bind the administrator's key. Send the resolved key as the request header `x-api-key: <key>`. Do not store user API keys in this skill directory or commit them to source control.

For multi-user bot mode, pass `--channel feishu|wechat --user-id <external-user-id>` to `scripts/lingtu_shop_data.py` subcommands. The script resolves the user's key from `~/.lingtu-skills/config.json`, or calls the backend binding check endpoint if the local key is missing. Use `shared/scripts/user_keys.py bind` to generate the `/binduser` URL.

Use `https://api.ailingtu.com` as the default base URL unless a future API reference specifies another host.

## Workflow

1. Classify the request.
   - If the user asks about overall / cross-shop operations without naming a specific shop ("整体经营情况"、"全部店铺数据汇总"、"大盘"、"总 GMV/订单"、"所有店"、"全店"、"多店汇总" 等), use the summary report flow.
   - If the user asks for a specific shop's daily report (gives a shop name or shop id, or says "某店日报"), use the daily report flow.
   - If the user asks to list shops, use the shop list flow.
   - If the user asks a shop operations/business question and is not asking to fetch a specific daily report, use the AI chat flow.
   - If the user is ambiguous (e.g. "今天经营怎么样" without naming a shop), default to the summary report flow.
2. For daily reports, realtime-fetch the shop list first unless the user already provides a numeric shop id.
   - If the user gives a shop name, match it against the live shop list and use that shop id.
   - If the user does not specify a report date, ask for the date instead of guessing.
3. For summary reports, call `/v1/report/biz/summary?reportDate=...`. The script auto-falls back to the first shop's daily report when the summary response is empty; surface the fallback note so the user knows the data source switched.
4. For AI business questions, call `/v1/ai/chat/create` with the user's question and stream the answer back. Do not call the daily report API unless the user explicitly asks to retrieve a report.
5. Return concise results. Include the resolved shop id/name and report date for daily reports, and the report date for summary reports, so the data source is clear.

## Script Usage

List shops:

```bash
python3 scripts/lingtu_shop_data.py list-shops
```

Fetch the default first shop's daily report:

```bash
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09
```

Fetch a named shop's daily report:

```bash
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09 --shop-name "店铺名"
```

Fetch the all-shops summary report (auto-falls back to the first shop's daily report when the summary is empty):

```bash
python3 scripts/lingtu_shop_data.py summary-report --date 2026-06-09
```

Ask an AI shop operations question:

```bash
python3 scripts/lingtu_shop_data.py ask "这个店铺最近经营有什么问题？"
```
