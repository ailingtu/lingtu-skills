# 发布接口

只通过 `scripts/lingtu_skillhub_publish.py` 调用。不要手写 curl，也不要把密钥放进命令行回显。

## 灵途 SkillHub

`POST https://ailingtu.com/api/supermanage/skills`

本地调试可把 `LINGTU_SKILLHUB_BASE_URL` 设为 `http://127.0.0.1:2345`。这只改地址，不改密钥。

请求头是 `Authorization: Bearer $LINGTU_SKILLHUB_TOKEN`。错误的 Authorization 不会改用登录 Cookie。`x-api-key` 和 `LINGTU_API_KEY` 无效。

发布或升级使用 multipart：

| 字段 | 含义 |
| --- | --- |
| `file` | ZIP。根目录必须有带 frontmatter 的 `SKILL.md`，最大 32 MB |
| `packageName` | 可选。若填写，必须与包内 `name` 一致 |
| `catalog` | 可选。完整目录对象的 JSON 文本，不要再包一层 `packageName` |

`SKILL.md` 必须满足：`name` 与 `slug` 同为 `lingtu-` 开头的 kebab-case，`version` 为 `x.y.z`，`auth` 为 `lingtu-api-key` 或 `none`。

已发布技能省略 catalog 时沿用数据库文案，并用 `displayName`、`summary` 覆盖中文标题和简介。新技能必须在 ZIP 根目录放 `catalog.json`，或用 `--catalog` 提交同一份目录。

更新已发布技能的网站文案、不更换 ZIP 时，发送 JSON：

```json
{"packageName":"lingtu-video-publish","catalog":{}}
```

`catalog` 含 `slug`、`category`、`iconKey`、`tone`、`platforms`、`sortOrder`，以及 `locales.zh-CN` 和 `locales.en-US`。每个语言都要有 `title`、`description`、`prompt`、`highlights`、`input`、`output`、`requirement`、`categoryLabel`。`iconKey` 只能是 `arrow-up-tray`、`video-camera`、`chart-bar`、`eye`、`play-circle`、`chat-bubble`。`tone` 只能是 `emerald`、`violet`、`rose`、`cyan`、`sky`、`amber`。

成功响应：

```json
{"mode":"publish","packageName":"lingtu-video-publish","slug":"video-publish","version":"0.2.2"}
```

`mode` 为 `publish` 或 `update`。

| HTTP | 含义 |
| --- | --- |
| 401 | 发布密钥无效、过期或已撤销 |
| 403 | 密钥没有 `blog:publish`。后台文案是“允许发布和下架文章、发布和更新官网技能” |
| 409 | 旧版本覆盖新版本、同一版本内容不同，或已有发布正在进行 |
| 413 | ZIP 超过 32 MB |
| 500 | 目录已写入但安装索引导出失败。用同一 ZIP 和同一版本重试 |

## 腾讯 WorkBuddy（skillhub.cn）

只调用本机 `skillhub` CLI，不自己打包，也不自己校验 metadata。未安装 CLI 时让客户打开 https://skillhub.cn/tutorials 安装，并用 `skillhub --version` 确认。主机固定为 `https://api.skillhub.cn`。

```bash
skillhub login --key "$SKILLHUB_KEY" --host "https://api.skillhub.cn"
skillhub publish --dry-run --json --host "https://api.skillhub.cn" /绝对路径/技能目录
skillhub publish --json --host "https://api.skillhub.cn" /绝对路径/技能目录
```

`publish` 必须带技能目录或 zip 路径。`--dry-run` 只在本地校验 metadata 并打包，不登录、不发请求。真正发布前才执行 `login`。

当前 CLI 不支持 `login --key` 时，才改用：

```bash
skillhub auth login --token "$SKILLHUB_KEY" --host "https://api.skillhub.cn"
```

`SKILL.md` 至少要有 kebab-case 的 `slug`（2–128；没有 `slug` 时用 `name`）、`version`（`x.y.z`）和 `displayName`。建议同时有 `summary`、`description`、`license`、`homepage`，缺这些不阻断发布。

CLI 不会上传技能头像；没有 `iconUrl` 时平台使用默认图。安装说明见 https://skillhub.cn/tutorials ，发布说明见 https://skillhub.cn/ai/release.md 。
