# 灵途 SkillHub 单包发布流程

本文是灵途官方 Skill 发布到 SkillHub 的操作手册。更新已有 Skill 或新增
Skill 时，先完整阅读本文，再执行构建、上传或官网发布。

## 核心原则

- 每次只构建和发布一个 Skill。
- 正常发布必须传入 `--package lingtu-<package-id>`；不要无参数发布整个
  `dist/packages/` 目录。
- 官方索引采用增量合并：只替换指定 slug 的记录，其余记录的版本、URL、哈希和
  文件大小必须保持不变。
- 用户安装和升级统一使用 <https://ailingtu.com/install/skills.md>。GitHub 只是
  开发源码，不是安装渠道。
- `auth: lingtu-api-key` 仅用于调用受保护灵途业务接口的 Skill；公开匿名接口使用
  `auth: none`。
- 官网发布遵循 `www.ailingtu/DEPLOY.md`。不要从有无关改动的工作区直接发布。

## 项目位置

默认使用以下相邻项目：

```text
/Users/jason/www/lingtuai/lingtu-skills   # Skill 源码、构建和测试
/Users/jason/www/lingtuai/www.ailingtu    # TOS/CDN 发布器和 SkillHub 官网
```

## 更新已有 Skill

以下示例更新 `tk-blacklist`，其发布 slug 是 `lingtu-tk-blacklist`。

1. 修改 `packages/tk-blacklist/`。如果端点、请求字段、响应字段或状态处理有变化，
   先阅读并同步 `packages/tk-blacklist/references/api.md`。
2. 在 `SKILL.md` 升级 SemVer 版本号。已发布版本不可覆盖或复用。
3. 运行包内测试和相关仓库测试，并确认脚本语法正常。
4. 从仓库根目录只构建目标包：

```bash
cd /Users/jason/www/lingtuai/lingtu-skills
python3 scripts/build_package.py tk-blacklist
```

构建产物位于 `dist/packages/`，包括最新版 ZIP、校验文件和元数据。ZIP 解压后
根目录必须直接包含 `SKILL.md`。

5. 先从官网项目运行定向 dry-run：

```bash
cd /Users/jason/www/lingtuai/www.ailingtu
npm run skills:publish -- \
  /Users/jason/www/lingtuai/lingtu-skills/dist/packages \
  --package lingtu-tk-blacklist \
  --dry-run
```

检查输出中的目标 slug、版本和最终索引记录数。索引记录数应等于当前线上记录数，
不能因为发布单包而减少。

6. dry-run 正确后，执行同一个目标的正式发布：

```bash
npm run skills:publish -- \
  /Users/jason/www/lingtuai/lingtu-skills/dist/packages \
  --package lingtu-tk-blacklist
```

发布器会上传最新版 ZIP、带版本号的不可变 ZIP，并只合并更新索引中的目标记录。

7. 如果版本、名称、说明、分类、输入输出或认证要求发生变化，同步 SkillHub 官网
   展示。当前目录定义位于 `www.ailingtu/composables/useSkillCatalog.ts`，中英文文案
   位于 `www.ailingtu/locales/zh-CN.json` 和 `en-US.json`。修改前先检查当前实现，
   避免覆盖正在进行的目录数据化改造。
8. 按 `www.ailingtu/DEPLOY.md` 完成 Web 构建、提交和发布。只发布 Web，不执行 MCP
   或数据库迁移。

## 新增 Skill

1. 使用脚手架创建包，不要手工复制旧包：

```bash
cd /Users/jason/www/lingtuai/lingtu-skills
python3 scripts/create_package.py creator-insights \
  --display-name "灵途达人洞察" \
  --summary "分析达人数据并生成可执行建议。" \
  --description "查询达人数据并生成分析结果。" \
  --auth lingtu-api-key
```

公开匿名接口改用 `--auth none`。

2. 完成 `SKILL.md`、`agents/openai.yaml`、`references/api.md` 和 `scripts/`。在根级
   `AGENTS.md` 增加明确路由，在中英文 README 登记新包。
3. 按上一节运行测试和单包构建：

```bash
python3 scripts/build_package.py creator-insights
```

4. 使用完整发布 slug 做定向 dry-run 和正式发布：

```bash
cd /Users/jason/www/lingtuai/www.ailingtu
npm run skills:publish -- \
  /Users/jason/www/lingtuai/lingtu-skills/dist/packages \
  --package lingtu-creator-insights \
  --dry-run

npm run skills:publish -- \
  /Users/jason/www/lingtuai/lingtu-skills/dist/packages \
  --package lingtu-creator-insights
```

新增包会追加到线上索引；已有记录必须保持原样。

5. 在官网 SkillHub 增加目录卡片、中英文详情、分类和认证要求。构建通过后按官网
   发布规范上线。

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

- 不要上传整个 `lingtu-skills` 仓库。
- 不要把多个 `packages/*` 合并成一个 ZIP。
- 不要在日常更新中省略 `--package`。
- 不要复用已发布版本号覆盖不可变版本包。
- 不要从 GitHub、其他 Skill 商店或浏览器手工上传替代官方 TOS/CDN 流程。
- 不要把 API Key 写入仓库、命令、日志或聊天。
