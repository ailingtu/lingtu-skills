#!/usr/bin/env python3
"""Render a Lingtu report image from a template + data JSON payload.

Two modes:

  fill (default)
      Use a placeholder template `<id>.template.html` rendered with a tiny
      stdlib engine: `{{ key }}`, `{{ key.sub }}`, `{% for x in items %} ... {% endfor %}`,
      `{% if key %} ... {% endif %}`. No AI call. Fastest, deterministic.

  ai
      Send a reference template `<id>.example.html` plus the data to
      `POST /v1/ai/chat/complete` (roleId=html_design, promptId=html_design_basic),
      let the model emit a full HTML document. Slower, more flexible when the
      data shape is still moving.

Both modes go through the same sanitize -> number-check -> screenshot pipeline,
and any failure in either falls back to a minimal white-card view so the caller
never sees an error.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from html import escape as html_escape
from pathlib import Path


DEFAULT_BASE_URL = "https://api.ailingtu.com"
COMPOSE_PATH = "/v1/ai/chat/complete"
ROLE_ID = "html_design"
PROMPT_ID = "html_design_basic"

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PACKAGE_ROOT / "templates"
OUTPUT_DIR = PACKAGE_ROOT / "output"

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

from lingtu_auth import require_api_key


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def api_key():
    return require_api_key()


def base_url():
    return os.environ.get("LINGTU_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


# ---------------------------------------------------------------------------
# Template & data loading
# ---------------------------------------------------------------------------

def template_path(template_id, mode):
    if mode == "ai":
        names = (f"{template_id}.example.html", f"{template_id}.template.html")
    else:
        names = (f"{template_id}.template.html", f"{template_id}.example.html")
    for name in names:
        candidate = TEMPLATES_DIR / name
        if candidate.exists():
            return candidate
    available = sorted(p.name for p in TEMPLATES_DIR.glob("*.html"))
    raise SystemExit(f"Template {template_id!r} not found. Available: {available}")


def load_template(template_id, mode):
    return template_path(template_id, mode).read_text(encoding="utf-8")


def load_data(data_arg):
    if data_arg == "-":
        return json.loads(sys.stdin.read())
    if data_arg.startswith("{") or data_arg.startswith("["):
        return json.loads(data_arg)
    path = Path(data_arg)
    if not path.exists():
        raise SystemExit(f"Data file not found: {data_arg}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Per-template defaults
# ---------------------------------------------------------------------------

def apply_defaults(template_id, data):
    """Merge sensible defaults so callers can pass tiny payloads."""
    if not isinstance(data, dict):
        return data
    merged = dict(data)
    if template_id == "daily_report":
        merged.setdefault("title", "店铺日报")
        merged.setdefault("subtitle", datetime.now().strftime("%Y-%m-%d"))
        merged.setdefault("summary", "")
        merged.setdefault("summary_emoji", "")
        merged.setdefault("metrics", [])
        merged.setdefault("metrics_title", "核心指标")
        merged.setdefault("insights", [])
        merged.setdefault("insights_title", "今日洞察")
        merged.setdefault(
            "footer",
            f"Powered by Lingtu · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )
        cols = len(merged["metrics"])
        merged["metrics_columns"] = 4 if cols >= 4 else max(2, cols or 2)
    return merged


# ---------------------------------------------------------------------------
# Mini template engine: {{x}}, {{x.y}}, {% for x in xs %}, {% if x %}
# ---------------------------------------------------------------------------

TOKEN_PATTERN = re.compile(
    r"""
    \{\{\s*(?P<var>[\w.]+)\s*\}\}
    |
    \{%\s*for\s+(?P<loop_var>\w+)\s+in\s+(?P<loop_src>[\w.]+)\s*%\}
    |
    \{%\s*endfor\s*%\}
    |
    \{%\s*if\s+(?P<if_src>[\w.]+)\s*%\}
    |
    \{%\s*endif\s*%\}
    """,
    re.VERBOSE,
)


def resolve(path, scope):
    parts = path.split(".")
    value = scope
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)
        if value is None:
            return None
    return value


def stringify(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render_template(source, data):
    """Render the mini-template `source` with `data`.

    Auto HTML-escapes `{{var}}` substitutions. Loop variables shadow outer
    scope; resolution falls back to outer scope when a name isn't in the loop.
    Unknown variables render as empty strings (warned via stderr in caller).
    """
    tokens = []
    pos = 0
    for match in TOKEN_PATTERN.finditer(source):
        if match.start() > pos:
            tokens.append(("text", source[pos:match.start()]))
        if match.group("var") is not None:
            tokens.append(("var", match.group("var")))
        elif match.group("loop_var") is not None:
            tokens.append(("for", match.group("loop_var"), match.group("loop_src")))
        elif match.group("if_src") is not None:
            tokens.append(("if", match.group("if_src")))
        elif match.group(0).strip().startswith("{% endfor"):
            tokens.append(("endfor",))
        elif match.group(0).strip().startswith("{% endif"):
            tokens.append(("endif",))
        pos = match.end()
    if pos < len(source):
        tokens.append(("text", source[pos:]))

    def walk(start, scopes, stop_tags):
        out = []
        i = start
        while i < len(tokens):
            token = tokens[i]
            kind = token[0]
            if kind in stop_tags:
                return "".join(out), i
            if kind == "text":
                out.append(token[1])
                i += 1
            elif kind == "var":
                value = None
                for scope in reversed(scopes):
                    value = resolve(token[1], scope)
                    if value is not None:
                        break
                out.append(html_escape(stringify(value)))
                i += 1
            elif kind == "for":
                _, loop_var, loop_src = token
                # locate matching endfor accounting for nesting
                inner_start = i + 1
                inner_end = find_matching(tokens, inner_start, "for", "endfor")
                source_value = None
                for scope in reversed(scopes):
                    source_value = resolve(loop_src, scope)
                    if source_value is not None:
                        break
                if isinstance(source_value, list):
                    for item in source_value:
                        chunk, _ = walk(inner_start, scopes + [{loop_var: item}], {"endfor"})
                        out.append(chunk)
                i = inner_end + 1
            elif kind == "if":
                _, if_src = token
                inner_start = i + 1
                inner_end = find_matching(tokens, inner_start, "if", "endif")
                cond = None
                for scope in reversed(scopes):
                    cond = resolve(if_src, scope)
                    if cond is not None:
                        break
                if truthy(cond):
                    chunk, _ = walk(inner_start, scopes, {"endif"})
                    out.append(chunk)
                i = inner_end + 1
            else:
                # stray endfor/endif outside expected stop set — skip safely
                i += 1
        return "".join(out), i

    rendered, _ = walk(0, [data if isinstance(data, dict) else {}], set())
    return rendered


def find_matching(tokens, start, open_kind, close_kind):
    depth = 1
    i = start
    while i < len(tokens):
        kind = tokens[i][0]
        if kind == open_kind:
            depth += 1
        elif kind == close_kind:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise RuntimeError(f"Unbalanced template: missing {{% {close_kind} %}}")


def truthy(value):
    if value is None or value is False:
        return False
    if isinstance(value, (list, dict, str)):
        return bool(value)
    return bool(value)


# ---------------------------------------------------------------------------
# AI compose call
# ---------------------------------------------------------------------------

def compose_html(template, data):
    payload = {
        "roleId": ROLE_ID,
        "promptId": PROMPT_ID,
        "stream": False,
        "params": {
            "template": template,
            "content": json.dumps(data, ensure_ascii=False),
        },
    }
    req = urllib.request.Request(
        f"{base_url()}{COMPOSE_PATH}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-api-key": api_key(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {COMPOSE_PATH}: {detail}") from exc
    try:
        envelope = json.loads(body)
    except json.JSONDecodeError:
        return body
    return extract_html(envelope)


def extract_html(envelope):
    """Pull the HTML string out of common response shapes."""
    if isinstance(envelope, str):
        return envelope
    if not isinstance(envelope, dict):
        raise RuntimeError(f"Unexpected compose response: {envelope!r}")

    direct_keys = ("content", "html", "text", "result")
    for key in direct_keys:
        value = envelope.get(key)
        if isinstance(value, str) and value.strip():
            return value

    data = envelope.get("data")
    if isinstance(data, str) and data.strip():
        return data
    if isinstance(data, dict):
        for key in direct_keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value

    choices = envelope.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content

    raise RuntimeError(f"Could not find HTML in compose response: {envelope!r}")


# ---------------------------------------------------------------------------
# HTML sanitizing
# ---------------------------------------------------------------------------

UNSAFE_TAG_PATTERN = re.compile(
    r"<\s*(script|iframe|object|embed)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
UNSAFE_SELF_CLOSING = re.compile(
    r"<\s*(script|iframe|object|embed)\b[^>]*/?\s*>",
    re.IGNORECASE,
)
ON_ATTR_PATTERN = re.compile(r"\s+on[a-z]+\s*=\s*(\".*?\"|'.*?'|[^\s>]+)", re.IGNORECASE | re.DOTALL)
JS_HREF_PATTERN = re.compile(r"(href|src|action)\s*=\s*([\"'])\s*javascript:[^\"']*\2", re.IGNORECASE)
LINK_IMPORT_PATTERN = re.compile(r"<\s*link\b[^>]*\brel\s*=\s*[\"']?import[\"']?[^>]*>", re.IGNORECASE)


def sanitize_html(html):
    cleaned = html
    cleaned = UNSAFE_TAG_PATTERN.sub("", cleaned)
    cleaned = UNSAFE_SELF_CLOSING.sub("", cleaned)
    cleaned = ON_ATTR_PATTERN.sub("", cleaned)
    cleaned = JS_HREF_PATTERN.sub(r"\1=\2#\2", cleaned)
    cleaned = LINK_IMPORT_PATTERN.sub("", cleaned)

    cleaned = re.sub(r"^\s*```(?:html)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    return cleaned.strip()


def looks_like_full_document(html):
    lowered = html.lower()
    return "<html" in lowered and "</html>" in lowered


# ---------------------------------------------------------------------------
# Number-fidelity check
# ---------------------------------------------------------------------------

NUMBER_PATTERN = re.compile(r"-?\d+(?:[.,]\d+)*")


def collect_numbers(value):
    found = set()
    if isinstance(value, str):
        for match in NUMBER_PATTERN.findall(value):
            found.add(match.replace(",", ""))
    elif isinstance(value, (int, float)):
        found.add(str(value))
    elif isinstance(value, dict):
        for v in value.values():
            found.update(collect_numbers(v))
    elif isinstance(value, list):
        for v in value:
            found.update(collect_numbers(v))
    return found


def verify_numbers(html, data):
    expected = collect_numbers(data)
    if not expected:
        return []
    haystack = NUMBER_PATTERN.findall(html)
    haystack_norm = {n.replace(",", "") for n in haystack}
    return sorted(n for n in expected if n not in haystack_norm)


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def screenshot(html, output_path, viewport_width=1080):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required. Install with:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        ) from exc

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(
                viewport={"width": viewport_width, "height": 1600},
                device_scale_factor=2,
            )
            page = context.new_page()
            page.set_content(html, wait_until="networkidle")
            page.screenshot(path=str(output_path), full_page=True)
        finally:
            browser.close()
    return output_path


# ---------------------------------------------------------------------------
# Fallback rendering
# ---------------------------------------------------------------------------

FALLBACK_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><style>
body{margin:0;padding:48px 40px;width:1080px;background:#F5F7FB;
font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color:#0F172A;}
.card{background:#fff;border-radius:20px;padding:32px;box-shadow:0 8px 24px rgba(15,23,42,.06);}
h1{font-size:32px;margin:0 0 16px;}
pre{font-size:16px;line-height:1.55;color:#334155;white-space:pre-wrap;word-break:break-word;
font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
.footer{margin-top:24px;font-size:14px;color:#64748B;text-align:center;}
</style></head><body>
<div class="card"><h1>__TITLE__</h1><pre>__BODY__</pre></div>
<div class="footer">Powered by Lingtu · fallback</div>
</body></html>"""


