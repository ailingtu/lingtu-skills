# Video-Publish API Reference

## 认证

所有请求通过 `x-api-key` header 认证。API base URL 默认 `https://api.ailingtu.com`，可通过 `LINGTU_AI_BASE_URL` 环境变量覆盖。

---

## 接口列表

| 接口 | 用途 |
|------|------|
| `POST /v1/file/presign` | 获取预签名上传 URL |
| `POST /v1/file/confirm` | 确认上传完成 |
| `GET /v1/creatorAccount/pageList` | 获取已授权达人列表 |
| `POST /v1/creator/post/create` | 创建视频 / 带货图文发布任务 |
| `GET /v1/creator/post/pageList` | 按 postId 查询发布任务状态 |
| `GET /v1/creator/tiktokshop/product/listByShop` | 搜索店铺商品 |
| `GET /v1/creator/tiktokshop/product/listByShowcase` | 搜索橱窗商品 |

---

## 达人账号管理

### GET /v1/creatorAccount/pageList

**Query Parameters:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pageSize | number | 是 | 每页数量 |
| pageNumber | number | 是 | 页码 |
| valid | boolean | 否 | 是否有效，默认 true |
| authSource | string | 否 | TIKTOK_SHOP / TIKTOK_LOGIN_KIT / TIKTOK_SHOP_CREATOR |
| usernames | string[] | 否 | 批量按用户名筛选 |
| selectionRegion | string | 否 | 带货达人目标/选择地区筛选，如 US。仅用于 TikTok Shop 带货达人列表；普通 TikTok 列表不按国家筛选 |
| hasPhotoPermission | boolean | 否 | 可选。`true` 时只返回具备带货图文权限（如 `PHOTO_SHOPPABLE_PERMISSION_PRODUCT`）的账号 |

区域字段随后端版本可能不同。生成默认排期时，优先使用更贴近目标市场/店铺市场的字段：`targetRegion`、`targetMarket`、`marketRegion`、`shopRegion`、`selectionRegion`；没有这些字段时再回退到 `oauthRegion` / `registerRegion`。

**Response:**

```json
{
  "code": 0,
  "data": {
    "list": [{
      "id": 1, "creatorId": "gid_xxx", "username": "shop_creator",
      "authSource": "TIKTOK_SHOP", "oauthRegion": "USA",
      "registerRegion": "US", "selectionRegion": "US",
      "targetMarket": "US", "valid": true, "tagNames": ["top-tier"],
      "permissions": ["PHOTO_SHOPPABLE_PERMISSION_PRODUCT", "VIDEO_SHOPPABLE_PERMISSION"]
    }],
    "total": 1, "pageNumber": 1, "pageSize": 200, "totalPages": 1
  }
}
```

**带货图文达人筛选与资格：**

| 方式 | 说明 |
|------|------|
| 服务端筛选（推荐） | 查询参数 `hasPhotoPermission=true`（可选），只返回有图文权限的账号 |
| 客户端兜底 | `authSource` 须为 TikTok Shop（如 `TIKTOK_SHOP_CREATOR`）；`permissions` 含 `PHOTO_SHOPPABLE_PERMISSION_PRODUCT` |

`gen-csv --media-type photo` / 图文 `publish` 会自动带 `hasPhotoPermission=true`；`creators --has-photo-permission` 可手动筛。

---

## 文件上传（Presigned URL）

### POST /v1/file/presign

获取预签名上传 URL。SHA-256 计算方式：`raw bytes → hex → SHA-256`。

**Request Body:**

```json
{
  "fileName": "video.mp4",
  "contentType": "video/mp4",
  "size": 12345678,
  "hash": "<sha256-of-hex-encoded-bytes>"
}
```

**Response:**

```json
{
  "code": 0,
  "data": {
    "fileId": 12345,
    "uploadUrl": "https://s3.xxx/presigned-url",
    "url": "https://cdn.ailingtu.com/xxx.mp4",
    "isNew": true,
    "expiresAt": "2026-07-03T00:00:00Z"
  }
}
```

