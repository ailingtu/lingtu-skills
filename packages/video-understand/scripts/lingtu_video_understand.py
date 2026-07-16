#!/usr/bin/env python3
import argparse
import http.client
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def _shared_scripts_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "shared" / "scripts"
        if candidate.is_dir():
            return candidate
    raise RuntimeError("未找到 shared/scripts 目录。请确认 skill 安装完整。")


sys.path.insert(0, str(_shared_scripts_dir()))

from lingtu_auth import require_api_key


DEFAULT_BASE_URL = "https://api.ailingtu.com"
UPLOAD_PATH = "/v1/file/upload"
UPLOAD_CHUNK_SIZE = 64 * 1024
PROGRESS_MIN_BYTES = 1024 * 1024


def api_key():
    return require_api_key()


def base_url():
    return os.environ.get("LINGTU_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _format_bytes(n):
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def _emit_progress(sent, total, show):
    if not show:
        return
    pct = (sent / total * 100) if total else 0
    sys.stderr.write(
        f"\rUploading: {_format_bytes(sent)} / {_format_bytes(total)} ({pct:5.1f}%)"
    )
    sys.stderr.flush()


def upload_file(path):
    if not os.path.isfile(path):
        raise SystemExit(f"File not found: {path}")

    filename = os.path.basename(path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    boundary = f"----LingtuFormBoundary{uuid.uuid4().hex}"

    file_size = os.path.getsize(path)
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    trailer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    total_size = len(header) + file_size + len(trailer)
    show_progress = file_size >= PROGRESS_MIN_BYTES and sys.stderr.isatty()

    parsed = urllib.parse.urlparse(base_url())
    if parsed.scheme not in ("http", "https"):
        raise SystemExit(f"Unsupported base URL scheme: {base_url()}")
    conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    conn = conn_cls(host, port, timeout=600)
    try:
        conn.putrequest("POST", UPLOAD_PATH)
        conn.putheader("x-api-key", api_key())
        conn.putheader("Accept", "application/json")
        conn.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
        conn.putheader("Content-Length", str(total_size))
        conn.endheaders()

        sent = 0
        conn.send(header)
        sent += len(header)
        _emit_progress(sent, total_size, show_progress)

        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                conn.send(chunk)
                sent += len(chunk)
                _emit_progress(sent, total_size, show_progress)

        conn.send(trailer)
        sent += len(trailer)
        _emit_progress(sent, total_size, show_progress)
        if show_progress:
            sys.stderr.write("\n")
            sys.stderr.flush()

        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        if resp.status >= 400:
            raise SystemExit(f"HTTP {resp.status} from {base_url()}{UPLOAD_PATH}: {body}")
    finally:
        conn.close()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise SystemExit(f"Upload returned non-JSON body: {body}")

    if not isinstance(payload, dict) or payload.get("code") != 0:
        raise SystemExit(f"Upload failed: {json.dumps(payload, ensure_ascii=False)}")
    data = payload.get("data") or {}
    file_id = data.get("id")
    if file_id is None:
        raise SystemExit(f"Upload response missing data.id: {json.dumps(payload, ensure_ascii=False)}")
    return {"id": file_id, "url": data.get("url"), "isNew": data.get("isNew")}


def stream_replication(payload, raw=False):
    url = f"{base_url()}/v1/material/analysisTask/stream"
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
    chunks = []
    task_id = None
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace")
                if raw:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    continue
                text = line.strip()
                if not text:
                    continue
                if text.startswith("data:"):
                    text = text[5:].lstrip()
                if not text or text == "[DONE]":
                    continue
                try:
                    event = json.loads(text)
                except json.JSONDecodeError:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    continue
                if isinstance(event, dict):
                    if task_id is None and event.get("id") is not None:
                        task_id = event.get("id")
                    piece = event.get("result")
                    if isinstance(piece, str) and piece:
                        chunks.append(piece)
                        sys.stdout.write(piece)
                        sys.stdout.flush()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc

    if not raw:
        sys.stdout.write("\n")
        sys.stdout.flush()
    return {"id": task_id, "prompt": "".join(chunks)}


def replicate(args):
    inputs = [bool(args.url), bool(args.business_id), bool(args.file)]
    if sum(inputs) != 1:
        raise SystemExit("Pass exactly one of --url, --business-id, or --file.")
    if args.business_id and not args.business_type:
        raise SystemExit("--business-id requires --business-type FILE or MATERIAL.")

    payload = {"type": "REPLICATION"}
    if args.url:
        payload["url"] = args.url
    elif args.file:
        if not os.path.isfile(args.file):
            raise SystemExit(f"File not found: {args.file}")
        sys.stderr.write(f"Uploading {args.file} ...\n")
        sys.stderr.flush()
        uploaded = upload_file(args.file)
        sys.stderr.write(
            f"Uploaded: id={uploaded['id']} url={uploaded.get('url')} isNew={uploaded.get('isNew')}\n"
        )
        sys.stderr.flush()
        payload["businessId"] = str(uploaded["id"])
        payload["businessType"] = "FILE"
    else:
        payload["businessId"] = str(args.business_id)
        payload["businessType"] = args.business_type

    stream_replication(payload, raw=args.raw)


def main():
    parser = argparse.ArgumentParser(description="Lingtu video understanding (replication prompt).")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rep_parser = subparsers.add_parser("replicate", help="Generate a replication prompt from a video URL, local file, or uploaded material.")
    rep_parser.add_argument("--url", help="Public TikTok, YouTube, or Instagram URL.")
    rep_parser.add_argument("--file", help="Local video file path. Uploaded via /v1/file/upload, then replicated as businessType=FILE.")
    rep_parser.add_argument("--business-id", help="Uploaded material/file id (skip upload).")
    rep_parser.add_argument("--business-type", choices=["FILE", "MATERIAL"], help="Business type when using --business-id.")
    rep_parser.add_argument("--raw", action="store_true", help="Print raw SSE lines instead of the assembled prompt text.")

    upload_parser = subparsers.add_parser("upload", help="Upload a local file to /v1/file/upload and print the file id.")
    upload_parser.add_argument("path", help="Local file path to upload.")

    args = parser.parse_args()
    if args.command == "replicate":
        replicate(args)
    elif args.command == "upload":
        result = upload_file(args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
