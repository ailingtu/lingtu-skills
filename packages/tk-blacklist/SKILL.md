---
name: lingtu-tk-blacklist
slug: lingtu-tk-blacklist
version: 0.1.2
auth: none
displayName: 灵途 AI TikTok 达人合作黑名单
summary: 由灵途 AI 提供，批量查询 TikTok 达人合作黑名单及反馈记录，为合作前核验提供参考。
description: "TikTok 达人合作黑名单查询，由灵途 AI 提供。支持通过达人用户名、@handle 或 TikTok 链接，单个或批量查询合作黑名单记录，查看地区、昵称、反馈次数、最近反馈时间及反馈原因，为合作前核验提供参考。用户提到\"达人合作黑名单\"、\"达人黑名单\"、\"黑名单查询\"、\"查达人是否拉黑\"、\"TK 达人风控\"、\"TikTok 黑名单\"或提供达人 uniqueId 要核验黑名单时使用。 也用于“更新灵途 Skills”“升级灵途技能”或更新指定灵途技能。"
license: Apache-2.0
homepage: https://ailingtu.com/skills/tk-blacklist
---

# 灵途 AI TikTok 达人合作黑名单

## 更新灵途 Skills

用户说“更新灵途 Skills”“更新灵途的 skills”“升级灵途技能”或要求更新某个灵途技能时，优先执行此流程，不启动本技能的业务任务。无需 API Key；无需先安装其他技能。只需由一个已加载的灵途技能统一处理，避免多个技能重复更新。

1. 读取 https://ailingtu.com/install/skills.md 和实时索引 https://cdn.ailingtu.cn/skills/packages/index.json 。更新所有技能时，在当前 Agent 实际启用的用户级与项目级 Skills 目录中查找已安装的灵途技能；指定技能时只处理匹配项。不扫描其他应用，不安装尚未安装的技能。
2. 用本地 SKILL.md 的 name/slug 精确匹配索引，按 SemVer 比较 version（数字比较，不按字符串排序）。同版跳过，本地更高版本保留，不自动降级；版本缺失、格式不明或索引无匹配时单独报告，不猜测下载地址。重复目录解析真实路径去重；确有多个启用副本时逐个报告路径并更新。忽略备份目录。
3. 对有新版的技能逐包下载，核对索引 SHA-256、大小及包内 name/version，验证 ZIP 路径不越界且不含符号链接，再在暂存目录解压。备份旧目录到 Agent 不会扫描的目录，保留用户配置和任务输出，然后完整替换包文件，避免覆盖解压留下旧脚本。失败恢复原目录，其余包可继续；不读取或修改密钥。
4. 汇报各包旧版→新版、已是最新、跳过或失败原因、实际安装与备份位置。宿主不支持热加载时提示重启。官方文档或索引不可访问时明确说明，保留本地版本。

用户已明确要求更新时直接执行；仅在路径歧义无法自行确定或宿主权限要求时再询问。不要将本次更新请求理解为自动定时更新或发布授权。

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
