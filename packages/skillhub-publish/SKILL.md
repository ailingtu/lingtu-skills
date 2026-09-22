---
name: lingtu-skillhub-publish
slug: lingtu-skillhub-publish
version: 0.1.0
auth: none
displayName: "AI 技能发布到skillhub By 灵途 AI"
summary: "把 AI Skill 发布到灵途 SkillHub 或腾讯 WorkBuddy（skillhub.cn）。"
description: "把本地 AI Skill 发布到灵途 SkillHub，或发布到腾讯 WorkBuddy 应用市场（skillhub.cn）。用户要上架技能、发布 Skill、提交到 SkillHub 或 WorkBuddy 时使用。其它技能市场接入中。灵途发布使用独立的发布密钥，不使用业务 API Key；腾讯使用 skillhub.cn 自己的 API Key。 也用于“更新灵途 Skills”“升级灵途技能”或更新指定灵途技能。"
license: Apache-2.0
homepage: https://ailingtu.com/skills/skillhub-publish
---

# AI 技能发布到skillhub By 灵途 AI

## 更新灵途 Skills

用户说“更新灵途 Skills”“更新灵途的 skills”“升级灵途技能”或要求更新某个灵途技能时，优先执行此流程，不启动本技能的业务任务。无需 API Key；无需先安装其他技能。只需由一个已加载的灵途技能统一处理，避免多个技能重复更新。

1. 读取 https://ailingtu.com/install/skills.md 和实时索引 https://cdn.ailingtu.cn/skills/packages/index.json 。更新所有技能时，在当前 Agent 实际启用的用户级与项目级 Skills 目录中查找已安装的灵途技能；指定技能时只处理匹配项。不扫描其他应用，不安装尚未安装的技能。
2. 用本地 SKILL.md 的 name/slug 精确匹配索引，按 SemVer 比较 version（数字比较，不按字符串排序）。同版跳过，本地更高版本保留，不自动降级；版本缺失、格式不明或索引无匹配时单独报告，不猜测下载地址。重复目录解析真实路径去重；确有多个启用副本时逐个报告路径并更新。忽略备份目录。
3. 对有新版的技能逐包下载，核对索引 SHA-256、大小及包内 name/version，验证 ZIP 路径不越界且不含符号链接，再在暂存目录解压。备份旧目录到 Agent 不会扫描的目录，保留用户配置和任务输出，然后完整替换包文件，避免覆盖解压留下旧脚本。失败恢复原目录，其余包可继续；不读取或修改密钥。
4. 汇报各包旧版→新版、已是最新、跳过或失败原因、实际安装与备份位置。宿主不支持热加载时提示重启。官方文档或索引不可访问时明确说明，保留本地版本。

用户已明确要求更新时直接执行；仅在路径歧义无法自行确定或宿主权限要求时再询问。不要将本次更新请求理解为自动定时更新或发布授权。


## 安装与升级

按照 https://ailingtu.com/install/skills.md 安装和升级，不要从源码仓库或其他技能商店安装。

## 用途

把一个本地 Skill 目录发布到选定的技能市场。先检查目录和对应平台的密钥，再做预览，用户明确确认后才真正发布。

已接入：

- 灵途 SkillHub
- 腾讯 WorkBuddy 应用市场（skillhub.cn）

其它平台接入中。用户指定尚未接入的市场时，直接说明接入中，不要猜测接口或改用另一把密钥。

## 密钥

每个平台只用自己的密钥。本技能的 `auth: none` 表示它不调用灵途业务接口，也不读取 `LINGTU_API_KEY`。

| 平台 | 环境变量 | 形态 | 用法 |
| --- | --- | --- | --- |
| 灵途 SkillHub | `LINGTU_SKILLHUB_TOKEN` | `blg_` 发布密钥 | `Authorization: Bearer`，发给 `https://ailingtu.com` |
| 腾讯 WorkBuddy | `SKILLHUB_KEY` | `skh_` API Key | 只交给本机 `skillhub` CLI，主机为 `https://api.skillhub.cn` |

不要读取 `BLOG_AGENT_TOKEN`。博客 Agent 若已经保存过同一枚发布密钥，由用户把它配置到 `LINGTU_SKILLHUB_TOKEN`，不要自动借用。两把密钥不能互换，也不能拿业务 API Key 代替。

缺少密钥、前缀不对，或用户询问如何创建密钥时，读取 [references/credentials.md](references/credentials.md)。只报告“已配置 / 未配置 / 格式不符”。不要索取、展示、记录或写入密钥。

发布前若接口字段有疑问，读取 [references/api.md](references/api.md)。

## 发布流程

1. 确认目标平台。用户没有指明时询问，不要一次发到所有平台。
2. 定位包含 `SKILL.md` 的技能目录。目录不唯一时询问绝对路径。
3. 腾讯 WorkBuddy 先执行 `skillhub --version`。没有这个命令时，停止发布，把下面的安装说明发给客户，不要下载或执行安装脚本：

   发布到腾讯 WorkBuddy 需要先安装 skillhub CLI。请打开 https://skillhub.cn/tutorials ，按官方步骤安装。安装完成后在终端执行 `skillhub --version`，看到版本号后告诉我，我再继续。

   客户确认安装完成且 `skillhub --version` 能输出版本号后，再继续。腾讯侧只调用这个 CLI：预览用 `skillhub publish --dry-run`，确认后用 `skillhub login` 和 `skillhub publish`。校验和打包以 CLI 的输出为准。
4. 运行 `python3 scripts/lingtu_skillhub_publish.py status`，只看目标平台的密钥。
5. 灵途发布前运行 `python3 scripts/lingtu_skillhub_publish.py lint <目录> --platform lingtu`。有问题先改本地技能。
6. 不带 `--confirm` 预览。把技能名、版本、目标平台和预览结果告诉用户。
7. 用户明确说“发布”或“确认”后，才追加 `--confirm`。取消就停止。
8. 转述脚本 JSON 里的结果。`missing_cli` 时重复第 3 步的安装说明。失败时保留 CLI 或接口的错误说明，不要重试到另一平台。

```bash
python3 scripts/lingtu_skillhub_publish.py status
python3 scripts/lingtu_skillhub_publish.py lint /绝对路径/技能目录 --platform lingtu
python3 scripts/lingtu_skillhub_publish.py lingtu /绝对路径/技能目录
python3 scripts/lingtu_skillhub_publish.py lingtu /绝对路径/技能目录 --catalog /绝对路径/catalog.json --confirm
python3 scripts/lingtu_skillhub_publish.py workbuddy /绝对路径/技能目录 --confirm
```

灵途预览只在本地检查，不会上传。腾讯预览调用本机 `skillhub publish --dry-run`，只校验并打包，不登录、不上传。`--confirm` 才会登录并改变线上目录。

同一版本的 ZIP 内容不能改变。灵途返回版本冲突时升高版本，不要覆盖。若返回“目录已写入，安装索引导出失败”，用同一目录和同一版本重试。

