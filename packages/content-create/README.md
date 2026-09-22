# 商品图片与带货视频生成 By 灵途 AI

面向电商商家与内容创作者的 AI 带货视频和 AI 商品图片生成 Skill，由灵途 AI 提供。从商品图片、卖点和提示词出发，生成电商带货视频、UGC 短视频、商品主图、卖点细节图和生活场景图。

当前版本以 [`SKILL.md`](./SKILL.md) 文件头部的 `version` 字段为准，安装器可据此判断是否需要升级。

## 主要能力

- 根据参考图片生成商品图和电商视频。
- 针对目标市场和语言编写带货短视频提示词。
- 创建灵途 AI 生成任务，轮询至完成并返回媒体链接或本地文件。

## 智能体工作流

主要使用说明见 [`SKILL.md`](./SKILL.md)。Codex 可直接作为技能读取，其他智能体可作为任务说明使用。详细工作流见 [`references/`](./references)：

- [`wan-prompt-guide.md`](./references/wan-prompt-guide.md): Wan 3.0 的素材指代、音色与台词、镜头和声音控制规则。
- [`ecommerce-video-workflow.md`](./references/ecommerce-video-workflow.md): 为目标市场生成多个电商视频版本。
- [`api.md`](./references/api.md): 灵途 AI 任务接口约定与数据结构说明。

## 使用要求

所有认证请求仅从环境变量 `LINGTU_API_KEY` 读取密钥，并通过 `x-api-key` 请求头发送。缺少密钥时，引导用户前往 https://ailingtu.com/api-keys 创建或管理密钥，在运行技能的环境中配置后重试。不要将密钥粘贴到聊天中，也不要将密钥、私人媒体或经营数据提交到仓库。

## 模型偏好

视频默认使用 `wan3.0-video`，图片默认使用 `gpt-image-2.5-ext-flare`。不指定模型时自动读取本机偏好；“这次用”只覆盖当前任务，“以后默认用”则保存到 `~/.config/lingtu/content-create.json`，新对话继续沿用，升级不会覆盖。操作命令见 [模型偏好说明](./references/model-preferences.md)。

## 脚本用法

使用已保存的模型偏好或内置默认模型及默认时长，生成竖屏电商视频：

```bash
python3 scripts/lingtu_content_task.py \
  --kind video \
  --size 480x854 \
  --prompt "15秒竖屏写实手机拍摄视频……" \
  --reference-image ./ref-1.png \
  --reference-image ./ref-2.png \
  --reference-image ./ref-3.png \
  --reference-video ./motion-reference.mp4 \
  --reference-audio ./voice-reference.mp3
```

使用 `wan3.0-video` 时，`--reference-video` 和 `--reference-audio`（也可写为 `--reference-dubbing`）支持本地媒体路径或已有的灵途文件正整数 ID。重复传入参数可按顺序使用多个参考素材。

生成商品图片：

```bash
python3 scripts/lingtu_content_task.py \
  --kind image \
  --aspect-ratio 9:16 \
  --prompt "生成干净清晰的商品主图……" \
  --reference-image ./product.jpg
```

## 许可证

采用 Apache 2.0 许可证，详见 [`LICENSE`](./LICENSE)。

生成的媒体示例仅用于演示，可能有单独的使用限制。

完整配置步骤（含 Mac / Windows 打开终端、命令和重启说明）：[API Key 配置指南](../../shared/references/api-key-setup.md)。
