#!/usr/bin/env python3
"""Shared JSON HTTP helpers for Lingtu skills."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from lingtu_auth import require_api_key

DEFAULT_BASE_URL = "https://api.ailingtu.com"
DEFAULT_TIMEOUT = 60


class LingtuHttpError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        url: str = "",
        body: str = "",
        reason: str = "",
    ) -> None:
        super().__init__(message)
        self.status = status
        self.url = url
        self.body = body
        self.reason = reason


def base_url(default: str = DEFAULT_BASE_URL) -> str:
    return os.environ.get("LINGTU_AI_BASE_URL", default).rstrip("/")


def build_url(base: str, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return urllib.parse.urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def auth_headers(
    api_key: str | None = None,
    *,
    accept: str = "application/json",
    content_type: str | None = None,
) -> dict[str, str]:
    headers = {
        "Accept": accept,
        "x-api-key": api_key if api_key is not None else require_api_key(),
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def request_bytes(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.getcode() or 200, response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LingtuHttpError(
            f"HTTP {exc.code} from {url}: {body}",
            status=exc.code,
            url=url,
            body=body,
            reason=str(exc.reason),
        ) from exc
    except urllib.error.URLError as exc:
        raise LingtuHttpError(
            f"Request failed for {url}: {exc.reason}",
            url=url,
            reason=str(exc.reason),
        ) from exc


def request_json(
    method: str,
    path_or_url: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    api_key: str | None = None,
    base: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    expect_envelope: bool = False,
    return_data: bool = False,
) -> Any:
    """JSON API call.

    - Relative paths join with ``base`` or ``base_url()``.
    - Absolute http(s) URLs are used as-is.
    - ``expect_envelope=True`` requires ``code == 0``.
    - ``return_data=True`` returns ``result["data"]`` when envelope succeeds.
    """
    url = path_or_url if path_or_url.startswith(("http://", "https://")) else build_url(base or base_url(), path_or_url)
    if query:
        url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"

    data = None
    headers = auth_headers(api_key)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    _, raw_bytes = request_bytes(method, url, headers=headers, data=data, timeout=timeout)
    raw = raw_bytes.decode("utf-8")
    if not raw:
        if expect_envelope:
            raise LingtuHttpError(f"Empty response from {url}", url=url)
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        if expect_envelope:
            raise LingtuHttpError(f"Expected JSON from {url}, got: {raw[:500]}", url=url, body=raw) from exc
        return raw

    if expect_envelope:
        if not isinstance(parsed, dict):
            raise LingtuHttpError(
                f"Expected JSON object from {url}, got: {type(parsed).__name__}",
                url=url,
                body=raw,
            )
        code = parsed.get("code")
        if code != 0:
            message = parsed.get("message") or "未知错误"
            raise LingtuHttpError(
                f"{path_or_url} 调用失败 (code={code})：{message}",
                url=url,
                body=raw,
            )
        if return_data:
            data_field = parsed.get("data")
            if not isinstance(data_field, dict):
                raise LingtuHttpError(
                    f"{path_or_url} 调用失败：缺少 data 对象",
                    url=url,
                    body=raw,
                )
            return data_field
        return parsed

    return parsed


def raise_system_exit(exc: LingtuHttpError, label: str | None = None) -> None:
    """Convert LingtuHttpError into SystemExit for CLI packages."""
    if label and exc.status is not None:
        raise SystemExit(f"{label} HTTP 错误：{exc.status} {exc.reason or exc}") from exc
    if label and exc.reason and exc.status is None:
        raise SystemExit(f"{label} 网络错误：{exc.reason}") from exc
    if label:
        raise SystemExit(f"{label}：{exc}") from exc
    raise SystemExit(str(exc)) from exc
