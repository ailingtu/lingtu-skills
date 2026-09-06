#!/usr/bin/env python3
"""Minimal runtime used when video-understand is installed by itself."""

from __future__ import annotations

import http.client
import json
import mimetypes
import os
import platform
import sys
import urllib.parse
import uuid
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://api.ailingtu.com"
UPLOAD_CHUNK_SIZE = 64 * 1024
UPLOAD_TIMEOUT = 600


def api_key_setup_instructions() -> str:
    if platform.system() == "Windows":
        return (
            'Set it in PowerShell with `$env:LINGTU_API_KEY = "your-api-key"` for the current session, '
            'or `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")` '
            "and then open a new terminal."
        )
    return (
        "Set it in Terminal with `export LINGTU_API_KEY='your-api-key'`. "
        "To keep it across sessions on macOS, add that line to `~/.zshrc` and run `source ~/.zshrc`."
    )


def require_api_key() -> str:
    key = os.environ.get("LINGTU_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "LINGTU_API_KEY environment variable is not set. "
            f"{api_key_setup_instructions()}"
        )
    return key


def base_url(default: str = DEFAULT_BASE_URL) -> str:
    return os.environ.get("LINGTU_AI_BASE_URL", default).rstrip("/")


def _parse_upload_payload(payload: Any, require_id: bool) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("code") != 0:
        raise RuntimeError(f"Upload failed: {json.dumps(payload, ensure_ascii=False)}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"Upload response missing data: {json.dumps(payload, ensure_ascii=False)}")
    if require_id and data.get("id") is None:
        raise RuntimeError(f"Upload response missing data.id: {json.dumps(payload, ensure_ascii=False)}")
    return {"id": data.get("id"), "url": data.get("url"), "isNew": data.get("isNew")}


def multipart_upload(
    file_path: str | Path,
    *,
    base: str | None = None,
    api_key: str | None = None,
    timeout: float = UPLOAD_TIMEOUT,
    stream: bool = False,
    progress: bool | None = None,
    require_id: bool = True,
    as_system_exit: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """Upload one file to /v1/file/upload without external dependencies."""
    path = Path(file_path)
    try:
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        root = (base or base_url()).rstrip("/")
        parsed = urllib.parse.urlparse(root)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise RuntimeError(f"Unsupported base URL: {root}")

        key = api_key if api_key is not None else require_api_key()
        boundary = f"----LingtuFormBoundary{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        trailer = f"\r\n--{boundary}--\r\n".encode("utf-8")
        total_size = len(header) + path.stat().st_size + len(trailer)
        request_path = f"{parsed.path.rstrip('/')}/v1/file/upload"
        connection_type = (
            http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        )
        connection = connection_type(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            timeout=timeout,
        )
        show_progress = bool(progress and sys.stderr.isatty())

        try:
            connection.putrequest("POST", request_path)
            connection.putheader("x-api-key", key)
            connection.putheader("Accept", "application/json")
            connection.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
            connection.putheader("Content-Length", str(total_size))
            connection.endheaders()

            sent = 0
            connection.send(header)
            sent += len(header)
            with path.open("rb") as file_handle:
                while True:
                    chunk = file_handle.read(UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    connection.send(chunk)
                    sent += len(chunk)
                    if show_progress:
                        percent = sent / total_size * 100
                        sys.stderr.write(f"\rUploading: {percent:5.1f}%")
                        sys.stderr.flush()
            connection.send(trailer)
            if show_progress:
                sys.stderr.write("\rUploading: 100.0%\n")
                sys.stderr.flush()

            response = connection.getresponse()
            response_text = response.read().decode("utf-8", errors="replace")
            if response.status >= 400:
                raise RuntimeError(
                    f"HTTP {response.status} from {root}/v1/file/upload: {response_text}"
                )
        finally:
            connection.close()

        return _parse_upload_payload(json.loads(response_text), require_id)
    except (OSError, ValueError, RuntimeError, http.client.HTTPException) as exc:
        if as_system_exit:
            raise SystemExit(str(exc)) from exc
        raise
