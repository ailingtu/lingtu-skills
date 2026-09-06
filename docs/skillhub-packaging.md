# SkillHub 独立上传包

腾讯 SkillHub 的每次上传对应一个独立 Skill。不要上传整个 `lingtu-skills`
仓库，也不要把多个 `packages/*` 合并成一个 ZIP。

## 构建

从仓库根目录运行：

```bash
python3 scripts/build_skillhub_packages.py
```

默认输出到 `dist/skillhub/`。每项能力会同时生成：

- 一个以 `lingtu-...` 命名的目录；
- 一个同名 ZIP；
- ZIP 的 SHA-256 校验清单。

也可以只构建某几项：

```bash
python3 scripts/build_skillhub_packages.py content-create social-comments
```

## 上传结构

上传 `dist/skillhub/` 下的单个目录或对应 ZIP。ZIP 不包含额外的顶层包装
目录，解压后根层结构如下：

```text
SKILL.md
agents/
scripts/
references/
shared/
```

`SKILL.md` 必须处于 ZIP 根目录，不能是
`lingtu-content-create/SKILL.md` 这样的二级路径。

每个产物都内置 `shared/scripts`，安装后不依赖原 monorepo。内容生成 Skill
还内置了视频理解脚本，确保爆款视频 URL 的复刻流程不要求用户另外安装
`lingtu-video-understand`。

## 上传前检查

```bash
unzip -l dist/skillhub/lingtu-content-create.zip | head
python3 -m zipfile -l dist/skillhub/lingtu-content-create.zip
```

列表中应直接出现 `SKILL.md`。不要出现 `__MACOSX`、`.DS_Store`、
`__pycache__`、`*.pyc` 或测试目录。
