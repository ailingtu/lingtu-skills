# 灵途 TK 店铺数据查询

通过灵途 AI 接口查询和分析 TK 店铺经营数据，支持店铺列表、店铺日报和经营问题问答。

当前版本以 [`SKILL.md`](./SKILL.md) 文件头部的 `version` 字段为准，安装器可据此判断是否需要升级。

## 主要能力

- 通过灵途 AI 查询可用店铺列表。
- 按店铺 ID、店铺名称和日期查询单店日报。
- 按日期查询全部店铺汇总日报；汇总为空时自动回退至首个店铺的日报。
- 通过灵途 AI 对话接口回答店铺经营问题。
- 为可运行本地工具的智能体提供统一脚本入口。

## 使用要求

所有认证请求仅从环境变量 `LINGTU_API_KEY` 读取密钥，并通过 `x-api-key` 请求头发送。缺少密钥时，引导用户前往 https://ailingtu.com/api-keys 创建或管理密钥，在运行技能的环境中配置后重试。不要将密钥粘贴到聊天中，也不要将密钥、私人媒体或经营数据提交到仓库。

## 脚本用法

查询店铺列表：

```bash
python3 scripts/lingtu_shop_data.py list-shops
```

查询单店日报：

```bash
python3 scripts/lingtu_shop_data.py daily-report --date 2026-06-09
```

查询全部店铺汇总日报：

```bash
python3 scripts/lingtu_shop_data.py summary-report --date 2026-06-09
```

询问店铺经营问题：

```bash
python3 scripts/lingtu_shop_data.py ask "这个店铺最近经营有什么问题？"
```

## 接口参考

修改接口路径、请求字段、响应字段或流式解析前，先阅读 [`references/api.md`](./references/api.md)。
