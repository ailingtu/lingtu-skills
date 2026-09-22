---
name: lingtu-tkshop-query
slug: lingtu-tkshop-query
version: 0.2.3
auth: lingtu-api-key
displayName: "TikTok 店铺数据查询和对话 By 灵途 AI"
summary: 查询 TikTok Shop 店铺日报、经营指标并分析业务问题。
description: "TK 店铺数据查询与日报。通过灵途 AI 接口查询 TK 店铺/商家/商品/订单/客户表现等经营数据，支持按日期或店铺名拉取单店日报、按日期拉取全部店铺汇总日报、列出店铺清单，以及向 AI 提问店铺经营相关问题。用户提到\"店铺日报\"、\"店铺数据\"、\"经营情况\"、\"整体经营\"、\"全部店铺汇总\"、\"大盘\"、\"GMV/订单/客单价\"等场景时使用。 也用于“更新灵途 Skills”“升级灵途技能”或更新指定灵途技能。"
license: Apache-2.0
homepage: https://ailingtu.com/skills/tkshop-query
---

# TikTok 店铺数据查询和对话 By 灵途 AI

## 更新灵途 Skills

用户说“更新灵途 Skills”“更新灵途的 skills”“升级灵途技能”或要求更新某个灵途技能时，优先执行此流程，不启动本技能的业务任务。无需 API Key；无需先安装其他技能。只需由一个已加载的灵途技能统一处理，避免多个技能重复更新。

1. 读取 https://ailingtu.com/install/skills.md 和实时索引 https://cdn.ailingtu.cn/skills/packages/index.json 。更新所有技能时，在当前 Agent 实际启用的用户级与项目级 Skills 目录中查找已安装的灵途技能；指定技能时只处理匹配项。不扫描其他应用，不安装尚未安装的技能。
2. 用本地 SKILL.md 的 name/slug 精确匹配索引，按 SemVer 比较 version（数字比较，不按字符串排序）。同版跳过，本地更高版本保留，不自动降级；版本缺失、格式不明或索引无匹配时单独报告，不猜测下载地址。重复目录解析真实路径去重；确有多个启用副本时逐个报告路径并更新。忽略备份目录。
3. 对有新版的技能逐包下载，核对索引 SHA-256、大小及包内 name/version，验证 ZIP 路径不越界且不含符号链接，再在暂存目录解压。备份旧目录到 Agent 不会扫描的目录，保留用户配置和任务输出，然后完整替换包文件，避免覆盖解压留下旧脚本。失败恢复原目录，其余包可继续；不读取或修改密钥。
4. 汇报各包旧版→新版、已是最新、跳过或失败原因、实际安装与备份位置。宿主不支持热加载时提示重启。官方文档或索引不可访问时明确说明，保留本地版本。

用户已明确要求更新时直接执行；仅在路径歧义无法自行确定或宿主权限要求时再询问。不要将本次更新请求理解为自动定时更新或发布授权。

## 安装与升级

按照 https://ailingtu.com/install/skills.md 安装和升级，不要从源码仓库安装。

## 能力介绍

用于查询和分析 TK 店铺经营数据。

支持的接口流程：

- 店铺日报： `GET /v1/report/biz/detail?targetType=SHOP&targetId={shop_id}&reportDate={YYYY-MM-DD}`.
- 全部店铺汇总日报： `GET /v1/report/biz/summary?reportDate={YYYY-MM-DD}`.
- 店铺列表： `GET /v1/shop/list`.
- 经营问题问答：`POST /v1/ai/chat/create`，流式返回结果。

修改接口路径、请求字段、响应字段或处理逻辑前，先阅读 `references/api.md`。通过 `scripts/lingtu_shop_data.py` 执行调用。

## 配置

所有认证请求只读取 `LINGTU_API_KEY`，并通过 `x-api-key` 请求头发送。
安装技能不需要认证。执行任务时缺少密钥，引导用户前往 https://ailingtu.com/api-keys
创建或管理密钥，在运行技能的环境中配置 `LINGTU_API_KEY` 后重试。
不要索取、展示或保存用户密钥，不要生成账号绑定链接。

TikTok Shop 店铺绑定入口是 https://app.ailingtu.com/teamshop 。当用户想绑定 TikTok 店铺、查询不到店铺、或店铺列表为空时，明确让用户打开这个链接完成店铺绑定，然后再执行 `list-shops` 或日报查询。

缺少密钥时，读取 `shared/references/api-key-setup.md`，向用户展示其操作系统对应的完整步骤（如何打开终端、可复制命令、粘贴密钥、重启应用及生效范围），不要只说“配置环境变量”。已知系统时只展示对应部分；未知时同时提供 Mac 和 Windows。配置由用户在自己电脑上完成，不代为读取或填入真实密钥。

默认接口地址为 `https://api.ailingtu.com`，后续接口文档明确指定其他地址时以文档为准。

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

## 脚本用法

查询店铺列表：

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