- `isNew` = true/false（false 表示秒传，文件已存在，跳过 PUT）
- `uploadUrl` 仅在 isNew=true 时需要

### PUT to uploadUrl

```
PUT {uploadUrl}
Content-Type: {contentType}
Body: raw file bytes
```

### POST /v1/file/confirm

确认上传完成。

**Request Body:**

```json
{ "fileId": 12345 }
```

---

## 发布管理

### POST /v1/creator/post/create

支持 **视频**（默认）与 **带货图文**（`mediaType=PHOTO`）。

#### 视频发布（默认 / mediaType 省略或 VIDEO）

**Request Body:**

```json
{
  "businessId": "12345",
  "businessType": "FILE",
  "creatorId": "gid_xxx",
  "title": "Check out this product!",
  "platform": "TIKTOK_SHOP",
  "scheduledAt": 1751702400000,
  "scheduledTz": "America/New_York",
  "oauthRegion": "USA",
  "tiktokShop": {
    "productInfo": {
      "productId": "pid_001234",
      "title": "爆款T恤",
      "source": "SHOP"
    }
  }
}
```

#### 带货图文发布（mediaType=PHOTO）

多图 + **单个**购物车锚点（`MULTI_PHOTO_ONE_ANCHOR`）：

- `businessId`：**默认首图** fileId（用户上传顺序第 1 张）
- `tiktokShopPhoto.businessIds`：**全部图片** fileId，**严格按用户上传顺序**
- `tiktokShopPhoto.productLinks`：**有且仅有 1 个产品**（多图共用一个挂车）

**Request Body:**

