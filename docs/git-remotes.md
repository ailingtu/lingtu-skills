# Git 双源同步

Codeup 与 GitHub 保存同一份开发源码和提交历史：

| 远程名称 | 拉取地址 | 推送地址 |
| --- | --- | --- |
| `origin` | `git@codeup.aliyun.com:coss/ailingtu/skills.ailingtu.git` | Codeup 与 GitHub |
| `github` | `git@github.com:ailingtu/lingtu-skills.git` | GitHub |

用户安装与升级仍统一使用 <https://ailingtu.com/install/skills.md>。
以下命令仅用于开发者维护已有源码工作区，不是 Skill 安装命令。

## 配置已有工作区

Git 远程配置仅保存在各自工作区，不随提交同步。其他开发者需要分别配置。
先执行 `git remote -v` 和 `git remote get-url --push --all origin` 检查已有设置。
当 `origin` 已指向 Codeup、尚未添加 `github`、尚未配置显式 push URL 时，执行一次：

```sh
git remote add github git@github.com:ailingtu/lingtu-skills.git
git config --add remote.origin.pushurl git@codeup.aliyun.com:coss/ailingtu/skills.ailingtu.git
git config --add remote.origin.pushurl git@github.com:ailingtu/lingtu-skills.git
```

若已有对应设置，调整现有项，避免重复添加。需要具备两个仓库的 SSH 推送权限。

## 日常开发

从 Codeup 拉取默认主线；查看 GitHub 上的新增提交时单独获取：

```sh
git fetch origin
git fetch github
git log --oneline main..origin/main
git log --oneline main..github/main
```

有人向任一平台提交新改动时，先合并到本地主线并完成检查，再同步两边：

```sh
git push origin main
```

Git 会依次向两个 push URL 推送，不是跨平台原子操作。如果只有一边成功，
先检查失败原因与远程提交，再补推；不要强制覆盖同事的新提交。

核对两边 `main` 与本地提交一致：

```sh
git rev-parse main
git ls-remote git@codeup.aliyun.com:coss/ailingtu/skills.ailingtu.git refs/heads/main
git ls-remote git@github.com:ailingtu/lingtu-skills.git refs/heads/main
```
