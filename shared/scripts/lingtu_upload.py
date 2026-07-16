#!/usr/bin/env python3
"""Shared file upload helpers for Lingtu skills.

Supports:
- multipart POST /v1/file/upload (images / general files)
- streaming multipart upload (large videos)
- presign → PUT → confirm (video-publish)
"""

from __future__ import annotations

import hashlib
import http.client
import json
import mimetypes
import os
import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lingtu_auth import require_api_key
from lingtu_http import (
    DEFAULT_TIMEOUT,
    LingtuHttpError,
    base_url,
    build_url,
    raise_system_exit,
    request_json,
)

UPLOAD_PATH = "/v1/file/upload"
FILE_PRESIGN_PATH = "/v1/file/presign"
FILE_CONFIRM_PATH = "/v1/file/confirm"
UPLOAD_TIMEOUT = 600
UPLOAD_CHUNK_SIZE = 64 * 1024
PROGRESS_MIN_BYTES = 1024 * 1024


def guess_content_type(filename: str, fallback: str = "application/octet-stream") -> str:
    return mimetypes.guess_type(filename)[0] or fallback


def compute_content_hash(file_path: str | Path) -> str:
    """Java-compatible hash: sha256(raw_bytes.hex().encode())."""
    raw = Path(file_path).read_bytes()
    return hashlib.sha256(raw.hex().encode("utf-8")).hexdigest()


def build_multipart_file_body(
    file_path: str | Path,
    *,
    field_name: str = "file",
) -> tuple[bytes, str]:
    path = Path(file_path)
    filename = path.name
    content_type = guess_content_type(filename)
    boundary = f"----LingtuFormBoundary{uuid.uuid4().hex}"
    file_bytes = path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


def _format_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def _default_progress(sent: int, total: int) -> None:
    pct = (sent / total * 100) if total else 0
    sys.stderr.write(f"\rUploading: {_format_bytes(sent)} / {_format_bytes(total)} ({pct:5.1f}%)")
    sys.stderr.flush()


