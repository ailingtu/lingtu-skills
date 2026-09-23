# 灵途 SkillHub 单包发布流程

本文是灵途官方 Skill 发布到 SkillHub 的操作手册。更新已有 Skill 或新增
Skill 时，先完整阅读本文，再执行构建、上传或官网发布。

## 核心原则

- 每次只构建和发布一个 Skill。
- 正常发布统一使用按 <https://ailingtu.com/install/skills.md> 安装的
  `lingtu-skillhub-publish` Skill，先预览、后确认发布。不要调用官网仓库里的脚本，
  不要手工请求后台发布 API，也不要发布整个 `dist/packages/` 目录。
- 官方索引采用增量合并：只替换指定 slug 的记录，其余记录的版本、URL、哈希和
  文件大小必须保持不变。
- 用户安装和升级统一使用 <https://ailingtu.com/install/skills.md>。Codeup 只是
  开发源码，不是安装渠道。
- `auth: lingtu-api-key` 仅用于调用受保护灵途业务接口的 Skill；公开匿名接口使用
  `auth: none`。
- 普通 Skill 发布只更新 TOS/CDN 和数据库，不部署官网。只有官网代码改动才遵循 `www.ailingtu/DEPLOY.md` 发布 Web。

## 项目位置

开发源码仓库为 <https://codeup.aliyun.com/coss/ailingtu/skills>，Git 远程地址为
`git@codeup.aliyun.com:coss/ailingtu/skills.git`。

默认源码项目：

```text
/Users/jason/www/lingtuai/skills.ailingtu   # Skill 源码、构建和测试
```

构建器根据脚本位置定位源码根目录，改名后仍输出到本仓库的 `dist/packages/`。
正式发布不依赖相邻官网仓库；发布 Skill 会本地校验目标目录、打包，并调用线上
SkillHub 发布接口。

## 更新已有 Skill

以下示例更新 `tk-blacklist`，其发布 slug 是 `lingtu-tk-blacklist`。

1. 修改 `packages/tk-blacklist/`。如果端点、请求字段、响应字段或状态处理有变化，
   先阅读并同步 `packages/tk-blacklist/references/api.md`。
2. 在 `SKILL.md` 升级 SemVer 版本号。已发布版本不可覆盖或复用。
3. 运行包内测试和相关仓库测试，并确认脚本语法正常。
4. 从仓库根目录只构建目标包：

```bash
cd /Users/jason/www/lingtuai/skills.ailingtu
python3 scripts/build_package.py tk-blacklist
```

构建产物位于 `dist/packages/`，包括最新版 ZIP、校验文件和元数据。ZIP 解压后
根目录必须直接包含 `SKILL.md`。

5. 确认当前 Agent 已按官方安装文档安装 `lingtu-skillhub-publish`，然后用该 Skill
   对目标技能目录运行密钥状态检查、Lint 和预览。预览不上传：

```bash
python3 ~/.codex/skills/lingtu-skillhub-publish/scripts/lingtu_skillhub_publish.py status
python3 ~/.codex/skills/lingtu-skillhub-publish/scripts/lingtu_skillhub_publish.py lint \
  /Users/jason/www/lingtuai/skills.ailingtu/packages/tk-blacklist --platform lingtu
python3 ~/.codex/skills/lingtu-skillhub-publish/scripts/lingtu_skillhub_publish.py lingtu \
  /Users/jason/www/lingtuai/skills.ailingtu/packages/tk-blacklist
```

检查输出中的目标 slug、版本、平台、目录文案和预览结果。

6. 预览正确并得到用户明确确认后，通过同一个发布 Skill 正式发布：

```bash
python3 ~/.codex/skills/lingtu-skillhub-publish/scripts/lingtu_skillhub_publish.py lingtu \
  /Users/jason/www/lingtuai/skills.ailingtu/packages/tk-blacklist --confirm
```

发布器上传并校验不可变版本 ZIP，事务更新数据库，再导出索引并更新兼容下载别名。安装索引使用不可变 URL；其他 Skill 记录保持不变。

