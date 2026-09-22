---
name: lingtu-video-download
slug: lingtu-video-download
version: 0.1.1
auth: lingtu-api-key
displayName: "TikTok 抖音 视频号 小红书无水印下载和数据获取 By 灵途 AI"
summary: "下载公开链接里的无水印视频，或保存图文笔记的图片。"
description: "根据 TikTok、抖音、视频号和小红书的公开链接，默认调用一次 POST /v1/material/fetch 并下载作品：视频保存无水印文件，图文按顺序保存图片，同时记下作者、文案、互动数据和本地路径。用户说只要数据时不保存文件；说填表时用这次结果填入用户指定的表，不重新请求。不用于评论下载、达人账号监控、视频理解或视频发布。同一接口也接受 Instagram 和 YouTube 公开链接。 也用于“更新灵途 Skills”“升级灵途技能”或更新指定灵途技能。"
license: Apache-2.0
homepage: https://ailingtu.com/skills/video-download
---

# TikTok 抖音 视频号 小红书无水印下载和数据获取 By 灵途 AI

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

根据 TikTok、抖音、视频号和小红书的公开链接，默认下载作品本身，并保留一份数据。用户没有提出进一步要求时，交付文件路径和数据后即停止。不用于评论下载、达人账号监控、视频理解或视频发布。同一接口也接受 Instagram 和 YouTube 公开链接。

## 认证

所有认证请求只读取 `LINGTU_API_KEY`，并通过 `x-api-key` 请求头发送。
安装技能不需要认证。执行任务时缺少密钥，引导用户前往 https://ailingtu.com/api-keys
创建或管理密钥，在运行技能的环境中配置 `LINGTU_API_KEY` 后重试。
不要索取、展示或保存用户密钥，不要生成账号绑定链接。
缺少密钥时读取 `shared/references/api-key-setup.md`，向用户说明如何打开 Mac 终端或 Windows PowerShell、具体配置命令和重启应用的步骤，不要仅提示配置环境变量。

默认 API 地址是 `https://api.ailingtu.com`；测试时可通过 `LINGTU_AI_BASE_URL` 覆盖。不要把密钥或下载到的视频提交到仓库。

修改接口路径、请求字段、响应字段或状态处理前，先阅读 `references/api.md`。只调用 `POST /v1/material/fetch`，不要改用各平台单独的素材或评论接口。

下列命令默认从本 Skill 根目录（即包含 `SKILL.md` 的目录）执行。从仓库根目录运行时，把脚本路径改为 `packages/video-download/scripts/lingtu_video_download.py`。

## 工作流

1. 从用户输入取得一条公开作品的 http 或 https 链接。主要处理 TikTok、抖音、视频号和小红书；Instagram 与 YouTube 公开链接也可以交给同一接口。
2. 用户没有说「只要数据」时，直接运行 `download`。只调用一次 `POST /v1/material/fetch`。
3. 视频（`materialType` 为 `VIDEO`，或返回 `downloadAddr` / `playAddr`）只保存无水印视频，优先 `downloadAddr`。封面留在数据里，不另存成图片。图文（`materialType` 为 `PHOTO`，或返回 `imageList`）按顺序保存图片。两者都没有时仍然返回数据，并说明这次响应里没有可下载文件。
4. 把作者、文案、播放、点赞、评论、转发、收藏和本地文件路径写入旁边的 JSON。把路径和这些数据交给用户后停止。不要主动填表、总结成长文、发布或监控。
5. 用户随后提出明确要求时，用这一次的结果处理，不要为同一链接再请求：
   - 「只要数据」：运行 `fetch`，不保存视频和图片。
   - 「下载」：就是默认的 `download` 结果。
   - 「填表」：用作者、文案、互动数据和本地路径，填进用户指定的表。列以用户给出的为准。
6. 视频和图片直链是签名短链。已保存的文件可继续使用；直链失效后重新请求，不要猜测或拼接地址。

## 命令

下载无水印视频；若响应里有 `imageList`，图片写入视频旁边的 `{文件名}-images` 目录。图文笔记没有视频时，`--output` 作为图片目录：

```bash
python3 scripts/lingtu_video_download.py download \
  --video-url "https://www.tiktok.com/@creator/video/7123456789012345678" \
  --output ./video.mp4
```

下载图文图片：

```bash
python3 scripts/lingtu_video_download.py download \
  --video-url "https://xhslink.cn/o/example" \
  --output ./xhs-note
```

只获取数据：

```bash
python3 scripts/lingtu_video_download.py fetch \
  --video-url "https://www.douyin.com/video/7123456789012345678" \
  --output ./video.json
```

常用参数：

- `--output PATH`：视频写成这个文件；没有视频的图文笔记把这里当作图片目录。`fetch` 时写成 JSON。文件已存在时需要 `--force`。
- `--metadata PATH`：`download` 时另行指定数据 JSON；默认写到视频文件旁边，扩展名改为 `.json`。
- `--timeout SECONDS`：单次请求超时，默认 60；下载视频默认 180。
- `--retries N`：对 429、5xx 和网络错误重试，默认 2 次，按指数退避。

