# 网页发布能力在 Skill 中的使用

所有路径统一 `/v1`，只用 x-api-key。迁移依据 app.ailingtu 的请求类型及发布参数构造；前端代码未修改，也未迁移前端登录令牌、会员弹窗或短信校验。服务端权限与额度仍由接口判定。不宣称未联调的路径已在服务端开放。

## 发布场景

| platform | media-type | 功能 |
|---|---|---|
| tiktok_shop | video | 商品、平台配乐、预审、AI标识、上传或截帧封面 |
| tiktok_shop | photo | 多图单商品锚点、平台配乐 |
| tiktok | video | Login Kit，账号允许的隐私与互动、品牌声明、AI标识、截帧 |
| tiktok_business | video | 高级版，商用配乐与两个音量、地域、互动、品牌声明、AI标识、封面 |
| tiktok_business | photo | 高级版不带货图文，隐私、评论、品牌声明、选曲或自动配乐、地域 |

先 creators 查询当前平台的授权账号。普通与高级版账号不按国家筛选；图文仅 Shop 查询需要 hasPhotoPermission。高级版图文仅 JPG/JPEG/WEBP，每张≤10MB、1～15张，不沿用Shop图片格式名单。

## 选曲与试听

```bash
python3 scripts/lingtu_video_publish.py music search --creator alice --keyword summer --region US --language en
# 搜索结果翻页必须同时保留原pageToken和searchId
python3 scripts/lingtu_video_publish.py music search --creator alice --keyword summer --page-token TOKEN --search-id SESSION
python3 scripts/lingtu_video_publish.py music favorites --keyword summer
python3 scripts/lingtu_video_publish.py music favorite --params-file /path/to/favorite.json
python3 scripts/lingtu_video_publish.py music favorite --params-file /path/to/favorite.json --confirm
python3 scripts/lingtu_video_publish.py music unfavorite --music-id MUSIC_ID --confirm
python3 scripts/lingtu_video_publish.py music trending --creator business_alice --genre ALL --country-code US --date-range 7DAY
python3 scripts/lingtu_video_publish.py location --creator business_alice --search-query london
```

展示若干真实候选曲名、作者、时长、排名（如有）和试听链接。使用服务端返回的 playUrl/previewUrl，不下载远程音频绕过展示限制。用户选择后将ID及展示信息写入发布设置并重新预览。热门音乐用 musicSoundId，绝不能把 commercialMusicId 写入 id。试听URL可能过期，过期后重新查。

收藏参数：`{"musicId":"ID","title":"Tune","author":"Artist","duration":"15"}`，可选 coverUrl/playUrl。收藏与取消也属于写操作，按用户明确要求执行。

## 发布设置

```bash
python3 scripts/lingtu_video_publish.py publish-config --creator alice --platform tiktok
python3 scripts/lingtu_video_publish.py quota
python3 scripts/lingtu_video_publish.py configure --folder /path/to/batch --row 0 --settings-file /path/to/settings.json
# 省略row应用到全批；替换整份设置，未提供的旧字段不保留
python3 scripts/lingtu_video_publish.py publish --folder /path/to/batch
```

Agent 根据对话写设置JSON，不要求用户理解接口字段。configure 把JSON存入CSV的「发布设置」，不保存凭据。字段都需属于该场景；设置变化使预览失效，重跑校验并取得确认。

带货视频设置示例：

```json
{
  "musicInfo": {"id": "MUSIC_ID", "title": "Tune", "author": "Artist", "duration": "15"},
  "preCheck": true,
  "preCheckOvertime": 1800,
  "isAiGenerated": true,
  "coverFile": "/absolute/path/cover.jpg"
}
```

高级版视频设置示例：

```json
{
  "musicInfo": {"id": "MUSIC_SOUND_ID", "title": "Tune", "author": "Artist", "musicSoundVolume": 30, "videoOriginalSoundVolume": 100},
  "locationInfo": {"locationId": "LOCATION_ID", "locationName": "London"},
  "disableComment": false,
  "brandContentToggle": false,
  "brandOrganicToggle": false,
  "aigc": true,
  "coverTimestampMs": 0
}
```

高级版图文允许 privacyLevel、autoAddMusic、disableComment、brandContentToggle、brandOrganicToggle、musicInfo（无音量）、locationInfo。Login Kit允许 privacyLevel、disableComment、disableDuet、disableStitch、brandContentToggle、brandOrganicToggle、aigc、coverTimestampMs，不能加曲目或上传封面。立即发布加 publishImmediately=true，并在用户方案中明确显示立即发布。

