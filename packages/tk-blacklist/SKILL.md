---
name: lingtu-tk-blacklist
slug: lingtu-tk-blacklist
version: 0.1.1
auth: none
displayName: TikTok 达人合作黑名单 By 灵途 AI
summary: 由灵途 AI 提供，批量查询 TikTok 达人合作黑名单及反馈记录，为合作前核验提供参考。
description: TikTok 达人合作黑名单查询，由灵途 AI 提供。支持通过达人用户名、@handle 或 TikTok 链接，单个或批量查询合作黑名单记录，查看地区、昵称、反馈次数、最近反馈时间及反馈原因，为合作前核验提供参考。用户提到"达人合作黑名单"、"达人黑名单"、"黑名单查询"、"查达人是否拉黑"、"TK 达人风控"、"TikTok 黑名单"或提供达人 uniqueId 要核验黑名单时使用。
license: Apache-2.0
homepage: https://ailingtu.com/skills/tk-blacklist
---

# TikTok 达人合作黑名单 By 灵途 AI

## Installation and upgrades

Follow https://ailingtu.com/install/skills.md. Do not install or upgrade this Skill from GitHub or another skill store.

## Overview

Use this Skill to check one or more TikTok creators against Lingtu AI's creator collaboration blacklist and review feedback records before a potential collaboration.

Supported API flow:

- Blacklist search: `POST /web/influencerBlack/search` with JSON body `{"uniqueIds":["..."]}`.

Read `references/api.md` before changing endpoint paths, request fields, response fields, or status handling. Use `scripts/lingtu_tk_blacklist.py` for deterministic calls.

## Authentication

This endpoint currently accepts anonymous requests. Do not read, request, bind, or send an API key for blacklist lookups.

Use `https://api.ailingtu.com` as the default base URL unless a future API reference specifies another host.

## Workflow

1. Extract TikTok `uniqueId` values from the user request.
   - Accept raw IDs such as `vexbolts`.
   - Accept `@handle` mentions and TikTok profile or video URLs; normalize them to the handle.
2. Call `scripts/lingtu_tk_blacklist.py search ...` with all unique IDs in one request.
3. Summarize the result clearly.
   - If an ID is present in `data.list`, report it as found and include `count`, `region`, `nickname`, `feedbackAt`, and `feedbackReason` when available.
   - If an input ID is absent from `data.list`, report it as not found in the blacklist response.
4. Do not infer safety or compliance beyond the API result. The response only confirms whether blacklist records were returned.

## Script usage

Query one creator:

```bash
python3 scripts/lingtu_tk_blacklist.py search vexbolts
```

Query multiple creators:

```bash
python3 scripts/lingtu_tk_blacklist.py search test2 test vexbolts xochitlklepper
```

Output concise text:

```bash
python3 scripts/lingtu_tk_blacklist.py search vexbolts --format text
```
