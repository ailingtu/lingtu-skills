# 公开 Skill 目录接口

## 目录

`GET https://ailingtu.com/api/skills`，不需要认证，不发送 API Key。

响应为 `{ "skills": [...] }`，没有分页、关键词搜索或单项详情参数。每项包括：

- `slug`：短 ID；`packageName`：完整包名。匹配安装索引时使用 `packageName`，不要把短 ID 当成索引 slug。
- `version`、`updatedAt`、`auth`：当前版本、更新时间、认证模式。
- `category`、`platforms`：分类和适用平台。
- `locales["zh-CN"]`、`locales["en-US"]`：`title`、`description`、`highlights`、`prompt`、`input`、`output`、`requirement`、`categoryLabel`。
- `packagePath`、`versionedPackagePath`：包路径。安装时使用官方安装索引的完整 URL 和校验值，不自行拼接路径。

成功响应是 HTTP 200；数据库异常时返回 HTTP 503。目录从已发布记录实时读取，响应设置 `Cache-Control: no-store`。网络失败、非 JSON、缺少 skills 数组都属于查询失败，不能解释成没有匹配技能。空 skills 数组表示目录当前无条目。

## 安装索引与流程

- `GET https://cdn.ailingtu.cn/skills/packages/index.json`：`packages` 数组，条目包括完整 `slug`、`displayName`、`summary`、`version`、`url`、`versionedUrl`、`sha256`、`bytes`；认证模式以实时返回为准。
- `GET https://ailingtu.com/install/skills.md`：安装、更新、当前 Agent 目录识别与校验步骤。

目录用于理解能力，索引用于下载和验证。目录与索引版本不一致时刷新一次；安装以索引的同一条完整发布记录为准，并向用户说明差异。索引没有对应包时报告暂不可安装，不猜测地址。

接口依据：官网 `server/api/skills/index.get.ts`、`shared/skill-catalog.mjs`、`server/routes/install/skills.md.get.ts`；2026-09-23 已验证公开目录可匿名读取。新增或修改接口字段前核对实时响应与官网实现。