封面上传时自动使用该账号主键和 returnCoverFileId=true；封面文件也进入内容指纹。上传后传coverFileId，Shop额外传photoUri对应的coverUri。封面与截帧互斥。

非带货发布前读取账号发布配置，不允许不在列表中的隐私范围；账号已禁止互动时必须保持禁用。视频时长通过ffprobe读取，并检查账号maxVideoPostDurationSec；缺少ffprobe或不可播放时提示安装/修复，不能假装校验通过。文案保持用户原文，带货≤4000，非带货≤2000；只有购物车标题继续限制标点/表情与30字符。

## 排期与AI

plan 支持 --times 09:00,19:00 --count 2，明确时间不再额外错峰。--skip-existing-days 查询每个账号已有活动排期并跳过对应当地日期。默认仍使用原错峰时间。所有非立即提交至少距当前5分钟，上传后再次检查。

AI排期不需要把整个前端页面迁入：Agent可按用户要求形成建议，或通过 `service ai-schedule --params-file request.json` 预览，再加 --confirm 调用 `/v1/relay/chat/completions`（model/messages，stream=false）。结果可用 --output 保存。必须核对达人、素材、商品和时区不变，修改CSV后重新展示确认；不直接把模型返回当成已授权发布。

## 发布任务管理

```bash
python3 scripts/lingtu_video_publish.py posts list --params-file filters.json
python3 scripts/lingtu_video_publish.py posts detail --post-id POST_ID
python3 scripts/lingtu_video_publish.py posts cancel --post-id POST_ID
python3 scripts/lingtu_video_publish.py posts cancel --post-id POST_ID --confirm
python3 scripts/lingtu_video_publish.py posts submit --post-id POST_ID --confirm
python3 scripts/lingtu_video_publish.py posts sync --post-id POST_ID --confirm
python3 scripts/lingtu_video_publish.py posts update --params-file update.json
python3 scripts/lingtu_video_publish.py posts reschedule --params-file reschedule.json
python3 scripts/lingtu_video_publish.py posts stats --params-file filters.json
python3 scripts/lingtu_video_publish.py posts daily --params-file filters.json
```

update.json 需要 postId/title/scheduledAt/scheduledTz；配置结构采用服务端原生 tiktokShop/tiktokShopPhoto/tiktok/tiktokBusiness/tiktokBusinessPhoto，先detail读取并保留未修改配置，不直接发送configure的简化结构。主素材不替换，修改图片/视频要另做新方案，并先处理旧任务。reschedule.json=`{"postIds":["p1"],"durationHours":6}`；展示成功数量与failedList，不能把部分失败报成全部成功。

所有POST默认只展示请求；确认后加--confirm，不能自动重试提交类操作。posts submit 是重新提交同一服务端任务，不要新建一条来替代失败重提。取消、修改、重排后刷新status；本地旧方案不代表服务端更新后状态。可用delete删除失败/取消记录，bind-video/to-library沿用网页相同参数合同。

账号与商品辅助接口：service account-sync、managers、showcase-add，参数见api.md。无授权仍优先引导网页完成授权，不生成灵途账号绑定URL。

## 云端草稿

```bash
python3 scripts/lingtu_video_publish.py draft list
python3 scripts/lingtu_video_publish.py draft detail --draft-id DRAFT_ID --output /path/to/draft-detail.json
python3 scripts/lingtu_video_publish.py draft create --params-file webpage-v1-create.json
python3 scripts/lingtu_video_publish.py draft update --params-file webpage-v1-update.json --confirm
```

提供网页云草稿API的查询和管理入口；目前**不自动将本地CSV/plan.json转换为网页草稿**，也不把云草稿直接当成本地素材路径发布。保存必须使用完整网页V1：accountSelections、scheduleSettings、lastAiScheduleResult、publishTasks、unassignedMedia，以及同次生成的fileIds/taskCount/accountCount。发布设置、音乐和地域都在各publishTasks中保存；本地File和blob地址不得保存。

update/rename/delete/complete带已读取的lockVersion，版本冲突保留数据，不能自动覆盖。complete只在该云草稿全部任务已明确提交成功后执行，失败只重试同一份complete请求，绝不重新发布。未知schemaVersion拒绝写入。详情输出保留网页原始Payload和resolvedFiles，不改字段、不强塞默认值；恢复编辑可交给网页继续。
