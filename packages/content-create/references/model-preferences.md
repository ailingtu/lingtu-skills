# 模型选择与本机偏好

不要求用户每次选择模型。创建任务的优先级：本次 `--model` > 本机保存的对应类型模型 > 内置默认。视频内置默认是 `wan3.0-video`，图片是 `gpt-image-2.5-ext-flare`。用户说的 Wan3.0、GPT Image 2.5 Ext Flare 分别对应这两个 API 标识。其他受支持模型与参数见 `api.md`，仅在用户指定或参数不兼容时读取。

- 没有指定模型：生成命令省略 `--model`，让脚本读取偏好，不能把示例里的模型当作每次必传的值。
- “这次用 X”或当前任务明确指定 X：本次传 `--model X`，不修改保存值。
- “以后都用 X／默认改成 X”：运行保存命令。只要求设置偏好时不生成内容；同时要求生成时，保存成功后再执行生成命令。
- 用户仅说“换成 X”但没有表达持久化意图：按本次切换处理。
- 明确要求恢复默认：执行对应类型的重置命令。
- 参数不兼容时说明具体限制和替代方案，不自行修改保存值或轮番换模型重试。

从 Skill 根目录执行，下面的配置命令都不需要认证，也不会上传素材或创建生成任务：

```bash
# 查看视频的实际默认模型
python3 scripts/lingtu_content_task.py --kind video --show-default-model

# 保存视频偏好（图片使用 --kind image）
python3 scripts/lingtu_content_task.py --kind video --set-default-model wan3.0-video
python3 scripts/lingtu_content_task.py --kind image --set-default-model gpt-image-2.5-ext-flare

# 清除视频偏好，恢复内置 Wan3.0；图片偏好保持不变
python3 scripts/lingtu_content_task.py --kind video --reset-default-model
```

配置固定保存在 `~/.config/lingtu/content-create.json`，只保存 `video`、`image` 模型名称，不保存 API Key。每次创建任务都会读取，因此同一系统用户的新对话和升级后的 Skill 都能沿用。它不会自动同步到另一台电脑。爆款复刻由独立的分段重绘脚本固定使用 Wan3.0，不读取这份生成模型偏好。

首次使用无需创建配置文件，直接采用内置默认。已有本机图片模型偏好会继续优先于新的内置默认；运行 `--reset-default-model` 后才会恢复 `gpt-image-2.5-ext-flare`。无效或损坏的配置会明确报错，不静默换模型；本次显式 `--model` 可覆盖配置。轮询旧任务不读取当前偏好，也不应用内置默认，防止模型变化影响旧结果匹配。

视频内置默认分辨率为 480p，默认竖屏尺寸 `480x854`（横屏为 `854x480`）。可用 `--size` 临时覆盖。分辨率暂不写入模型偏好文件。若所选模型不支持 480p，脚本会在提交前报错；说明可用尺寸并由用户选择，不自动升级分辨率。

图片内置默认比例为 `9:16`。用户本次要求其他比例时用 `--aspect-ratio` 覆盖；比例暂不写入模型偏好文件。