```json
{
  "businessId": "591",
  "businessType": "FILE",
  "creatorId": "2077242233106595840",
  "title": "test #12341234",
  "platform": "TIKTOK_SHOP",
  "mediaType": "PHOTO",
  "scheduledAt": 1784896665989,
  "scheduledTz": "America/New_York",
  "tiktokShopPhoto": {
    "postType": "MULTI_PHOTO_ONE_ANCHOR",
    "businessIds": ["591", "592"],
    "productLinks": [
      {
        "productId": "1732280564607717841",
        "title": "Summer Vibes 2026 Vacease Cord",
        "source": "SHOP"
      }
    ],
    "musicInfo": {
      "id": "7567668059796720391",
      "title": "original sound - ivaaan_beltran",
      "author": "𝑰𝒗𝒂𝒏",
      "duration": "15"
    }
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| businessId | string | 是 | 主文件 fileId：视频 id；**图文=首图 id**（与 `businessIds[0]` 一致） |
| businessType | string | 是 | "FILE" 或 "AI_TASK" |
| creatorId | string | 是 | 达人 creatorId |
| title | string | 是 | 文案 / caption |
| platform | string | 是 | "TIKTOK_SHOP" / "TIKTOK" |
| mediaType | string | 是 | `"VIDEO"`=视频；`"PHOTO"`=带货图文（客户端固定传，视频不再省略） |
| scheduledAt | number | 否 | 定时发布时间（epoch ms） |
| scheduledTz | string | 否 | IANA 时区 |
| oauthRegion | string | 否 | 授权区域 |
| tiktokShop | object | 否 | **视频**带货参数（mediaType 非 PHOTO 时） |
| tiktokShop.productInfo | object | 否 | 产品信息 |
| tiktokShop.productInfo.productId | string | 是 | 产品 ID |
| tiktokShop.productInfo.title | string | 是 | 产品标题 |
| tiktokShop.productInfo.source | string | 是 | "SHOP" / "SHOWCASE" |
| tiktokShopPhoto | object | 否 | **图文**带货参数（mediaType=PHOTO 时） |
| tiktokShopPhoto.postType | string | 是 | 固定 `MULTI_PHOTO_ONE_ANCHOR`（多图单锚点） |
| tiktokShopPhoto.businessIds | string[] | 是 | 全部图片 fileId；**顺序=用户上传顺序**；`businessIds[0]` 即首图 |
| tiktokShopPhoto.productLinks | object[] | 是 | 挂车商品；**长度必须为 1**（多图共用一个产品） |
| tiktokShopPhoto.productLinks[].productId | string | 是 | 产品 ID |
| tiktokShopPhoto.productLinks[].title | string | 是 | 购物车标题 |
| tiktokShopPhoto.productLinks[].source | string | 是 | "SHOP" / "SHOWCASE" |
| tiktokShopPhoto.musicInfo | object | 否 | 背景音乐；不传则不挂音乐 |
| tiktokShopPhoto.musicInfo.id | string | 是* | 音乐 ID（有 musicInfo 时必填） |
| tiktokShopPhoto.musicInfo.title | string | 否 | 音乐标题 |
| tiktokShopPhoto.musicInfo.author | string | 否 | 作者 |
| tiktokShopPhoto.musicInfo.duration | string | 否 | 时长（秒，字符串） |
| tiktok | object | 否 | 养号视频参数（platform=TIKTOK） |

**带货图文图片约束（客户端校验）：**

| 项 | 规则 |
|----|------|
| 张数 | 至少 1 张，最多 15 张 |
| 单张大小 | ≤ 10MB |
| 格式 | JPG, JPEG, PNG, WEBP, HEIC, BMP |
| 宽高比 | 9:16 ～ 16:9（含边界，即 `w/h ∈ [9/16, 16/9]`） |

**Response:**

```json
{
  "code": 0,
  "data": {
    "id": 100, "postId": "post_xxx",
    "platform": "TIKTOK_SHOP", "title": "Check out this product!",
    "videoUrl": "https://...", "status": "SCHEDULED"
  }
}
```

---

## 商品查询

### GET /v1/creator/tiktokshop/product/listByShop

搜索店铺商品。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | number | 是 | 创作者账号表主键（`pageList` 返回的整数 `id`，**不是** `creatorId` 字符串） |
| origin | string | 是 | "TIKTOK" |
| pageSize | number | 是 | 每页数量 |
| pageToken | string | 否 | 分页 token |
| titleKeyword | string | 否 | 标题关键词 |

### GET /v1/creator/tiktokshop/product/listByShowcase

搜索橱窗商品。参数同上（无 titleKeyword）。

**Response:**

```json
{
  "code": 0,
  "data": {
    "products": [{
      "id": "pid_xxx", "title": "爆款T恤",
      "price": { "amount": "19.99", "currency": "USD" },
      "images": [{ "url": "https://...", "width": 800, "height": 800 }]
    }],
    "nextPageToken": "", "totalCount": 1
  }
}
```

---

## 错误码

| code | 含义 |
|------|------|
| 0 | 成功 |
| -1 | 参数无效或资源不存在 |
| 401 | 未授权（x-api-key 缺失或无效） |

错误响应包含 `message`（string）字段。

## 发布记录查询（2026-10-11 核对公开规范）

来源：https://ailingtu.com/openapi/operations/listCreatorPosts.json （OpenAPI 1.10.0）。

`GET /v1/creator/post/pageList`，必填 `pageSize`（1～200）、`pageNumber`（从 1 起）。可选 `postId` 为灵途发布任务 ID；另支持 beginTime/endTime（毫秒）、status、creatorUsername、platform 等筛选。CLI 对每个保存的 postId 精确查询，读取 `data.list`。

记录包含 `postId`、`status`、`reason`、`platformPostId`、`scheduledAt`、`scheduledTz`、`publishedAt`。创建成功不是平台发布完成；`SUCCESS` / `COMPLETED` 可报平台成功，`PRE_CHECK_PASSED` 仅预检通过。失败类为 `FAILED` / `SUBMIT_FAILED` / `PRE_CHECK_REJECTED`；`CANCELLED` 表示取消；其他状态保持原值。

查询不到或请求失败不证明未提交。没有 postId 的未知提交不能按相似 caption 自动匹配或重发。CLI 未实现服务端取消/更新任务，不自动重发已创建但最终失败的任务。

## 网页功能迁移合同

按用户要求，将 app.ailingtu/src/api/admin/creatorAccount.ts 与 creatorPostDraft.ts 的 `/admin` 前缀统一替换为 `/v1`，仍只用 `LINGTU_API_KEY` / `x-api-key`。没有公开规范的迁移路径不宣称已完成服务端联调；若服务端 404/403，报告对应路径，不回退 `/admin` 或登录令牌。

- GET `/v1/creatorAccount/tiktok/publishConfig?id=账号主键`：privacyLevelOptions、commentDisabled、duetDisabled、stitchDisabled、maxVideoPostDurationSec。
- GET `/v1/creator/tiktokshop/searchMusic`：id（账号主键）、keyword、pageSize、region、language；翻页带 pageToken 与 searchId。返回 music、hasMore、nextPageToken、searchId。
- GET `/v1/creator/tiktokshop/music/favorites`：pageNumber/pageSize/title。POST favorite：musicId/title/author/duration/coverUrl/playUrl；POST unfavorite：musicId。
- GET `/v1/creator/tiktokBusiness/trendingMusic`：id、genre、countryCode、dateRange（1DAY/7DAY/30DAY/90DAY）。返回 music；发布必须使用 musicSoundId，不使用 commercialMusicId。
- GET `/v1/creator/tiktokBusiness/searchLocation`：id、searchQuery；返回 locations，locationId 与 locationName 成对。
- POST `/v1/creator/tiktokshop/uploadPhoto`：multipart form 的 id、file、returnCoverFileId=true；返回 photoFile.photoUri、coverFileId。
- Business 账号 authSource=TIKTOK_BUSINESS_ACCOUNT_API，platform=TIKTOK_BUSINESS。视频使用 tiktokBusiness（不传 privacyLevel），图文使用 tiktokBusinessPhoto（要求 privacyLevel，有序整数 businessIds，最多15张 JPG/JPEG/WEBP，每张≤10MB）。
- Shop 视频 tiktokShop 可传 musicInfo、preCheck、preCheckOvertime（开启超时固定1800秒）、isAiGenerated、coverUri、coverTimestampMs。图文仍只传 tiktokShopPhoto 的图片、商品、musicInfo，不混入视频字段。
- Business 视频 musicSoundInfo={musicSoundId,musicSoundName,musicSoundArtist,musicSoundVolume,videoOriginalSoundVolume}，音量0～100；Business图文去掉两个音量。locationInfo 的 ID/名称成对。品牌声明和AI标识按各场景发送。
- 顶层 coverFileId 与上传封面返回值一致；有上传封面时不传截帧。Login Kit仅支持截帧，不支持平台音乐或上传封面。
- POST `/v1/creator/post/{cancel,delete,submit,sync}`：postId。update：postId/title/scheduledAt/scheduledTz及各场景配置，不替换主素材。reschedule：postIds/durationHours（1～24），返回 successCount/failedList。
- GET `/v1/creator/post/{detail,monthlyAccountQuota,stats,stats/dailyAccount}`：detail传postId；统计按日期时区账号等筛选。
- POST `/v1/creatorAccount/sync`：id；POST `/v1/creator/tiktokshop/product/addToShowcase`：id、addType以及productIds或productLink。
- 云草稿 `/v1/creator/postDraft/{create,update,detail,pageList,rename,delete,complete}` 沿用网页的schemaVersion=1与lockVersion合同；JSON载荷须为完整网页V1格式，不能直接提交本地plan.json。

所有创建任务只报“已提交”。平台 SUCCESS/COMPLETED 才报发布完成，PRE_CHECK_PASSED 只报预审通过。写操作先预览参数，用户确认后执行，不自动重试提交类请求。
