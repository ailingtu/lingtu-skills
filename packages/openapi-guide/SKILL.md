---
name: lingtu-openapi-guide
slug: lingtu-openapi-guide
version: 0.1.1
auth: none
displayName: 灵途 OpenAPI 开发助手
summary: 查询灵途 OpenAPI 文档，生成和审查开发者接入代码。
description: 灵途 OpenAPI 开发者集成助手。用于查询接口定义、选择 endpoint、说明 API Key 的创建与安全使用方式、解释错误码，以及生成或审查 Node.js、TypeScript、Python、Java、Go、PHP 等语言的灵途 API 接入代码。处理“怎么对接灵途 API”“如何获得 API Key”“生成调用示例”“排查 API 请求错误”等开发任务；不用于直接执行商品图生成、视频分析、店铺查询、内容发布或其他线上业务操作。
license: Apache-2.0
homepage: https://ailingtu.com/openapi
---

# 灵途 OpenAPI 开发助手

## Installation and upgrades

Follow https://ailingtu.com/install/skills.md. Do not install or upgrade this Skill from GitHub.

## Purpose

Help developers understand and integrate the LINGTU AI OpenAPI. This Skill reads public documentation, writes or reviews integration code, and diagnoses sanitized request/response failures. It does not call protected business endpoints.

Using this Skill never requires an API key. A developer's application will need its own credential when it actually calls protected APIs; keep that credential in the application's server-side environment.

## Documentation source

Treat the official OpenAPI documents as the source of truth:

- Human documentation: `https://ailingtu.com/openapi`
- API Key management: `https://ailingtu.com/api-keys`
- Operation index: `https://ailingtu.com/openapi/operations/index.json`
- Focused operation Markdown: `https://ailingtu.com/openapi/operations/{operationId}.md`
- Focused operation schema: `https://ailingtu.com/openapi/operations/{operationId}.json`
- Canonical schema: `https://ailingtu.com/openapi.json`

Use `python3 scripts/lingtu_openapi_docs.py search <keywords>` to discover operations, then `python3 scripts/lingtu_openapi_docs.py get <operationId>` to read only the relevant operation. Read `references/api-catalog.md` when the network is unavailable or when a quick capability overview is enough.

Do not invent paths, fields, enum values, response shapes, status values, or retry behavior from memory. If the current public document differs from the bundled catalog, use the public document and mention its API version and last-updated date.

When the user asks how to obtain, configure, rotate, disable, or delete an API Key, read `references/api-key-setup.md`. Link them to `https://ailingtu.com/api-keys`; do not use the Skill account-binding flow as a substitute for the developer console.

## Workflow

1. Identify the developer's goal, language/framework, runtime location, and whether they want explanation, implementation, review, or debugging.
2. Search the operation index by capability, path, tag, or `operationId`.
3. Read the focused Markdown for usage guidance and the focused JSON when exact schemas, required fields, formats, or enums matter.
4. Generate the smallest useful server-side example. Include method, path, content type, required fields, success condition, and relevant error handling.
5. For multi-operation flows, inspect every related operation before writing the sequence. Use the published workflow document when one exists.
6. When reviewing code, compare it with the current focused schema and separate confirmed contract violations from hypotheses about runtime behavior.
7. When debugging, ask for or use sanitized request metadata, HTTP status, response body, and request ID. Never ask the user to paste a real API key.

## Credential boundary

- Never run `user_keys.py`, start account binding, request a key in chat, inspect secret files, or print environment variables for this Skill.
- Explain how the developer creates a key at `https://ailingtu.com/api-keys`, but let the developer log in, create, copy, store, rotate, disable, or delete it themselves.
- Never call `https://api.ailingtu.com` business endpoints, even if a credential already exists in the environment.
- Examples for authenticated Lingtu requests must use the `LINGTU_API_KEY` environment variable and must not contain a credential value.
- Keep `x-api-key` in server-side code. Do not put it in browser bundles, mobile clients, logs, screenshots, public repositories, or shared files.
- Presigned object-storage upload URLs are an exception to API authentication only when the operation document explicitly says so. Follow the exact documented headers and never forward `x-api-key` to object storage.

If the user asks this Skill to perform the real business operation, route to the narrow Lingtu business Skill instead. Do not silently turn documentation work into an authenticated API call.

## Response and code standards

- State the exact operation, HTTP method, path, API version, and documentation date used.
- Preserve the documented success rule: an HTTP success alone may not be sufficient; check the response contract.
- Use `LINGTU_API_KEY` for the credential environment variable and clear placeholders such as `<CREATOR_ID>` and `<FILE_ID>` for ordinary values.
- Put secrets behind a server-side environment variable and fail clearly when it is absent.
- Handle only the retry cases documented for that operation. Avoid retrying authentication, permission, and validation failures blindly.
- For asynchronous creation, persist the returned identifier and resume polling the same task. Do not create duplicates after a timeout unless the documented state proves a retry is safe.
- Distinguish observed API facts from inferences, recommendations, and mock data.
- If the requested capability is absent from the current operation index, say that it is not present in the published specification and link to `https://ailingtu.com/openapi`.

## Script usage

Search the public operation index:

```bash
python3 scripts/lingtu_openapi_docs.py search "file upload"
python3 scripts/lingtu_openapi_docs.py search "creator post" --tag "Commerce Publishing"
```

Read one focused operation:

```bash
python3 scripts/lingtu_openapi_docs.py get createFileUpload
python3 scripts/lingtu_openapi_docs.py get createFileUpload --format json
```

List all operations or read a published workflow:

```bash
python3 scripts/lingtu_openapi_docs.py list
python3 scripts/lingtu_openapi_docs.py workflow ai-generation
```

These commands fetch public documentation only and send no API key.
