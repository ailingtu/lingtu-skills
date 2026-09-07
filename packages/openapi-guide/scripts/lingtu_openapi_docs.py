#!/usr/bin/env python3
"""Read LINGTU AI's public OpenAPI documentation without credentials."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


DEFAULT_DOCS_URL = "https://ailingtu.com"
USER_AGENT = "lingtu-openapi-guide/0.1"


class DocumentationError(RuntimeError):
    """Raised when a public documentation resource cannot be read."""


def fetch(base_url: str, path: str, *, timeout: float) -> bytes:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"Accept": "*/*", "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        raise DocumentationError(f"documentation request failed: HTTP {exc.code} {url}") from exc
    except URLError as exc:
        raise DocumentationError(f"documentation request failed: {exc.reason} ({url})") from exc


def fetch_json(base_url: str, path: str, *, timeout: float) -> dict[str, Any]:
    payload = fetch(base_url, path, timeout=timeout)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DocumentationError(f"documentation returned invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DocumentationError(f"documentation returned an unexpected JSON value: {path}")
    return value


def operation_index(base_url: str, *, timeout: float) -> dict[str, Any]:
    return fetch_json(base_url, "/openapi/operations/index.json", timeout=timeout)


def matches(operation: dict[str, Any], query: str, tag: str | None) -> bool:
    tags = [str(value) for value in operation.get("tags", [])]
    if tag and tag.casefold() not in {value.casefold() for value in tags}:
        return False
    if not query:
        return True
    haystack = " ".join(
        [
            str(operation.get("operationId", "")),
            str(operation.get("method", "")),
            str(operation.get("path", "")),
            str(operation.get("summary", "")),
            *tags,
        ]
    ).casefold()
    return all(term in haystack for term in query.casefold().split())


def print_operations(document: dict[str, Any], query: str = "", tag: str | None = None) -> int:
    operations = document.get("operations", [])
    if not isinstance(operations, list):
        raise DocumentationError("operation index has no operations array")
    selected = [op for op in operations if isinstance(op, dict) and matches(op, query, tag)]
    print(
        f"LINGTU AI OpenAPI {document.get('version', '?')} "
        f"(updated {document.get('lastUpdated', '?')})"
    )
    for operation in selected:
        print(
            f"{operation.get('method', '?'):6} {operation.get('path', '?')}\n"
            f"       {operation.get('operationId', '?')} — {operation.get('summary', '')}"
        )
    if not selected:
        print("No matching operation found.", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search and read LINGTU AI's public OpenAPI documentation. No API key is sent."
    )
    parser.add_argument("--base-url", default=DEFAULT_DOCS_URL, help="Public documentation origin")
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List published operations")
    list_parser.add_argument("--tag", help="Require an exact tag, case-insensitively")

    search_parser = subparsers.add_parser("search", help="Search operations")
    search_parser.add_argument("query", help="Space-separated terms that must all match")
    search_parser.add_argument("--tag", help="Require an exact tag, case-insensitively")

    get_parser = subparsers.add_parser("get", help="Read one focused operation document")
    get_parser.add_argument("operation_id")
    get_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")

    workflow_parser = subparsers.add_parser("workflow", help="Read a published workflow")
    workflow_parser.add_argument("workflow_id", choices=("ai-generation",))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in {"list", "search"}:
            document = operation_index(args.base_url, timeout=args.timeout)
            query = args.query if args.command == "search" else ""
            return print_operations(document, query=query, tag=args.tag)

        if args.command == "get":
            suffix = "json" if args.format == "json" else "md"
            operation_id = quote(args.operation_id, safe="")
            payload = fetch(
                args.base_url,
                f"/openapi/operations/{operation_id}.{suffix}",
                timeout=args.timeout,
            )
            if args.format == "json":
                document = json.loads(payload)
                print(json.dumps(document, ensure_ascii=False, indent=2))
            else:
                print(payload.decode("utf-8"))
            return 0

        payload = fetch(
            args.base_url,
            f"/openapi/workflows/{quote(args.workflow_id, safe='')}.md",
            timeout=args.timeout,
        )
        print(payload.decode("utf-8"))
        return 0
    except (DocumentationError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
