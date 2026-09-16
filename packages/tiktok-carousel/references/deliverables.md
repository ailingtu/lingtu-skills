# 交付约定

## 策划阶段

默认在对话中展示易审阅的内容；用户需要文件或将继续生成时，将方案保存到单独的任务目录，不写入 Skill 安装目录。

1. 创意摘要：商品、市场、语言、人群、主要购买理由、结构、图数、比例、风格。
2. 已知事实与来源、创作假设、待补资料。
3. 逐页表：页码、页面目的、画面描述、目标语言图中文字、所用事实/参考图。
4. 每页完整生成提示词，避免塞进过宽表格。
5. 发布标题、正文和相关标签。可选封面 B 文案明确标注为未生成。
6. 需要确认的内容与下一步：“确认后可说‘按这个方案生成’。”仅做策划时到此结束。

## 任务目录

需要持久化时使用如下有实际内容的文件，不提前创建空图片：

- `plan.md`：用户可读方案及修订说明。
- `manifest.json`：方案、任务与文件映射。
- `prompts/01.txt` 等：逐页完整提示词。
- `caption.txt`：发布标题、正文、标签。
- `pages/01/` 等：进入生成后保存该页素材及结果记录。

manifest 建议结构：schema_version=1，mode=plan，status=planned，market、language、page_count、aspect_ratio、product_facts（含来源）、assumptions、unresolved、visual_rules、caption、pages。
每个 page 包含 page_number、purpose、reference_images、image_text、prompt_file、status、client_task_id、schedule_id、task_ids、asset_path、asset_url、review_notes。未生成的 ID 与素材路径为 null，不能填写猜测的 URL。这里是本地清单，不是发布 API 请求体。

商品信息不足可记录 status=needs_input；生成时逐页使用 submitting / processing / generated / needs_revision / failed / unknown 等真实状态。发生超时记录 unknown 和已知 ID，不把它等同于服务端失败。整组状态由实际页面决定，部分完成用 partial。

## 成品阶段

按顺序展示图片，给出文件位置与发布文案。多图预览可使用对话内按序展示；宿主提供可靠拼图工具时可额外生成总览图，不把总览图混入发布页序。

说明需要复查的商品细节或文字。存在未通过的页面时明确列出，保留成功页。用户要求改某页时保留原文件，在该页新增修订版本，更新清单到当前选用版本。

如后续对接发布 Skill，交付有序图片列表和文案；只有用户要求发布后才按发布能力要求映射字段、核查账号与商品信息。
