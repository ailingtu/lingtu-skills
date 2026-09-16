# 灵途 Skills 独立分发包

每个 Skill 都通过灵途 TOS/CDN 单独下载和安装。不要上传整个
`skills.ailingtu` 仓库，也不要把多个 `packages/*` 合并成一个 ZIP。

## 与安装文档的关系

用户和 Agent 统一读取 <https://ailingtu.com/install/skills.md>。该文档会读取
<https://cdn.ailingtu.cn/skills/packages/index.json>，再按 slug 下载单个包。

因此本仓库中的 `packages/*` 是开发源码，实际发布入口是本脚本生成的单个
自包含目录或 ZIP。不要直接上传仓库根目录，也不要直接上传仍依赖根级
`shared/` 的源码目录。

## 构建一个 Skill

新包应先通过 `scripts/create_package.py` 创建。`SKILL.md` 必须显式声明：

- `auth: lingtu-api-key`：调用灵途业务 API，构建时自动内置统一认证运行时。
- `auth: none`：不调用需要认证的灵途业务 API，构建产物不包含认证运行时。

构建器会校验该声明。`lingtu-api-key` 包的 `SKILL.md` 还必须包含
`LINGTU_API_KEY`、`x-api-key` 和 `https://ailingtu.com/api-keys` 配置引导。

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

所有会调用灵途业务 API 的产物都内置 `shared/scripts`，以便统一读取
`LINGTU_API_KEY`，缺少时提示用户配置该环境变量；安装后不依赖原 monorepo。只读取公开文档的
`openapi-guide` 不包含认证运行时。内容生成 Skill
还内置了视频理解脚本，确保参考视频 URL 的结构改编生成流程不要求用户另外安装
`lingtu-video-understand`。

## 发布

上传最新版 ZIP 和带版本 ZIP 到灵途 TOS/CDN，然后更新官方索引中对应
slug 的条目。索引必须包含：

- `slug`、`displayName`、`summary`、`version`、`auth`；
- 最新版 `url` 和固定版本 `versionedUrl`；
- 由本次 ZIP 产生的 `sha256` 和 `bytes`。

构建生成的 `.metadata.json` 已提供除 URL 外的字段。上传后填入真实 URL，
不要猜测 CDN 地址。

## 用户安装

发布后，让用户或 Agent 按官方安装文档操作：

<https://ailingtu.com/install/skills.md>

不再引导用户从 Codeup、GitHub 或其他技能商店安装。

## 上传前检查

```bash
unzip -l dist/packages/lingtu-content-create.zip | head
python3 -m zipfile -l dist/packages/lingtu-content-create.zip
```

列表中应直接出现 `SKILL.md`。不要出现 `__MACOSX`、`.DS_Store`、
`__pycache__`、`*.pyc` 或测试目录。

## 打包记录

成功运行 `scripts/build_package.py <package-id>` 后，脚本自动更新根目录
`README.md` 能力表格中该包的版本号、北京时间和负责人；新包自动追加一行。
版本号读取 `SKILL.md`，不会自动升级。首次负责人默认读取 Git `user.name`，
后续保留已有负责人；可用 `--owner "负责人"` 显式指定或变更。
没有可用负责人时在构建前报错；构建失败不会更新表格。
打包完成后，将 README 的记录与包的源码改动一起提交。