7. 发布器现在事务更新 MySQL 目录与版本记录，再从数据库导出 CDN 索引。官网通过 API 动态读取，因此普通 Skill 发布不修改或部署官网代码。完整中英文文案更新可用 `--catalog /path/catalog.json`，也可放在包根目录 `catalog.json`；已有包不传时保留数据库文案，以 SKILL.md 同步中文名称和简介。
8. 发布只读取 `LINGTU_SKILLHUB_TOKEN`，不读取业务 API Key、官网数据库连接串或
   TOS 凭证。线上 API 负责数据库、不可变 ZIP、索引和兼容下载别名的一致性。

## 新增 Skill

1. 使用脚手架创建包，不要手工复制旧包：

```bash
cd /Users/jason/www/lingtuai/skills.ailingtu
python3 scripts/create_package.py creator-insights \
  --display-name "灵途达人洞察" \
  --summary "分析达人数据并生成可执行建议。" \
  --description "查询达人数据并生成分析结果。" \
  --auth lingtu-api-key
```

公开匿名接口改用 `--auth none`。

2. 完成 `SKILL.md`、`agents/openai.yaml`、`references/api.md` 和 `scripts/`。在根级
   `AGENTS.md` 增加明确路由，在中文 `README.md` 登记新包。
3. 按上一节运行测试和单包构建：

```bash
python3 scripts/build_package.py creator-insights
```

4. 使用 `lingtu-skillhub-publish` 对新技能目录执行 Lint 和预览，得到用户明确确认后
   加 `--confirm` 正式发布：

```bash
python3 ~/.codex/skills/lingtu-skillhub-publish/scripts/lingtu_skillhub_publish.py lint \
  /Users/jason/www/lingtuai/skills.ailingtu/packages/creator-insights --platform lingtu
python3 ~/.codex/skills/lingtu-skillhub-publish/scripts/lingtu_skillhub_publish.py lingtu \
  /Users/jason/www/lingtuai/skills.ailingtu/packages/creator-insights
python3 ~/.codex/skills/lingtu-skillhub-publish/scripts/lingtu_skillhub_publish.py lingtu \
  /Users/jason/www/lingtuai/skills.ailingtu/packages/creator-insights --confirm
```

新增包会追加到线上索引；已有记录必须保持原样。

5. 新 Skill 必须提供完整 `catalog.json`（包内或 `--catalog`）：包括分类、平台、中英文标题/简介/亮点/示例/输入输出/要求。发布器写入数据库后官网自动展示，不再改语言文件或部署官网。

## 发布后验收

每次发布至少完成以下检查：

1. `https://cdn.ailingtu.cn/skills/packages/index.json` 包含目标 slug、正确版本和
   `auth`。
2. 索引中的最新版 URL 和带版本 URL 均可下载。
3. 线上 ZIP 的 SHA-256 和字节数与本地产物一致。
4. 对比发布前后的索引，除目标 slug 外，其他记录的版本、URL、SHA-256 和字节数
   完全不变。
5. 中文 `/skillhub/<package-id>`、英文 `/en/skillhub/<package-id>` 和目录页均返回
   HTTP 200，并显示正确文案。
6. 随机检查至少一个原有 Skill 详情页，确认没有 i18n 或 SSR 回归。
7. 如果发布脚本、索引或页面出现异常，先停止继续发布，不要用全量上传修复单包
   问题。

## 禁止操作

- 不要上传整个 `skills.ailingtu` 仓库。
- 不要把多个 `packages/*` 合并成一个 ZIP。
- 不要绕过 `lingtu-skillhub-publish` 使用官网仓库脚本或手工调用后台 API。
- 不要复用已发布版本号覆盖不可变版本包。
- 不要从 Codeup、GitHub、其他 Skill 商店或浏览器手工上传替代官方 TOS/CDN 流程。
- 不要把 API Key 写入仓库、命令、日志或聊天。

## 打包记录

成功运行 `scripts/build_package.py <package-id>` 后，脚本自动更新根目录
`README.md` 能力表格中该包的版本号、北京时间和负责人；新包自动追加一行。
版本号读取 `SKILL.md`，不会自动升级。首次负责人默认读取 Git `user.name`，
后续保留已有负责人；可用 `--owner "负责人"` 显式指定或变更。
没有可用负责人时在构建前报错；构建失败不会更新表格。
打包完成后，将 README 的记录与包的源码改动一起提交。
