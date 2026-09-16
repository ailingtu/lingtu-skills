---
name: lingtu-tk-blacklist
slug: lingtu-tk-blacklist
version: 0.1.1
auth: none
displayName: 灵途 AI TikTok 达人合作黑名单
summary: 由灵途 AI 提供，批量查询 TikTok 达人合作黑名单及反馈记录，为合作前核验提供参考。
description: TikTok 达人合作黑名单查询，由灵途 AI 提供。支持通过达人用户名、@handle 或 TikTok 链接，单个或批量查询合作黑名单记录，查看地区、昵称、反馈次数、最近反馈时间及反馈原因，为合作前核验提供参考。用户提到"达人合作黑名单"、"达人黑名单"、"黑名单查询"、"查达人是否拉黑"、"TK 达人风控"、"TikTok 黑名单"或提供达人 uniqueId 要核验黑名单时使用。
license: Apache-2.0
homepage: https://ailingtu.com/skills/tk-blacklist
---

# 灵途 AI TikTok 达人合作黑名单

## 安装与升级

按照 https://ailingtu.com/install/skills.md 安装和升级，不要从源码仓库或其他技能商店安装。

## 能力介绍

通过灵途 AI 查询单个或多个 TikTok 达人的合作黑名单与反馈记录，为合作前核验提供参考。

支持的接口流程：

- 黑名单查询：`POST /web/influencerBlack/search`，JSON 请求体为 `{"uniqueIds":["..."]}`。

修改接口路径、请求字段、响应字段或处理逻辑前，先阅读 `references/api.md`。通过 `scripts/lingtu_tk_blacklist.py` 执行调用。

## 认证

该接口目前支持匿名请求。查询黑名单时不要读取、索取、绑定或发送 API 密钥。

默认接口地址为 `https://api.ailingtu.com`，后续接口文档明确指定其他地址时以文档为准。

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