def fallback_html(data, reason):
    title = "报告生成兜底视图"
    if isinstance(data, dict):
        for key in ("title", "subject", "name"):
            if isinstance(data.get(key), str) and data[key]:
                title = data[key]
                break
    body = json.dumps(data, ensure_ascii=False, indent=2)
    body = f"[{reason}]\n\n{body}"
    return (
        FALLBACK_HTML
        .replace("__TITLE__", html_escape(title))
        .replace("__BODY__", html_escape(body))
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def default_output_path(template_id):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"{template_id}-{stamp}.png"


def render(template_id, data, output_path, mode="fill", strict_numbers=False, debug_html=None):
    template = load_template(template_id, mode)
    enriched = apply_defaults(template_id, data)

    html = None
    fallback_reason = None

    if mode == "fill":
        try:
            html = render_template(template, enriched)
        except Exception as exc:
            fallback_reason = f"fill render failed: {exc}"
    else:
        try:
            html = compose_html(template, enriched)
        except Exception as exc:
            fallback_reason = f"compose failed: {exc}"

    if html:
        html = sanitize_html(html)
        if not looks_like_full_document(html):
            fallback_reason = fallback_reason or "rendered HTML is not a full document"
            html = None

    if html and isinstance(enriched, dict):
        missing = verify_numbers(html, enriched)
        if missing:
            msg = f"missing numbers in HTML: {missing}"
            if strict_numbers:
                fallback_reason = msg
                html = None
            else:
                print(f"warn: {msg}", file=sys.stderr)

    if html is None:
        html = fallback_html(enriched, fallback_reason or "unknown")

    if debug_html:
        Path(debug_html).write_text(html, encoding="utf-8")

    output = screenshot(html, output_path)
    return output, fallback_reason


def main():
    parser = argparse.ArgumentParser(description="Render a Lingtu report to PNG.")
    parser.add_argument("--template", required=True, help="Template id, e.g. daily_report.")
    parser.add_argument(
        "--data",
        required=True,
        help="Path to JSON file, '-' for stdin, or inline JSON.",
    )
    parser.add_argument(
        "--mode",
        choices=("fill", "ai"),
        default=os.environ.get("LINGTU_REPORT_MODE", "fill"),
        help="fill: stdlib placeholder template (default). ai: call /v1/ai/chat/complete.",
    )
    parser.add_argument("--out", help="Output PNG path. Default: output/<template>-<timestamp>.png")
    parser.add_argument(
        "--strict-numbers",
        action="store_true",
        help="Fall back if any numeric value from data is missing from HTML.",
    )
    parser.add_argument("--debug-html", help="Write the final HTML to this path before screenshotting.")

    args = parser.parse_args()
    data = load_data(args.data)
    out = Path(args.out) if args.out else default_output_path(args.template)

    started = time.time()
    output, reason = render(
        args.template,
        data,
        out,
        mode=args.mode,
        strict_numbers=args.strict_numbers,
        debug_html=args.debug_html,
    )
    elapsed = time.time() - started

    summary = {
        "success": True,
        "image": str(output),
        "mode": args.mode,
        "fallback": reason,
        "elapsed_seconds": round(elapsed, 2),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
