# Lingtu Report Render API

## Shared Configuration

- Base URL: `https://api.ailingtu.com`
- Authentication header: `x-api-key: <LINGTU_API_KEY>`
- Do not commit API keys.

## HTML Composition

Used to turn a template + data payload into a finished HTML page.

```http
POST /v1/ai/chat/complete
```

Request body:

```json
{
  "roleId": "html_design",
  "promptId": "html_design_basic",
  "stream": false,
  "params": {
    "template": "<full reference HTML — see templates/*.example.html>",
    "content": "<JSON-stringified business data>"
  }
}
```

Notes:

- `template` carries one of the `templates/*.example.html` files from this package. The composer treats it as the visual contract to mimic.
- `content` is the business JSON returned by the upstream skill, stringified. The composer must not invent or drop numbers.
- `stream` is always `false` for this skill — the renderer needs the full HTML before screenshot.

Expected response shape (subject to evolution; the script accepts the common variants):

```json
{
  "data": {
    "content": "<!DOCTYPE html>...</html>"
  }
}
```

The script also accepts:

- `{"content": "..."}`
- `{"data": "..."}`
- `{"data": {"text": "..."}}`
- `{"choices": [{"message": {"content": "..."}}]}`

## Modes

The script has two render modes; this endpoint is only used by `ai` mode.

- `fill` (default): no API call. The script renders `templates/<id>.template.html` locally with a stdlib mini engine (`{{var}}`, `{{var.sub}}`, `{% if %}`, `{% for %}`). Use this when you already know the field names and want speed/determinism.
- `ai`: hits this endpoint with `templates/<id>.example.html` as the visual reference. Use this when the data shape is still moving or you want richer composition.

Switch modes with `--mode ai|fill` or the `LINGTU_REPORT_MODE` env var.

## Forbidden response content

The script strips any of the following from the returned HTML before screenshotting:

- `<script>`, `<iframe>`, `<object>`, `<embed>`, `<link rel="import">`
- inline event handlers (`on*=`)
- `javascript:` URLs
- remote `<link>` and `<style>` references with absolute URLs

If stripping leaves the HTML structurally invalid, the renderer falls back to the raw template.