def put_file(
    url: str,
    data: bytes,
    content_type: str,
    *,
    timeout: float = UPLOAD_TIMEOUT,
) -> None:
    """HTTP PUT to a presigned URL (no x-api-key)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise LingtuHttpError(f"Unsupported upload URL scheme: {parsed.scheme}", url=url)
    conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(parsed.hostname or "", timeout=timeout)
    try:
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        conn.request("PUT", path, body=data, headers={"Content-Type": content_type})
        resp = conn.getresponse()
        resp.read()
        if resp.status >= 400:
            raise LingtuHttpError(
                f"文件上传失败：HTTP {resp.status} {resp.reason}",
                status=resp.status,
                url=url,
                reason=str(resp.reason),
            )
    except http.client.HTTPException as exc:
        raise LingtuHttpError(f"文件上传网络错误：{exc}", url=url, reason=str(exc)) from exc
    finally:
        conn.close()


def _parse_upload_payload(
    payload: Any,
    *,
    allow_null_code: bool,
    require_id: bool,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LingtuHttpError(f"Upload returned non-object JSON: {payload!r}")
    code = payload.get("code")
    ok = code in (0, None) if allow_null_code else code == 0
    if not ok:
        raise LingtuHttpError(f"Upload failed: {json.dumps(payload, ensure_ascii=False)}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise LingtuHttpError(f"Upload response missing data: {json.dumps(payload, ensure_ascii=False)}")
    url = data.get("url")
    file_id = data.get("id")
    if require_id and file_id is None:
        raise LingtuHttpError(f"Upload response missing data.id: {json.dumps(payload, ensure_ascii=False)}")
    if not require_id and (not isinstance(url, str) or not url):
        raise LingtuHttpError(f"Upload response missing data.url: {json.dumps(payload, ensure_ascii=False)}")
    return {"id": file_id, "url": url, "isNew": data.get("isNew")}


def multipart_upload(
    file_path: str | Path,
    *,
    base: str | None = None,
    api_key: str | None = None,
    timeout: float = UPLOAD_TIMEOUT,
    stream: bool = False,
    progress: bool | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    allow_null_code: bool = False,
    require_id: bool = True,
    as_system_exit: bool = False,
) -> dict[str, Any]:
    """POST /v1/file/upload and return {id, url, isNew}."""
    path = Path(file_path)
    try:
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        key = api_key if api_key is not None else require_api_key()
        root = (base or base_url()).rstrip("/")
        upload_url = build_url(root, UPLOAD_PATH)

        if not stream:
            body, content_type = build_multipart_file_body(path)
            from lingtu_http import auth_headers, request_bytes

            _, raw = request_bytes(
                "POST",
                upload_url,
                headers=auth_headers(key, content_type=content_type),
                data=body,
                timeout=timeout,
            )
            payload = json.loads(raw.decode("utf-8"))
            return _parse_upload_payload(payload, allow_null_code=allow_null_code, require_id=require_id)

        filename = path.name
        content_type = guess_content_type(filename)
        boundary = f"----LingtuFormBoundary{uuid.uuid4().hex}"
        file_size = path.stat().st_size
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        trailer = f"\r\n--{boundary}--\r\n".encode("utf-8")
        total_size = len(header) + file_size + len(trailer)
        show_progress = progress if progress is not None else (file_size >= PROGRESS_MIN_BYTES and sys.stderr.isatty())
        progress_cb = on_progress or (_default_progress if show_progress else None)

        parsed = urlparse(root)
        if parsed.scheme not in ("http", "https"):
            raise LingtuHttpError(f"Unsupported base URL scheme: {parsed.scheme}", url=root)
        conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        conn = conn_cls(host, port, timeout=timeout)
        try:
            conn.putrequest("POST", UPLOAD_PATH)
            conn.putheader("x-api-key", key)
            conn.putheader("Accept", "application/json")
            conn.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
            conn.putheader("Content-Length", str(total_size))
            conn.endheaders()

            sent = 0
            conn.send(header)
            sent += len(header)
            if progress_cb:
                progress_cb(sent, total_size)

            with path.open("rb") as fh:
                while True:
                    chunk = fh.read(UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    conn.send(chunk)
                    sent += len(chunk)
                    if progress_cb:
                        progress_cb(sent, total_size)

            conn.send(trailer)
            sent += len(trailer)
            if progress_cb:
                progress_cb(sent, total_size)
                if on_progress is None and show_progress:
                    sys.stderr.write("\n")
                    sys.stderr.flush()

            resp = conn.getresponse()
            body_text = resp.read().decode("utf-8", errors="replace")
            if resp.status >= 400:
                raise LingtuHttpError(
                    f"HTTP {resp.status} from {upload_url}: {body_text}",
                    status=resp.status,
                    url=upload_url,
                    body=body_text,
                    reason=str(resp.reason),
                )
        finally:
            conn.close()

        payload = json.loads(body_text)
        return _parse_upload_payload(payload, allow_null_code=allow_null_code, require_id=require_id)
    except (LingtuHttpError, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        if as_system_exit:
            if isinstance(exc, LingtuHttpError):
                raise_system_exit(exc)
            raise SystemExit(str(exc)) from exc
        if isinstance(exc, json.JSONDecodeError):
            raise LingtuHttpError(f"Upload returned non-JSON body: {exc}") from exc
        raise


def presign_upload(
    file_path: str | Path,
    *,
    base: str | None = None,
    api_key: str | None = None,
    timeout: float = UPLOAD_TIMEOUT,
    confirm_timeout: float = DEFAULT_TIMEOUT,
    as_system_exit: bool = True,
) -> dict[str, Any]:
    """Presign → optional PUT → confirm. Returns {id, url}."""
    path = Path(file_path).expanduser()
    try:
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在：{path}")
        if not path.is_file():
            raise FileNotFoundError(f"路径不是文件：{path}")

        key = api_key if api_key is not None else require_api_key()
        root = base or base_url()
        content_type = guess_content_type(path.name, fallback="video/mp4")
        file_hash = compute_content_hash(path)

        result = request_json(
            "POST",
            FILE_PRESIGN_PATH,
            body={
                "fileName": path.name,
                "contentType": content_type,
                "size": path.stat().st_size,
                "hash": file_hash,
            },
            api_key=key,
            base=root,
            timeout=timeout,
            expect_envelope=True,
        )
        data = result.get("data") or {}
        file_id = data.get("fileId") or data.get("id") or ""
        upload_url = data.get("uploadUrl") or ""
        raw_is_new = data.get("isNew")
        is_new = raw_is_new is True or raw_is_new == "true" or raw_is_new == "1" or raw_is_new == 1
        final_url = data.get("url") or ""

        should_upload = is_new or (raw_is_new is None and bool(upload_url))
        if should_upload and upload_url:
            put_file(upload_url, path.read_bytes(), content_type, timeout=timeout)
            request_json(
                "POST",
                FILE_CONFIRM_PATH,
                body={"fileId": file_id},
                api_key=key,
                base=root,
                timeout=confirm_timeout,
                expect_envelope=True,
            )

        return {"id": str(file_id), "url": final_url}
    except (LingtuHttpError, FileNotFoundError, OSError) as exc:
        if as_system_exit:
            if isinstance(exc, LingtuHttpError):
                raise_system_exit(exc)
            raise SystemExit(str(exc)) from exc
        raise
