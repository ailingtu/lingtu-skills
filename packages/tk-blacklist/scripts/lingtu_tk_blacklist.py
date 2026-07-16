#!/usr/bin/env python3
"""Query Lingtu TK blacklist records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any
from urllib.parse import urlparse
from pathlib import Path


def _shared_scripts_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "shared" / "scripts"
        if candidate.is_dir():
            return candidate
    raise RuntimeError("未找到 shared/scripts 目录。请确认 skill 安装完整。")


sys.path.insert(0, str(_shared_scripts_dir()))

from lingtu_auth import require_api_key as shared_require_api_key
from lingtu_http import LingtuHttpError, base_url as shared_base_url, request_json as shared_request_json


DEFAULT_BASE_URL = "https://api.ailingtu.com"
SEARCH_PATH = "/web/influencerBlack/search"


def require_api_key() -> str:
    return shared_require_api_key()


def base_url() -> str:
    return shared_base_url(DEFAULT_BASE_URL)


def parse_unique_id(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise SystemExit("uniqueId cannot be empty.")

    if "tiktok.com" in value:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        match = re.search(r"/@([^/?#]+)", parsed.path)
        if match:
            return normalize_unique_id(match.group(1))

    mention = re.search(r"@([A-Za-z0-9._-]+)", value)
    if mention:
        return normalize_unique_id(mention.group(1))

    return normalize_unique_id(value)


def normalize_unique_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "", value.strip()).strip("._-")
    if not normalized:
        raise SystemExit(f"Invalid uniqueId: {value!r}")
    return normalized


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def request_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = shared_request_json("POST", path, body=payload, timeout=60)
    except LingtuHttpError as exc:
        raise SystemExit(str(exc)) from exc
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise SystemExit(f"Invalid JSON from {base_url()}{path}: {parsed}")
    return parsed


def search_blacklist(unique_ids: list[str]) -> dict[str, Any]:
    payload = {"uniqueIds": unique_ids}
    response = request_json(SEARCH_PATH, payload)
    code = response.get("code")
    if code != 0:
        message = response.get("message") or "unknown error"
        raise SystemExit(f"Blacklist search failed: code={code}, message={message}, response={json.dumps(response, ensure_ascii=False)}")
    return {
        "query": {
            "uniqueIds": unique_ids,
        },
        "response": response,
        "records": extract_records(response),
        "missing": missing_ids(unique_ids, extract_records(response)),
    }


def extract_records(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response.get("data")
    if not isinstance(data, dict):
        return []
    records = data.get("list")
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def missing_ids(unique_ids: list[str], records: list[dict[str, Any]]) -> list[str]:
    returned = {
        str(record.get("uniqueId", "")).lower()
        for record in records
        if record.get("uniqueId") not in (None, "")
    }
    return [unique_id for unique_id in unique_ids if unique_id.lower() not in returned]


def print_text(result: dict[str, Any]) -> None:
    records = result["records"]
    missing = result["missing"]
    if not records and not missing:
        print("No blacklist records returned.")
        return

    for record in records:
        unique_id = record.get("uniqueId") or "-"
        count = record.get("count")
        nickname = record.get("nickname") or "-"
        region = record.get("region") or "-"
        feedback_at = record.get("feedbackAt") or "-"
        reason = record.get("feedbackReason") or "-"
        print(f"{unique_id}: FOUND count={count}, nickname={nickname}, region={region}, feedbackAt={feedback_at}, reason={reason}")

    for unique_id in missing:
        print(f"{unique_id}: NOT_FOUND")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query Lingtu TK blacklist.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search blacklist records by TikTok uniqueId.")
    search_parser.add_argument("unique_ids", nargs="+", help="One or more TikTok unique IDs, @handles, or TikTok URLs.")
    search_parser.add_argument("--format", choices=("json", "text"), default="json", help="Output format.")

    args = parser.parse_args()

    if args.command == "search":
        unique_ids = dedupe([parse_unique_id(value) for value in args.unique_ids])
        result = search_blacklist(unique_ids)
        if args.format == "text":
            print_text(result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
