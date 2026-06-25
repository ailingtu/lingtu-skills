---
name: lingtu-tk-blacklist
version: 0.1.0
description: TK 达人黑名单查询。通过灵途 AI 接口按 TikTok uniqueId 批量查询达人是否在黑名单中，返回地区、昵称、反馈次数、最近反馈时间和反馈原因。用户提到"达人黑名单"、"黑名单查询"、"查达人是否拉黑"、"TK 达人风控"、"TikTok 黑名单"或给出多个 uniqueId 要批量核验时使用。
---

# TK 达人黑名单查询

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Overview

Use this skill to query whether one or more TikTok creators are present in Lingtu's TK blacklist.

Supported API flow:

- Blacklist search: `POST /web/influencerBlack/search` with JSON body `{"uniqueIds":["..."]}`.

Read `references/api.md` before changing endpoint paths, request fields, response fields, or status handling. Use `scripts/lingtu_tk_blacklist.py` for deterministic calls.

## Configuration

Get your API key at https://app.ailingtu.com/api-key-management. Set `LINGTU_API_KEY` before making requests:

```bash
export LINGTU_API_KEY="..."
```

For macOS apps launched outside your shell, set a user launchd environment variable, then restart Codex:

```bash
launchctl setenv LINGTU_API_KEY "..."
```

Send the key as the request header `x-api-key: <key>`. Do not store user API keys in this skill directory or commit them to source control.

For multi-user bot mode, pass `--channel feishu|wechat --user-id <external-user-id>` to `scripts/lingtu_tk_blacklist.py search`. The script resolves the user's key from `~/.lingtu-skills/config.json`, or calls the backend binding check endpoint if the local key is missing. Use `shared/scripts/user_keys.py bind` to generate the `/binduser` URL.

Use `https://api.ailingtu.com` as the default base URL unless a future API reference specifies another host. `LINGTU_AI_BASE_URL` may override it for testing.

## Workflow

1. Extract TikTok `uniqueId` values from the user request.
   - Accept raw IDs such as `vexbolts`.
   - Accept `@handle` mentions and TikTok profile/video URLs when present; normalize to the handle.
2. Call `scripts/lingtu_tk_blacklist.py search ...` with all unique IDs in one request.
3. Summarize the result clearly:
   - If an ID is present in `data.list`, report it as found in the blacklist and include `count`, `region`, `nickname`, `feedbackAt`, and `feedbackReason` when available.
   - If an input ID is not returned in `data.list`, report it as not found in the blacklist response.
4. Do not infer safety or compliance beyond the API result. If downstream action is needed, state that the API only confirms blacklist records.

## Script Usage

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
