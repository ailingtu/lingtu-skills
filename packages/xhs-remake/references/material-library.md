# 素材库配置

## 配置位置

素材库路径保存在当前系统用户的：

```text
~/.config/lingtu/xhs-remake.json
```

这里只保存素材库绝对路径，不保存 API Key。配置会跨对话保留，Skill 升级不覆盖，也不会同步到其他电脑。

个人素材库的实际绝对路径不写入 Skill 包。首次执行内容任务时运行 `init`：如果尚未配置，自动创建跨平台的用户目录 `~/Lingtu/xhs-material-library` 并写入配置；如果已有配置，则原样保留。

## 查看与修改

```bash
python3 scripts/lingtu_xhs_config.py init

python3 scripts/lingtu_xhs_config.py show

python3 scripts/lingtu_xhs_config.py set \
  --path /absolute/path/to/material-library

python3 scripts/lingtu_xhs_config.py reset
```

`set` 要求目标是已存在的目录，并将路径解析为绝对路径。只有用户明确要求设置或更换素材库时才执行 `set`；任务中临时给出的素材文件夹不自动成为长期素材库。

`reset` 清除当前配置，但不删除素材文件。下一次执行 `init` 时会重新建立默认目录。

## 任务中的使用规则

- 每次任务开始先执行 `init`。它只在首次使用或执行过 `reset` 后创建默认目录，不覆盖用户自定义路径。
- 用户没有给素材路径：使用已配置素材库。
- 用户给出零散素材：扫描零散素材，并按任务需要从素材库选择 Logo、品牌规范、产品截图等资产。
- 用户明确说“只使用这些素材”：不扫描素材库。
- 用户说“把这些素材放进素材库”：保存到素材库中语义清晰的子目录，遇到同名或同内容文件不静默覆盖，并在任务档案记录目标路径。
- 用户指定了新的任务素材文件夹：仅作为当前任务输入，不改变长期素材库。
- 素材库路径不存在或不可读取：停止依赖该库，说明配置路径，并请用户修改或恢复目录；不要猜测替代目录。
