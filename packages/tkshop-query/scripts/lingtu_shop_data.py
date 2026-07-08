#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

from lingtu_auth import require_api_key


DEFAULT_BASE_URL = "https://api.ailingtu.com"


def api_key():
    return require_api_key()


def base_url():
    return os.environ.get("LINGTU_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def request_json(method, path, payload=None):
    url = f"{base_url()}{path}"
    data = None
    headers = {
        "x-api-key": api_key(),
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def extract_list(value):
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return []
    for key in ("data", "result"):
        nested = value.get(key)
        if isinstance(nested, list):
            return nested
        if isinstance(nested, dict):
            for list_key in ("list", "records", "items", "shops"):
                if isinstance(nested.get(list_key), list):
                    return nested[list_key]
    for list_key in ("list", "records", "items", "shops"):
        if isinstance(value.get(list_key), list):
            return value[list_key]
    return []


def shop_id(shop):
    for key in ("id", "shopId", "targetId"):
        if key in shop and shop[key] not in (None, ""):
            return str(shop[key])
    return None


def shop_name(shop):
    for key in ("name", "shopName", "title"):
        if key in shop and shop[key]:
            return str(shop[key])
    return ""


def list_shops():
    data = request_json("GET", "/v1/shop/list")
    shops = extract_list(data)
    return data, shops


def resolve_shop(shop_id_arg=None, shop_name_arg=None):
    if shop_id_arg:
        return str(shop_id_arg), None, None

    raw, shops = list_shops()
    if not shops:
        raise SystemExit(
            "No shops found in /v1/shop/list response. "
            "请先打开 https://app.ailingtu.com/teamshop 绑定 TikTok Shop 店铺后再重试。\n"
            f"Raw response: {json.dumps(raw, ensure_ascii=False)}"
        )

    if not shop_name_arg:
        first = shops[0]
        resolved_id = shop_id(first)
        if not resolved_id:
            raise SystemExit(f"First shop has no id field: {json.dumps(first, ensure_ascii=False)}")
        return resolved_id, shop_name(first), first

    exact = [shop for shop in shops if shop_name(shop) == shop_name_arg]
    matches = exact or [shop for shop in shops if shop_name_arg in shop_name(shop)]
    if not matches:
        available = [shop_name(shop) for shop in shops if shop_name(shop)]
        raise SystemExit(f"No shop matched {shop_name_arg!r}. Available shops: {json.dumps(available, ensure_ascii=False)}")
    if len(matches) > 1 and not exact:
        names = [shop_name(shop) for shop in matches]
        raise SystemExit(f"Multiple shops matched {shop_name_arg!r}: {json.dumps(names, ensure_ascii=False)}")
    resolved = matches[0]
    resolved_id = shop_id(resolved)
    if not resolved_id:
        raise SystemExit(f"Matched shop has no id field: {json.dumps(resolved, ensure_ascii=False)}")
    return resolved_id, shop_name(resolved), resolved


def daily_report(args):
    resolved_id, resolved_name, resolved_shop = resolve_shop(args.shop_id, args.shop_name)
    query = urllib.parse.urlencode({
        "targetType": "SHOP",
        "targetId": resolved_id,
        "reportDate": args.date,
    })
    report = request_json("GET", f"/v1/report/biz/detail?{query}")
    result = {
        "shop": {
            "id": resolved_id,
            "name": resolved_name,
            "source": resolved_shop,
        },
        "reportDate": args.date,
        "report": report,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def summary_is_empty(report):
    if report in (None, "", [], {}):
        return True
    if isinstance(report, dict):
        data = report.get("data")
        if data in (None, "", [], {}):
            return True
    return False


def summary_report(args):
    query = urllib.parse.urlencode({"reportDate": args.date})
    report = request_json("GET", f"/v1/report/biz/summary?{query}")
    if not summary_is_empty(report):
        result = {
            "reportDate": args.date,
            "summary": report,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    resolved_id, resolved_name, resolved_shop = resolve_shop(None, None)
    fallback_query = urllib.parse.urlencode({
        "targetType": "SHOP",
        "targetId": resolved_id,
        "reportDate": args.date,
    })
    fallback = request_json("GET", f"/v1/report/biz/detail?{fallback_query}")
    result = {
        "reportDate": args.date,
        "summary": report,
        "fallback": {
            "reason": "summary empty, returned first shop daily report",
            "shop": {
                "id": resolved_id,
                "name": resolved_name,
                "source": resolved_shop,
            },
            "report": fallback,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def emit_stream_text(raw):
    text = raw.strip()
    if not text:
        return
    if text == "[DONE]":
        return
    if text.startswith("data:"):
        text = text[5:].strip()
    if not text or text == "[DONE]":
        return
    try:
        event = json.loads(text)
    except json.JSONDecodeError:
        print(text, end="", flush=True)
        return

    candidates = []
    if isinstance(event, dict):
        candidates.extend([
            event.get("content"),
            event.get("text"),
            event.get("message"),
        ])
        delta = event.get("delta")
        if isinstance(delta, dict):
            candidates.append(delta.get("content"))
        choices = event.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                if isinstance(choice, dict):
                    choice_delta = choice.get("delta")
                    if isinstance(choice_delta, dict):
                        candidates.append(choice_delta.get("content"))
                    candidates.append(choice.get("text"))
    for item in candidates:
        if isinstance(item, str) and item:
            print(item, end="", flush=True)
            return


def ask(args):
    payload = {
        "message": args.question,
        "prompt": args.question,
        "content": args.question,
        "stream": True,
    }
    url = f"{base_url()}/v1/ai/chat/create"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-api-key": api_key(),
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                emit_stream_text(raw_line.decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
    print()


def main():
    parser = argparse.ArgumentParser(description="Query Lingtu shop data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-shops", help="Fetch the live shop list.")

    report_parser = subparsers.add_parser("daily-report", help="Fetch a shop daily report.")
    report_parser.add_argument("--date", required=True, help="Report date in YYYY-MM-DD format.")
    report_parser.add_argument("--shop-id", help="Numeric shop id. Skips shop-list lookup.")
    report_parser.add_argument("--shop-name", help="Shop name to resolve through /v1/shop/list.")

    summary_parser = subparsers.add_parser(
        "summary-report",
        help="Fetch the all-shops summary report. Falls back to the first shop's daily report when the summary is empty.",
    )
    summary_parser.add_argument("--date", required=True, help="Report date in YYYY-MM-DD format.")

    ask_parser = subparsers.add_parser("ask", help="Ask an AI shop operations question.")
    ask_parser.add_argument("question", help="Question to send to /v1/ai/chat/create.")

    args = parser.parse_args()
    if args.command == "list-shops":
        data, _shops = list_shops()
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif args.command == "daily-report":
        daily_report(args)
    elif args.command == "summary-report":
        summary_report(args)
    elif args.command == "ask":
        ask(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
