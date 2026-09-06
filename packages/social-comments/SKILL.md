---
name: lingtu-social-comments
slug: lingtu-social-comments
version: 0.1.0
displayName: 灵途社交媒体评论下载
summary: 下载多平台单条视频评论，自动分页、去重并导出 JSON。
description: 下载、导出或获取 TikTok、Instagram、抖音、视频号和小红书单条视频的评论数据，支持自动分页、重试限速、跨页去重、限制页数或评论数、原样续传游标、Instagram 热门/最新排序，以及规范化或原始 JSON 输出。用户提到“下载评论”“导出视频评论”“获取这条视频的评论”“抓评论区”“评论区反馈”或提供上述平台的单条视频链接要求评论数据时使用；不用于账号监控、视频指标查询或视频内容理解。
license: Apache-2.0
homepage: https://ailingtu.com/skills/social-comments
---

# 社交媒体评论下载

## 安装与升级

按照 https://ailingtu.com/install/skills.md 操作，不要从 GitHub 安装或升级本 Skill。

使用 `scripts/lingtu_social_comments.py` 获取单条 TikTok、Instagram、抖音、视频号或小红书视频的评论。不要抓取视频网页或调用第三方评论服务。

## 配置

安装不要求认证。执行任务时如果缺少 `LINGTU_API_KEY`，从本 Skill 根目录运行
`python3 shared/scripts/user_keys.py single bind`，并把生成的授权链接交给用户打开。
不要索取、展示或保存用户的 API Key。

默认 API 地址是 `https://api.ailingtu.com`；测试时可通过 `LINGTU_AI_BASE_URL` 覆盖。不要把密钥或下载的评论数据提交到仓库。

修改接口路径、字段、分页或输出结构前，先阅读 `references/api.md`。

下列命令默认从本 Skill 根目录（即包含 `SKILL.md` 的目录）执行。从仓库根目录运行时，把脚本路径改为 `packages/social-comments/scripts/lingtu_social_comments.py`。

## 工作流

1. 从用户输入中取得一条公开 TikTok、Instagram、抖音、视频号或小红书 URL。
2. 根据链接自动识别平台；必要时显式传 `--platform tiktok|instagram|douyin|wechat-channel|xiaohongshu`。
3. 调用 `download`，默认自动翻页直到接口没有下一页；每页间隔 500ms，并对 429、5xx 和网络错误自动重试两次。
4. 用户要求保存文件时传 `--output`；文件已存在时，只有用户明确允许覆盖才传 `--force`。
5. 返回评论数量、页数和保存路径。若用户进一步询问评论区反馈，再基于规范化 JSON 总结，不把总结写回下载文件。

## 命令

下载 TikTok 评论到文件：

```bash
python3 scripts/lingtu_social_comments.py download \
  --platform tiktok \
  --video-url "https://www.tiktok.com/@user/video/1234567890" \
  --output ./comments.json
```

下载 Instagram 最新评论：

```bash
python3 scripts/lingtu_social_comments.py download \
  --platform instagram \
  --video-url "https://www.instagram.com/reel/Example/" \
  --sort-order newest \
  --output ./comments.json
```

默认把规范化 JSON 输出到 stdout。常用参数：

- `--max-pages N`：最多抓取 N 页。
- `--max-comments N`：最多保留 N 条去重后的评论；最后一页可能先完整拉取再截断，不适合把返回游标当作截断位置继续下载。
- `--first-page`：只抓第一页。
- `--cursor VALUE`：从指定游标继续；所有平台都必须把接口返回值原样传回，不解码、不转义。
- `--retries N`、`--retry-sleep-ms N`：配置临时错误的重试次数和初始退避时间。
- `--sleep-ms N`：配置成功页之间的请求间隔，默认 500ms。
- `--no-dedupe`：保留跨页出现的重复评论 ID；默认自动去重。
- `--no-progress`：关闭写到 stderr 的逐页进度，不影响 stdout JSON。
- `--raw`：保留聚合后的接口原始字段。
- `--output PATH`：写入 JSON 文件。
- `--force`：允许覆盖已存在的输出文件。

抖音示例：

```bash
python3 scripts/lingtu_social_comments.py download \
  --platform douyin \
  --video-url "https://www.douyin.com/video/1234567890" \
  --output ./douyin-comments.json
```

视频号示例：

```bash
python3 scripts/lingtu_social_comments.py download \
  --video-url "https://weixin.qq.com/sph/Example" \
  --output ./wechat-channel-comments.json
```

视频号同时识别 `weixin.qq.com/sph/...` 与 `channels.weixin.qq.com/...` 链接。

小红书示例：

```bash
python3 scripts/lingtu_social_comments.py download \
  --platform xiaohongshu \
  --video-url "https://www.xiaohongshu.com/explore/1234567890" \
  --output ./xiaohongshu-comments.json
```

当前支持 TikTok、Instagram、抖音、视频号和小红书。YouTube 不在此 Skill 的评论下载范围内。
