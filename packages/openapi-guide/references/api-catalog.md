# LINGTU AI OpenAPI capability catalog

Bundled discovery snapshot for offline use only.

- API version: `1.9.0`
- Last updated: `2026-09-01`
- Source project: `www.ailingtu/data/openapi.ts`
- Current operation index: <https://ailingtu.com/openapi/operations/index.json>
- Canonical schema: <https://ailingtu.com/openapi.json>

When network access is available, use the current public operation index and focused operation documents instead of relying on this snapshot.

## Commerce Publishing

| operationId | Method | Path | Purpose |
|---|---|---|---|
| `createTikTokShopAuthorizationUrl` | GET | `/v1/creatorAccount/tiktokShopOauth/authorize` | Create a TikTok Shop creator authorization URL |
| `listCreatorAccounts` | GET | `/v1/creatorAccount/pageList` | List authorized creator accounts |
| `listTikTokShowcaseProducts` | GET | `/v1/creator/tiktokshop/product/listByShowcase` | List creator showcase products |
| `searchTikTokShopMusic` | GET | `/v1/creator/tiktokshop/searchMusic` | Search TikTok music |
| `addTikTokShowcaseProducts` | POST | `/v1/creator/tiktokshop/product/addToShowcase` | Add products to a creator showcase |
| `createCreatorPost` | POST | `/v1/creator/post/create` | Create a creator publishing task |
| `cancelCreatorPost` | POST | `/v1/creator/post/cancel` | Cancel a creator publishing task |
| `updateCreatorPost` | POST | `/v1/creator/post/update` | Update a creator publishing task |
| `listCreatorPosts` | GET | `/v1/creator/post/pageList` | List creator publishing records |

## File Upload

| operationId | Method | Path | Purpose |
|---|---|---|---|
| `createFileUpload` | POST | `/v1/file/presign` | Create a presigned file upload |
| `confirmFileUpload` | POST | `/v1/file/confirm` | Confirm a file upload |
| `uploadTikTokShopVideoCover` | POST | `/v1/creator/tiktokshop/uploadPhoto` | Upload a TikTok Shop video cover |

## AI Content Generation

| operationId | Method | Path | Purpose |
|---|---|---|---|
| `createAiGenerationSchedule` | POST | `/v1/ai/schedule/create` | Create an AI media generation schedule |
| `listAiTasksByScheduleId` | GET | `/v1/ai/task/listByScheduleId` | List AI generation tasks by schedule ID |

Read the current workflow at <https://ailingtu.com/openapi/workflows/ai-generation.md> before generating an end-to-end implementation.

## Creator and content data

| operationId | Method | Path | Purpose |
|---|---|---|---|
| `fetchTikTokCreatorPosts` | GET | `/v1/influencer/fetchPosts` | Fetch a TikTok creator profile and recent posts |
| `fetchInstagramCreatorPosts` | GET | `/v1/influencer/ins/fetchPosts` | Fetch an Instagram creator profile and recent posts |
| `fetchPublicVideoData` | POST | `/v1/material/fetch` | Fetch public video data |

## AI and video understanding

| operationId | Method | Path | Purpose |
|---|---|---|---|
| `streamViralVideoReplication` | POST | `/v1/material/analysisTask/stream` | Stream a viral-video replication prompt |
| `createRelayChatCompletion` | POST | `/v1/relay/chat/completions` | Relay a chat completion to a supported model |

## Shared contract facts

- Production API base URL: `https://api.ailingtu.com`.
- Protected operations use the `x-api-key` request header.
- JSON calls succeed only when the HTTP status is successful and the response body satisfies the documented success contract, currently `code === 0` for the shared response envelope.
- Keep API keys on the server; never place them in browser code, logs, or public files.
- Retry guidance and exceptions must be taken from the current focused operation document.
