#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import http.client
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _shared_scripts_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "shared" / "scripts"
        if candidate.is_dir():
            return candidate
    raise RuntimeError("未找到 shared/scripts 目录。请确认 skill 安装完整。")


shared_scripts_dir = _shared_scripts_dir()
sys.path.insert(0, str(shared_scripts_dir))
from lingtu_auth import require_api_key
from lingtu_http import base_url as shared_base_url
from lingtu_upload import multipart_upload


DEFAULT_BASE_URL = "https://api.ailingtu.com"


def api_key():
    return require_api_key()


def base_url():
    return shared_base_url(DEFAULT_BASE_URL)


def upload_file(path):
    return multipart_upload(path, stream=True, progress=True, require_id=True, as_system_exit=True)


def stream_replication(payload, raw=False, emit=True, timeout=300):
    """Validate the stream before emitting a usable prompt; raw is diagnostic only."""
    url = f"{base_url()}/v1/material/analysisTask/stream"
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"x-api-key": api_key(), "Accept": "text/event-stream",
                 "Content-Type": "application/json"}, method="POST",
    )
    chunks = []
    task_id = None
    pending = []

    def consume(event):
        nonlocal task_id
        if not isinstance(event, dict):
            raise ValueError("Expected a JSON object in SSE data")
        status = event.get("status")
        if event.get("code") not in (None, 0) or status in ("error", "failed", "failure", "cancelled"):
            raise ValueError(f"Analysis failed: {event.get('message') or event.get('error') or status}")
        if status not in ("streaming", "done"):
            raise ValueError(f"Unexpected analysis status: {status!r}")
        if event.get("id") is not None:
            if task_id is not None and str(task_id) != str(event["id"]):
                raise ValueError("Analysis task id changed during stream")
            task_id = event["id"]
        piece = event.get("result")
        if piece is not None and not isinstance(piece, str):
            raise ValueError("Analysis result must be text")
        if status == "streaming" and piece:
            chunks.append(piece)
        return status == "done"

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get_content_type()
            if content_type != "text/event-stream":
                raise ValueError(f"Expected text/event-stream, got {content_type}")
            for raw_line in resp:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if raw and emit:
                    sys.stdout.write(raw_line.decode("utf-8"))
                    sys.stdout.flush()
                if not line:
                    if pending:
                        raise ValueError("Malformed JSON in SSE data")
                    continue
                if line.startswith(":"):
                    continue
                field, separator, value = line.partition(":")
                if field in ("event", "id", "retry"):
                    continue
                if field != "data" or not separator:
                    raise ValueError("Unexpected non-SSE response content")
                if value.startswith(" "):
                    value = value[1:]
                if not pending and value == "[DONE]":
                    break
                if not pending and not value:
                    continue
                pending.append(value)
                try:
                    event = json.loads("\n".join(pending))
                except json.JSONDecodeError:
                    continue
                pending.clear()
                if consume(event):
                    break
            if pending:
                raise ValueError("Truncated or malformed SSE data")
        prompt = "".join(chunks)
        if not prompt.strip():
            raise ValueError("Analysis returned an empty prompt")
    except urllib.error.HTTPError as exc:
        with exc:
            detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
    except (OSError, urllib.error.URLError, http.client.HTTPException, ValueError) as exc:
        raise SystemExit(f"Video analysis failed: {exc}. No complete result saved; do not use partial output.") from exc
    if emit and not raw:
        print(prompt)
    return {"id": task_id, "prompt": prompt}


def batch(args):
    urls = list(dict.fromkeys(line.strip() for line in Path(args.urls).read_text(encoding="utf-8").splitlines() if line.strip()))
    if not urls:
        raise SystemExit("URL list is empty")
    api_key()  # Fail before starting workers when configuration is missing.
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    def worker(url):
        path = destination / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if args.resume and path.exists():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                if (isinstance(saved, dict) and saved.get("source") == url
                        and saved.get("status") == "success" and isinstance(saved.get("prompt"), str)
                        and saved["prompt"].strip()):
                    return saved
            except (ValueError, OSError):
                pass
        record = {"source": url}
        try:
            result = stream_replication({"type": "REPLICATION", "url": url}, emit=False, timeout=args.timeout)
            record.update(status="success", **result)
        except (SystemExit, Exception) as exc:
            record.update(status="failed", error=str(exc))
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        return record

    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(worker, url) for url in urls]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            record = future.result()
            failures += record["status"] != "success"
            print(f"{index}/{len(urls)} {record['status']}: {record['source']}", file=sys.stderr)
    print(json.dumps({"total": len(urls), "failed": failures, "output_dir": str(destination)}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


def positive_timeout(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive number of seconds")
    return number


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

    result = stream_replication(payload, raw=args.raw, emit=not args.json, timeout=args.timeout)
    if args.json:
        print(json.dumps({"source": args.url or args.file or args.business_id, "status": "success", **result}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Lingtu video understanding (replication prompt).")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rep_parser = subparsers.add_parser("replicate", help="Generate a replication prompt from a video URL, local file, or uploaded material.")
    rep_parser.add_argument("--url", help="Public TikTok, Douyin, Xiaohongshu, WeChat Channels, YouTube, or Instagram URL.")
    rep_parser.add_argument("--file", help="Local video file path. Uploaded via /v1/file/upload, then replicated as businessType=FILE.")
    rep_parser.add_argument("--business-id", help="Uploaded material/file id (skip upload).")
    rep_parser.add_argument("--business-type", choices=["FILE", "MATERIAL"], help="Business type when using --business-id.")
    output_group = rep_parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="Print source, task id and prompt as JSON after success.")
    rep_parser.add_argument("--timeout", type=positive_timeout, default=300, help="Socket timeout in seconds (default: 300).")
    output_group.add_argument("--raw", action="store_true", help="Print raw SSE lines instead of the assembled prompt text.")

    upload_parser = subparsers.add_parser("upload", help="Upload a local file to /v1/file/upload and print the file id.")
    upload_parser.add_argument("path", help="Local file path to upload.")

    batch_parser = subparsers.add_parser("batch", help="Analyze a URL list with isolated JSON results.")
    batch_parser.add_argument("--urls", required=True, help="UTF-8 text file, one URL per line.")
    batch_parser.add_argument("--output-dir", required=True)
    batch_parser.add_argument("--workers", type=int, choices=range(1, 11), default=3)
    batch_parser.add_argument("--resume", action="store_true", help="Skip saved successful results; rerun failures.")
    batch_parser.add_argument("--timeout", type=positive_timeout, default=300)

    args = parser.parse_args()
    if args.command == "replicate":
        replicate(args)
    elif args.command == "batch":
        batch(args)
    elif args.command == "upload":
        result = upload_file(args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
