#!/usr/bin/env python3
"""Shared file upload helpers for Lingtu skills.

Upload flow: presign → PUT to the returned object-storage URL → confirm.
File bytes never pass through the API gateway, so the gateway body timeout
does not apply, and the backend reuses the file when the same content hash
was uploaded before.
"""

from __future__ import annotations

import hashlib
import http.client
import mimetypes
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lingtu_auth import require_api_key
from lingtu_http import (
    DEFAULT_TIMEOUT,
    LingtuHttpError,
    base_url,
    raise_system_exit,
    request_json,
)

FILE_PRESIGN_PATH = "/v1/file/presign"
FILE_CONFIRM_PATH = "/v1/file/confirm"
UPLOAD_TIMEOUT = 600
UPLOAD_CHUNK_SIZE = 64 * 1024
PROGRESS_MIN_BYTES = 1024 * 1024


def guess_content_type(filename: str, fallback: str = "application/octet-stream") -> str:
    return mimetypes.guess_type(filename)[0] or fallback


def compute_content_hash(file_path: str | Path) -> str:
    """Java-compatible hash: sha256(raw_bytes.hex().encode())."""
    digest = hashlib.sha256()
    with Path(file_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(UPLOAD_CHUNK_SIZE), b""):
            digest.update(chunk.hex().encode("utf-8"))
    return digest.hexdigest()


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
    data: bytes | Path,
    content_type: str,
    *,
    timeout: float = UPLOAD_TIMEOUT,
    progress: bool | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """HTTP PUT to a presigned URL (no x-api-key).

    `data` is raw bytes or a local file path. A path is read and sent in chunks,
    so large videos never have to fit in memory.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise LingtuHttpError(f"Unsupported upload URL scheme: {parsed.scheme}", url=url)
    total = data.stat().st_size if isinstance(data, Path) else len(data)
    if on_progress is not None:
        notify: Callable[[int, int], None] | None = on_progress
    else:
        show = progress if progress is not None else (total >= PROGRESS_MIN_BYTES and sys.stderr.isatty())
        notify = _default_progress if show else None

    conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(parsed.hostname or "", parsed.port or (443 if parsed.scheme == "https" else 80), timeout=timeout)
    try:
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        if isinstance(data, Path) or notify is not None:
            conn.putrequest("PUT", path)
            conn.putheader("Content-Type", content_type)
            conn.putheader("Content-Length", str(total))
            conn.endheaders()
            sent = 0
            if isinstance(data, Path):
                with data.open("rb") as handle:
                    while True:
                        chunk = handle.read(UPLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        conn.send(chunk)
                        sent += len(chunk)
                        if notify is not None:
                            notify(sent, total)
            else:
                for start in range(0, total, UPLOAD_CHUNK_SIZE):
                    chunk = data[start:start + UPLOAD_CHUNK_SIZE]
                    conn.send(chunk)
                    sent += len(chunk)
                    if notify is not None:
                        notify(sent, total)
            if notify is not None and on_progress is None:
                sys.stderr.write("\n")
                sys.stderr.flush()
        else:
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
    except (http.client.HTTPException, OSError) as exc:
        raise LingtuHttpError(f"文件上传网络错误：{exc}", url=url, reason=str(exc)) from exc
    finally:
        conn.close()


def presign_upload(
    file_path: str | Path,
    *,
    base: str | None = None,
    api_key: str | None = None,
    timeout: float = UPLOAD_TIMEOUT,
    confirm_timeout: float = DEFAULT_TIMEOUT,
    presign_path: str | None = None,
    confirm_path: str | None = None,
    default_content_type: str = "video/mp4",
    progress: bool | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    as_system_exit: bool = True,
) -> dict[str, Any]:
    """Presign → optional PUT → confirm. Returns {id, url}."""
    path = Path(file_path).expanduser()
    try:
        if not path.exists():
            raise FileNotFoundError(f"文件不存在：{path}")
        if not path.is_file():
            raise FileNotFoundError(f"路径不是文件：{path}")

        key = api_key if api_key is not None else require_api_key()
        root = base or base_url()
        content_type = guess_content_type(path.name, fallback=default_content_type)
        file_hash = compute_content_hash(path)

        result = request_json(
            "POST",
            presign_path or FILE_PRESIGN_PATH,
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
        data = result.get("data")
        if not isinstance(data, dict):
            raise LingtuHttpError("上传响应缺少 data 对象。")
        file_id = data.get("fileId") or data.get("id") or ""
        if isinstance(file_id, bool) or not str(file_id).isdecimal() or int(file_id) <= 0:
            raise LingtuHttpError("上传响应缺少合法 data.fileId。")
        upload_url = data.get("uploadUrl") or ""
        raw_is_new = data.get("isNew")
        is_new = raw_is_new is True or raw_is_new == "true" or raw_is_new == "1" or raw_is_new == 1
        final_url = data.get("url") or ""

        should_upload = is_new or (raw_is_new is None and bool(upload_url))
        if should_upload:
            if not isinstance(upload_url, str) or not upload_url:
                raise LingtuHttpError("新文件上传响应缺少 data.uploadUrl。")
            put_file(
                upload_url,
                path,
                content_type,
                timeout=timeout,
                progress=progress,
                on_progress=on_progress,
            )
            request_json(
                "POST",
                confirm_path or FILE_CONFIRM_PATH,
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
