# Lingtu Shop Data API

## Shared Configuration

- Base URL: `https://api.ailingtu.com`
- Authentication header: `x-api-key: <LINGTU_API_KEY>`
- Do not commit API keys.

## Shop List

Fetch shops in realtime before resolving default or named-shop daily reports.

```http
GET /v1/shop/list
```

The exact response envelope may evolve. The script accepts common shapes such as:

- `{"data":[...]}`
- `{"data":{"list":[...]}}`
- `{"data":{"records":[...]}}`
- a raw JSON array

Shop id fields accepted by the script: `id`, `shopId`, `targetId`.

Shop name fields accepted by the script: `name`, `shopName`, `title`.

## Shop Daily Report

```http
GET /v1/report/biz/detail?targetType=SHOP&targetId={shop_id}&reportDate={YYYY-MM-DD}
```

Example:

```http
GET /v1/report/biz/detail?targetType=SHOP&targetId=1391&reportDate=2026-06-09
```

Routing:

- If the user gives a shop name, fetch `/v1/shop/list`, match by exact name first, then substring match.
- If the user gives a numeric shop id, call the report endpoint directly.

## All-Shops Summary Report

Use this when the user asks about overall / cross-shop operations (整体经营情况、全部店铺数据汇总、大盘数据、总 GMV/订单 等不指定店铺的口径).

```http
GET /v1/report/biz/summary?reportDate={YYYY-MM-DD}
```

Fallback: when the summary response body is empty (`null`, empty string, `[]`, `{}`, or a `{ "data": <empty> }` envelope), the script falls back to `/v1/report/biz/detail` using the first shop from `/v1/shop/list` and returns both the original empty summary and the fallback daily report so the caller can see why the fallback fired.

## AI Chat

Use this for shop operations questions when the user is not asking to fetch a specific daily report.

```http
POST /v1/ai/chat/create
```

The endpoint returns a streaming response. The script sends JSON with a `message` field and also includes `prompt` and `content` aliases for compatibility until the final backend contract is fixed. It parses common stream formats:

- Server-sent events lines prefixed with `data:`
- JSON chunks containing `content`, `text`, `message`, `delta.content`, or `choices[].delta.content`
- Plain text chunks

