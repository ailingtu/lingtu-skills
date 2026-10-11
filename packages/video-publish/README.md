# TikTok 视频与图文批量发布 By 灵途 AI

从素材文件夹生成可审核的发布方案，确认后上传素材、创建定时任务，再按任务 ID 查询结果。保留 CSV/XLSX 排期入口。

```bash
# 选定达人后准备方案（每份素材只分配给一个达人）
python3 scripts/lingtu_video_publish.py plan \
  --media-folder /path/to/videos --output-dir /path/to/batch \
  --platform tiktok --creators alice,bob --distribution distribute \
  --date 2026-10-12 --count 2 --title "Reviewed caption"

# 修改草稿；逐行内容也可由 Agent 编辑 CSV
python3 scripts/lingtu_video_publish.py fill --folder /path/to/batch --col title --row 0 --value "Caption A"

# 校验、展示实际发布内容，用户确认后提交
python3 scripts/lingtu_video_publish.py publish --folder /path/to/batch
python3 scripts/lingtu_video_publish.py publish --folder /path/to/batch --confirm

# 查询最终状态
python3 scripts/lingtu_video_publish.py status --folder /path/to/batch --refresh
```

图文用 `--platform tiktok_shop --media-type photo`，每个直接子文件夹是一篇图文。挂车提供 `--product-id`，自动查标题；可用 `--product-title` 明确指定。多账号的分配必须选择 distribute 或 all，后者每个账号都发全部素材。每日条数为 1～7，素材多则延伸日期，不循环素材。

方案保存 schedule.csv、plan.json、发布方案.md；校验通过保存 review.json；提交结果逐条保存 publish-journal.json。素材或账号身份变化需重新审核。重复执行跳过已有任务；只有提交前明确失败的条目可加 `--retry-failed` 重试。创建请求中断或超时后状态不明，禁止自动重发。去重只覆盖同一方案目录，保留目录及提交记录。

任务创建成功并不代表平台发布成功。查询 SUCCESS / COMPLETED 后才报成功；PRE_CHECK_PASSED 仅预检通过。已提交条目的方案修改不会更新旧服务端任务；先处理旧任务再确认新方案，使用 posts detail/update/cancel 管理旧服务端任务，不把本地修改误报成服务端已修改。

命令：plan、creators、products search、fill、publish、status、gen-csv。新增 music、location、configure、publish-config、quota、posts、draft 和 service。完整操作参见 SKILL.md、references/migrated-workflow.md 和 `--help`。

支持5种网页发布场景，接口统一/v1。云草稿提供网页V1 JSON接口管理，不自动转换本地CSV。非带货视频需要ffprobe读取时长。

Python 3.9+，CSV 无第三方依赖；旧 XLSX 需要 openpyxl。认证只使用 LINGTU_API_KEY，通过 x-api-key 发送。密钥配置见 https://ailingtu.com/api-keys ，不在聊天或文件中保存真实密钥。
