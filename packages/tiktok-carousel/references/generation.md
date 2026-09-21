# 确认后的生成工作流

先检查用户是否已经确认本次方案或明确要求直接生成。已有授权继续有效，不因内部进入新步骤而重复确认。只策划时不要执行本文件中的业务命令。

## 准备

- 读取 `api.md`，使用本包自带脚本；模型优先级为本次指定、本机偏好、内置默认。没有指定时省略 `--model`。仅在查询或修改偏好时读取 `model-preferences.md`。
- 确保目标市场、语言、商品参考与待渲染文字明确。不存在的商品参数从文案中移除，不渲染占位符。
- 默认整合图中文字直接生成；每页提示词精确指定文字并检查最终结果。若宿主有可靠文字排版工具，可以生成无字底图后叠字，保留底图与文字信息；不可声称本包自带独立排版或拼图引擎。
- 按 planning.md 逐页选择相关参考，出现本商品才传对应原商品图；无产品首图不传商品图。保留用户指定顺序，标明每张参考的角色与对应部位。提示词包含该页完整人物描述、精确文字和物理约束。

## 提交前的整套检查

先确认方案已经通过 concept-development.md 的动机与商品关联筛选，再按 planning.md 完成内部镜头表和独立提示词。逐页指定观众能读到的信息、动作瞬间、视线、画面中服务故事的细节与文字层级；人物参考限定为身份参考，明确不复制其姿势和构图。并排读各页提示词：若只是换背景和字幕、无意义地重复侧头微笑，先改正再提交。相同机位或字幕样式本身不是错误，书页展示、细节与对比可保留一致形式；不要以视觉变化替代信息推进。核对末页 CTA 的精确文字及入口条件；不能把 CTA 仅写在发布正文中。

## 提交与恢复

每页一个独立任务，使用 `--nums 1`。5 张方案意味着 5 个不同页面任务，不是一次相同提示词请求 5 个变体。未要求封面变体时不额外生成。

命令从 Skill 根目录执行，参考图、提示词文件与输出目录使用任务目录的绝对路径。为避免文案中的引号、反引号或美元符号被 shell 执行，建议由 Python 读取提示词并用参数数组运行脚本：

```python
import json
import secrets
import string
import subprocess
import sys
from pathlib import Path

# 以下路径由当前任务实际位置替换；此示例只处理一页。
skill_root = Path('/absolute/path/to/lingtu-tiktok-carousel')
job = Path('/absolute/path/to/carousel-job')
page = job / 'pages' / '01'
page.mkdir(parents=True, exist_ok=True)
client_id = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
# 新任务创建前记录；如果该页已有任务记录，先恢复查询，不再次执行此创建示例。
(page / 'request.json').write_text(json.dumps({'client_task_id': client_id}), encoding='utf-8')
args = [sys.executable, str(skill_root / 'scripts/lingtu_content_task.py'),
        '--kind', 'image', '--nums', '1', '--aspect-ratio', '9:16',
        '--client-task-id', client_id,
        '--prompt', (job / 'prompts/01.txt').read_text(encoding='utf-8'),
        '--reference-image', '/absolute/path/to/product.jpg',
        '--output-dir', str(page)]
subprocess.run(args, check=True)
```

将实际 schedule_id、task_ids 和素材路径及时写入 manifest。脚本输出需被宿主保留；脚本可能持续轮询，使用可恢复的执行会话并定期报告进展，不因工具等待结束重复提交。

本地图片由脚本上传，通过返回的远程 URL 引用；不使用 base64 图片参数。已有成功页不重跑。

网络断开、脚本非零退出、超时均不能证明服务端失败。优先恢复原任务：

```bash
python3 scripts/lingtu_content_task.py --kind image --poll-schedule-id ACTUAL_SCHEDULE_ID --output-dir /absolute/path/to/carousel-job/pages/01
# 只有 task id 时使用 --poll-task-id ACTUAL_TASK_ID。
```

只有创建前记录的 client_task_id 时，可以用该 ID 查询；查无结果不证明创建未发生，应保留 unknown 状态，报告无法确认。不要自动改用另一创建接口重投，也不要宣称客户端 ID 保证服务端幂等。

服务端明确失败后，可对该页进行一次有依据的修正重试；再次失败则停止该页并交付其余结果。成功结果若未通过下列视觉验收，标记 needs_revision，说明问题；在用户预算内仅对问题页进行一次有明确修正依据的重生成。仍未通过则交付其余结果并说明缺口，不无限生成替代版。用户指定预算或重试次数时优先遵循。

## 核验与结果

查看每张输出图：商品外观、颜色、结构、配件、品牌是否正确，人物身份和体型是否连续，使用位置是否匹配镜头；缩到手机阅读尺寸检查小产品、关键动作和文字是否清晰且互不遮挡，是否出现未经确认的效果、价格或评价。结尾需兑现首图承诺。未查看的图片不能称为核验通过。

再按顺序看整套，而非只检查每张是否清晰：

- 首图：不读策划说明能否认出与品类相关的问题、愿望或内容价值？后页是否回应了它？笑点或商品关联只存在于解释中，不能通过。
- 信息：第二页是否已提供回报，每页是否新增线索、细节、方法或情绪参与？生活道具是否支持情节，拼贴是否有有效内容？
- 人物与真实感（有人物时）：保持同一身份但动作、目光和情绪随事件变化；不因服装或背景不同就忽略重复姿势。是否像人在做事，而非连续摆拍？
- 排版：主次与强调词清楚，布局适合内容，相同样式有合理用途；手机尺寸可读，关键文字不贴边或遮挡产品。
- 结尾：首图承诺已兑现，商品承接前面的动机，方案约定的 CTA 出现在图内。约定 `linked here ↓` 时缺失、错字或不可读均不通过，正文有它不能补救。

qa.json 分别记录每页与整套的 pass / needs_revision 及观察依据。任务状态成功只表示接口完成，不能代替视觉与叙事验收。

保留每页原始结果和顺序。优先展示脚本返回的 Markdown 媒体与本地绝对路径，再提供任务目录和发布文案。下载未成功时如实提供原始素材链接，不伪造本地文件。返回接口错误或未知问题时保留开发者支持文案：`生成失败或遇到未知问题，请联系开发者：微信 yh8000m`。
