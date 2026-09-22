# 配置发布密钥

两把密钥各自创建、各自保存。不要把它们发到聊天里，也不要写进仓库。

检查时运行：

```bash
python3 scripts/lingtu_skillhub_publish.py status
```

只看 `configured` 和 `accepted`。不要用 `echo`、`printenv` 或截图展示密钥。

## 灵途 SkillHub：`LINGTU_SKILLHUB_TOKEN`

这是后台「发布密钥」，以 `blg_` 开头。它不是 https://ailingtu.com/api-keys 里的业务 API Key。

1. 用管理员账号打开 https://ailingtu.com/supermanage/blog/credentials 。
2. 创建凭证，并勾选「允许发布和下架文章、发布和更新官网技能」。不勾选时接口返回 403。
3. 完整密钥只显示一次。保存到密码管理器或运行环境的密钥配置。遗失后撤销旧凭证，再创建新的。
4. 按下面的系统步骤写入 `LINGTU_SKILLHUB_TOKEN`。

这枚密钥同时可以发布官网博客。只给技能发布使用时，不要再勾选公众号群发。

## 腾讯 WorkBuddy：`SKILLHUB_KEY`

这是 skillhub.cn 的 API Key，以 `skh_` 开头。

1. 打开 https://skillhub.cn ，用手机号登录。
2. 在个人中心完成实名认证。未认证不能创建 API Key，也不能发布。
3. 打开 https://skillhub.cn/dashboard/keys ，创建 API Key。完整密钥只显示一次。
4. 按下面的系统步骤写入 `SKILLHUB_KEY`。
5. 发布前还要有本机 `skillhub` 命令。没有就让客户打开 https://skillhub.cn/tutorials 自行安装，装好后执行 `skillhub --version`。不要代替客户下载或执行安装脚本，也不要把 API Key 写进安装命令。

## Mac

1. 按 **Command（⌘）+ 空格**，输入“终端”或 `Terminal`，按回车打开。
2. 把对应命令里的占位符换成真实密钥，保留英文单引号，整行粘贴后回车。一次只配置当前要发布的平台。

```sh
export LINGTU_SKILLHUB_TOKEN='你的发布密钥'; launchctl setenv LINGTU_SKILLHUB_TOKEN "$LINGTU_SKILLHUB_TOKEN"
```

```sh
export SKILLHUB_KEY='你的腾讯APIKey'; launchctl setenv SKILLHUB_KEY "$SKILLHUB_KEY"
```

3. 完全退出使用 Skill 的应用（**Command + Q**）再打开。只关窗口不一定退出。命令行工具可以在这个终端里继续运行。

这组 Mac 命令在当前登录会话有效。注销或重启后需要重新执行。只写进 `.zshrc` 不能保证从桌面打开的应用拿到变量。

## Windows

1. 按 **Win + R**，输入 `powershell`，按回车。不需要管理员。
2. 把占位符换成真实密钥，保留英文单引号，整行粘贴后回车。

```powershell
$env:LINGTU_SKILLHUB_TOKEN = '你的发布密钥'; [Environment]::SetEnvironmentVariable('LINGTU_SKILLHUB_TOKEN', $env:LINGTU_SKILLHUB_TOKEN, 'User')
```

```powershell
$env:SKILLHUB_KEY = '你的腾讯APIKey'; [Environment]::SetEnvironmentVariable('SKILLHUB_KEY', $env:SKILLHUB_KEY, 'User')
```

3. 完全退出使用 Skill 的应用再打开。托盘图标也要退出。若仍提示未配置，注销 Windows 账户后重新登录。

远程服务器、容器或云端 Agent 要在那个运行环境里配置同名变量。本机配置不会自动同步过去。
