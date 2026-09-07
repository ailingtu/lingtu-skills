# TKShop Query

TKShop Query is a reusable agent package for TK shop operations data. It supports shop list lookup, daily shop reports, and AI business questions through Lingtu AI APIs.

Current package version: `0.2.1`. Remote installers can compare the `version` field in [`SKILL.md`](./SKILL.md) frontmatter to decide whether an installed copy needs updating.

## What It Does

- Lists available shops through Lingtu AI.
- Fetches a single-shop daily report by shop id, shop name, and date.
- Fetches an all-shops summary report by date, with automatic fallback to the first shop's daily report when the summary is empty.
- Answers shop operations questions through the Lingtu AI chat API.
- Provides deterministic script entry points for agents that can run local tools.

## Requirements

All authenticated requests use only the `LINGTU_API_KEY` environment variable and send it as `x-api-key`. If it is missing, run `python3 shared/scripts/user_keys.py single bind` from this Skill root and open the generated authorization URL. Never paste the key into chat or commit it or private business data.

## Script Usage

List shops:

```bash
python3 scripts/lingtu_shop_data.py list-shops
```

Fetch a daily report:

```bash
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09
```

Fetch the all-shops summary report:

```bash
python3 scripts/lingtu_shop_data.py summary-report --date 2026-06-09
```

Ask a shop operations question:

```bash
python3 scripts/lingtu_shop_data.py ask "这个店铺最近经营有什么问题？"
```

## API Reference

Read [`references/api.md`](./references/api.md) before changing endpoint paths, request fields, response fields, or streaming parsing.
