#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _shared_scripts_dir() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "shared" / "scripts"
        if candidate.is_dir():
            return candidate
    return None


shared_scripts_dir = _shared_scripts_dir()
if shared_scripts_dir is not None:
    sys.path.insert(0, str(shared_scripts_dir))
    from lingtu_auth import require_api_key
    from lingtu_http import base_url as shared_base_url
    from lingtu_upload import multipart_upload
else:
    # A single skill directory may be installed without the repository-level
    # shared/ tree. Keep that supported with the bundled minimal runtime.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lingtu_standalone import (
        base_url as shared_base_url,
        multipart_upload,
        require_api_key,
    )


DEFAULT_BASE_URL = "https://api.ailingtu.com"


def api_key():
    return require_api_key()


def base_url():
    return shared_base_url(DEFAULT_BASE_URL)


def upload_file(path):
    return multipart_upload(path, stream=True, progress=True, require_id=True, as_system_exit=True)


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
    rep_parser.add_argument("--url", help="Public TikTok, Douyin, Xiaohongshu, WeChat Channels, YouTube, or Instagram URL.")
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
