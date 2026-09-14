# 配置灵途 API Key

还没有配置 `LINGTU_API_KEY`。按下面步骤配置一次，再回来重试。

## 1. 获取密钥

打开 https://ailingtu.com/api-keys ，登录后创建或复制 API Key。
密钥只粘贴到你自己电脑的终端中，不要发送到聊天里。

## 2. 按电脑系统配置

### Mac

1. 按 **Command（⌘）+ 空格**，输入“终端”或 `Terminal`，按回车打开。
2. 将下面命令中的 `你的_API_Key` 替换为自己的真实密钥，保留两侧的英文单引号，然后整行粘贴到终端，按回车执行。

```sh
export LINGTU_API_KEY='你的_API_Key'; launchctl setenv LINGTU_API_KEY "$LINGTU_API_KEY"
```

3. 完全退出使用 Skill 的应用（**Command + Q**），再重新打开，重试原来的任务。只关闭窗口不一定会退出应用。若使用命令行工具，在刚才这个终端中启动它。

这套 Mac 命令在当前登录会话有效；注销或重启电脑后需要重新执行。只写入终端的 `export` 或 `.zshrc` 并不能保证从桌面打开的应用拿到变量。

### Windows

1. 按 **Win + R**，输入 `powershell`，按回车打开 Windows PowerShell。无需管理员权限。
2. 将下面命令中的 `你的_API_Key` 替换为自己的真实密钥，保留两侧的英文单引号，然后整行粘贴到 PowerShell，按回车执行。命令会同时配置当前窗口并保存到当前 Windows 用户，重启电脑后仍然有效。

```powershell
$env:LINGTU_API_KEY = '你的_API_Key'; [Environment]::SetEnvironmentVariable('LINGTU_API_KEY', $env:LINGTU_API_KEY, 'User')
```

3. 完全退出使用 Skill 的应用，再重新打开，重试原来的任务。如果应用有托盘图标，也要从托盘退出。若使用命令行工具，可直接在刚才这个 PowerShell 中启动它。

如果新打开的应用仍提示未配置，请注销 Windows 账户后重新登录，再打开应用。

## 3. 仍然提示未配置时

告诉 Agent 你的操作系统和使用 Skill 的应用名称，不要发送密钥。
本机配置只影响本机进程；若 Skill 实际运行在远程服务器、容器或云端，需要在对应运行环境的密钥或环境变量设置中配置 `LINGTU_API_KEY`。
检查时只报告“已配置 / 未配置”，不要用 `echo`、`printenv` 或截图展示密钥。

参考：[Apple 终端环境变量说明](https://support.apple.com/en-mt/guide/terminal/apd382cc5fa-4f58-4449-b20a-41c53c006f8f/mac)、[Microsoft PowerShell 环境变量说明](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables)。Mac 桌面进程设置以本机 `man launchctl` 的 `setenv` 说明为准。
