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
| `POST /v1/creator/post/create` | 创建视频发布任务 |
| `GET /v1/creator/tiktok/product/listByShop` | 搜索店铺商品 |
| `GET /v1/creator/tiktok/product/listByShowcase` | 搜索橱窗商品 |

---

## 达人账号管理

### GET /v1/creatorAccount/pageList

**Query Parameters:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pageSize | number | 是 | 每页数量 |
| pageNumber | number | 是 | 页码 |
| valid | boolean | 否 | 是否有效，默认 true |
| authSource | string | 否 | TIKTOK_SHOP / TIKTOK_LOGIN_KIT |
| usernames | string[] | 否 | 批量按用户名筛选 |

**Response:**

```json
{
  "code": 0,
  "data": {
    "list": [{
      "id": 1, "creatorId": "gid_xxx", "username": "shop_creator",
      "authSource": "TIKTOK_SHOP", "oauthRegion": "USA",
      "registerRegion": "US", "valid": true, "tagNames": ["top-tier"]
    }],
    "total": 1, "pageNumber": 1, "pageSize": 200, "totalPages": 1
  }
}
```

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

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| businessId | string | 是 | fileId（上传返回的 id） |
| businessType | string | 是 | "FILE" 或 "AI_TASK" |
| creatorId | string | 是 | 达人 creatorId |
| title | string | 是 | 视频文案 |
| platform | string | 是 | "TIKTOK_SHOP" / "TIKTOK" |
| scheduledAt | number | 否 | 定时发布时间（epoch ms） |
| scheduledTz | string | 否 | IANA 时区 |
| oauthRegion | string | 否 | 授权区域 |
| tiktokShop | object | 否 | 带货参数 |
| tiktokShop.productInfo | object | 否 | 产品信息 |
| tiktokShop.productInfo.productId | string | 是 | 产品 ID |
| tiktokShop.productInfo.title | string | 是 | 产品标题 |
| tiktokShop.productInfo.source | string | 是 | "SHOP" / "SHOWCASE" |
| tiktok | object | 否 | 养号视频参数 |

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

### GET /v1/creator/tiktok/product/listByShop

搜索店铺商品。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | number | 是 | 创作者账号 ID |
| origin | string | 是 | "TIKTOK" |
| pageSize | number | 是 | 每页数量 |
| pageToken | string | 否 | 分页 token |
| titleKeyword | string | 否 | 标题关键词 |

### GET /v1/creator/tiktok/product/listByShowcase

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
