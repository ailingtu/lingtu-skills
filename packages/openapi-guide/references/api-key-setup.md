# API Key creation and safe use

Read this reference when a developer asks how to obtain, configure, use, rotate, disable, or delete a LINGTU AI API Key.

## Create a key

1. Open <https://ailingtu.com/api-keys> and log in with a LINGTU AI account.
2. Confirm the current company/account context. The created API Key belongs to the current company.
3. Select **创建 API Key**.
4. Enter a descriptive name based on the environment or integration, such as `Production backend`, `Staging worker`, or `Local development`. This makes later rotation and revocation safer.
5. Optionally choose an expiration time. Leaving it empty creates a key without an expiration according to the current management page.
6. Create the key, then copy and store it immediately in a password manager, deployment secret store, or server-side environment variable.

Never ask the developer to paste the resulting key into chat. The Skill does not create the key on the user's behalf and does not inspect where it was stored.

## Configure an application

Use a server-side secret named `LINGTU_API_KEY` unless the developer's project already has a suitable naming convention:

```bash
export LINGTU_API_KEY="<YOUR_API_KEY>"
```

Do not commit `.env` files containing the value. For deployed applications, prefer the hosting platform's secret manager or encrypted environment configuration.

Send the value in the `x-api-key` request header to the production API base URL:

```bash
curl --request GET \
  "https://api.ailingtu.com/<documented-path>" \
  --header "x-api-key: ${LINGTU_API_KEY}"
```

Server-side JavaScript:

```js
const apiKey = process.env.LINGTU_API_KEY;
if (!apiKey) throw new Error("LINGTU_API_KEY is not configured");

const response = await fetch("https://api.ailingtu.com/<documented-path>", {
  headers: { "x-api-key": apiKey },
});
```

Server-side Python:

```python
import os
import requests

api_key = os.environ.get("LINGTU_API_KEY")
if not api_key:
    raise RuntimeError("LINGTU_API_KEY is not configured")

response = requests.get(
    "https://api.ailingtu.com/<documented-path>",
    headers={"x-api-key": api_key},
    timeout=30,
)
```

Replace `<documented-path>` only after reading the focused operation document. Add the documented query parameters, body, content type, timeout, retry behavior, and success checks for that operation.

## Validate responses

For the current shared JSON response envelope, treat a call as successful only when both conditions hold:

- The HTTP status is successful.
- The response body satisfies the documented business-success condition, currently `code === 0`.

Streaming operations and presigned object-storage uploads may follow different response and authentication rules. Read the focused operation document instead of applying the JSON-envelope rule blindly. In particular, do not send `x-api-key` to an object-storage upload URL when the documentation says to upload with the presigned URL alone.

## Protect and rotate keys

- Keep keys in backend services, workers, CLIs, or secret managers—not browser code, mobile clients, logs, screenshots, analytics events, public repositories, or shared files.
- Use separate keys for development, staging, production, and independent integrations when practical.
- Set an expiration when the integration can support rotation.
- The management page shows status, expiration, last-used time, and management actions. Use these signals to identify unused or stale keys.
- Disable a key when temporarily suspending an integration. Re-enable it only after confirming the intended consumer.
- Delete a compromised or retired key. Requests using a deleted key stop working immediately, and deletion cannot be undone.
- When rotating, create and deploy the replacement first, verify the integration, then disable or delete the old key.

## Authentication failures

- `401` generally means the key is missing, malformed, expired, disabled, deleted, or otherwise invalid. Confirm the server-side environment and header name without printing the key.
- `403` generally means the authenticated company or credential lacks permission for the requested operation or resource.
- Do not retry `401` or `403` in a loop. Correct the credential or permission configuration first.

Use sanitized diagnostics only: HTTP status, response `code`, `message`, request ID, method, path, and whether the header was present. Never log or display the header value.
