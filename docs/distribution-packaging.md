# 灵途 Skills 独立分发包

每个 Skill 都通过灵途 TOS/CDN 单独下载和安装。不要上传整个
`lingtu-skills` 仓库，也不要把多个 `packages/*` 合并成一个 ZIP。

## 与安装文档的关系

用户和 Agent 统一读取 <https://ailingtu.com/install/skills.md>。该文档会读取
<https://cdn.ailingtu.cn/skills/packages/index.json>，再按 slug 下载单个包。

因此本仓库中的 `packages/*` 是开发源码，实际发布入口是本脚本生成的单个
自包含目录或 ZIP。不要直接上传仓库根目录，也不要直接上传仍依赖根级
`shared/` 的源码目录。

## 构建一个 Skill

从仓库根目录运行：

```bash
python3 scripts/build_package.py content-create
```

默认输出到 `dist/packages/`。每次必须明确指定一个 Skill，并生成：

- 一个以 `lingtu-...` 命名的目录；
- 一个同名 ZIP；
- 一个同名的 `.zip.sha256` 校验文件；
- 一个可用于更新官方索引的 `.metadata.json`。

可构建的 ID 自动取自 `packages/*/SKILL.md`。当前运行下面的命令查看：

```bash
python3 scripts/build_package.py --help
```

## 上传结构

上传 `dist/packages/` 下的单个 ZIP。ZIP 不包含额外的顶层包装
目录，解压后根层结构如下：

```text
SKILL.md
agents/
scripts/
references/
```

`SKILL.md` 必须处于 ZIP 根目录，不能是
`lingtu-content-create/SKILL.md` 这样的二级路径。

需要公共运行时的产物会内置 `shared/scripts`，安装后不依赖原 monorepo；
`video-remake` 的完整运行时直接位于自身 `scripts/`，不会打包无关公共代码。内容生成 Skill
还内置了视频理解脚本，确保爆款视频 URL 的复刻流程不要求用户另外安装
`lingtu-video-understand`。

## 发布

上传最新版 ZIP 和带版本 ZIP 到灵途 TOS/CDN，然后更新官方索引中对应
slug 的条目。索引必须包含：

- `slug`、`displayName`、`summary`、`version`；
- 最新版 `url` 和固定版本 `versionedUrl`；
- 由本次 ZIP 产生的 `sha256` 和 `bytes`。

构建生成的 `.metadata.json` 已提供除 URL 外的字段。上传后填入真实 URL，
不要猜测 CDN 地址。

## 用户安装

发布后，让用户或 Agent 按官方安装文档操作：

<https://ailingtu.com/install/skills.md>

不再引导用户从 GitHub 或其他技能商店安装。

## 上传前检查

```bash
unzip -l dist/packages/lingtu-content-create.zip | head
python3 -m zipfile -l dist/packages/lingtu-content-create.zip
```

列表中应直接出现 `SKILL.md`。不要出现 `__MACOSX`、`.DS_Store`、
`__pycache__`、`*.pyc` 或测试目录。
