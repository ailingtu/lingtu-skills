#!/usr/bin/env python3
"""Create and poll Lingtu AI media-generation tasks."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import secrets
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

from lingtu_auth import add_identity_arguments, configure_identity, require_api_key


SUCCESS_STATUSES = {"succeeded", "success", "completed", "complete", "done", "finished"}
FAILURE_STATUSES = {"failed", "failure", "error", "cancelled", "canceled", "expired"}
DEVELOPER_CONTACT = "微信 yh8000m"
DEVELOPER_CONTACT_MESSAGE = "生成失败或遇到未知问题，请联系开发者：微信 yh8000m"
UPLOAD_PATH = "/v1/file/upload"
ASSET_KEYS = {
    "url",
    "urls",
    "coverUrl",
    "image_url",
    "image_urls",
    "thumbnailUrl",
    "videoUrl",
    "video_url",
    "video_urls",
    "output",
    "outputs",
    "result",
    "results",
    "resultUrl",
    "base64",
}


def expected_task_type(kind: str) -> str:
    normalized = kind.lower()
    if normalized == "image":
        return "IMAGE_GENERATION"
    if normalized == "video":
        return "VIDEO_GENERATION"
    return normalized.upper()


def asset_type_for_kind(kind: str) -> str:
    normalized = kind.lower()
    if normalized == "image":
        return "IMAGE"
    if normalized == "video":
        return "VIDEO"
    return normalized.upper()


def generate_client_task_id() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def upload_reference_image(path: str, base_url: str, api_key: str) -> str:
    image_path = Path(path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Reference image not found: {path}")

    filename = image_path.name
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    boundary = f"----LingtuFormBoundary{uuid.uuid4().hex}"
    file_bytes = image_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    upload_url = build_url(base_url, UPLOAD_PATH)
    request = urllib.request.Request(
        upload_url,
        data=body,
        headers={
            "Accept": "application/json",
            "x-api-key": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {upload_url}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Reference upload failed for {path}: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Upload returned non-JSON body: {raw[:500]}") from exc
    if not isinstance(payload, dict) or payload.get("code") not in (0, None):
        raise RuntimeError(f"Upload failed: {raw[:500]}")
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise RuntimeError(f"Upload response missing data: {raw[:500]}")
    url = data.get("url")
    if not isinstance(url, str) or not url:
        raise RuntimeError(f"Upload response missing data.url: {raw[:500]}")
    return url


def resolve_reference_image(path_or_url: str, base_url: str, api_key: str) -> str:
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    return upload_reference_image(path_or_url, base_url, api_key)


def http_json(method: str, url: str, api_key: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "x-api-key": api_key,
    }
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Expected JSON from {url}, got: {raw[:500]}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Expected JSON object from {url}, got: {type(parsed).__name__}")
    return parsed


def deep_get(data: dict[str, Any], paths: list[str]) -> Any:
    for path in paths:
        current: Any = data
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                current = None
                break
        if current not in (None, ""):
            return current
    return None


def extract_list_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        "list",
        "records",
        "items",
        "data.list",
        "data.records",
        "data.items",
        "data.data.list",
        "data.data.records",
        "data.data.items",
    ]
    for path in candidates:
        value = deep_get(data, [path])
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def normalize_task_ids(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value not in (None, ""):
        return [str(value)]
    return []


def parse_created_at(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def collect_values(value: Any, keys: set[str]) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                found.append(item)
            found.extend(collect_values(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(collect_values(item, keys))
    return found


def flatten_assets(values: list[Any]) -> list[str]:
    assets: list[str] = []
    for value in values:
        if isinstance(value, str):
            assets.append(value)
        elif isinstance(value, list):
            assets.extend(flatten_assets(value))
        elif isinstance(value, dict):
            for key in ("url", "image_url", "imageUrl", "video_url", "videoUrl", "resultUrl", "coverUrl", "thumbnailUrl", "base64", "data"):
                item = value.get(key)
                if isinstance(item, str):
                    assets.append(item)
    return assets


def dedupe_assets(assets: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for asset in assets:
        if asset.startswith(("ai-images/", "ai-videos/")):
            asset = f"https://static.ailingtu.com/{asset}"
        if asset in seen:
            continue
        seen.add(asset)
        deduped.append(asset)
    return deduped


def markdown_for_assets(assets: list[str]) -> list[str]:
    markdown: list[str] = []
    image_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif")
    video_exts = (".mp4", ".mov", ".webm", ".m4v")
    for index, asset in enumerate(assets, start=1):
        normalized = asset.split("?", 1)[0].lower()
        if asset.startswith("data:image/") or normalized.endswith(image_exts):
            markdown.append(f"![Lingtu result {index}]({asset})")
        elif normalized.endswith(video_exts):
            markdown.append(f"![Lingtu video result {index}]({asset})")
    return markdown


def extension_from_url(asset: str) -> str | None:
    parsed = urllib.parse.urlparse(asset)
    suffix = Path(parsed.path).suffix
    return suffix if suffix else None


def extension_from_response(asset: str, content_type: str | None) -> str:
    if content_type:
        extension = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if extension:
            return extension
    return extension_from_url(asset) or ".bin"


def save_remote_asset_with_urllib(asset: str, output_dir: Path, index: int) -> str | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0",
    }
    request = urllib.request.Request(asset, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = response.read()
                extension = extension_from_response(asset, response.headers.get("Content-Type"))
            path = output_dir / f"lingtu-output-{index}{extension}"
            path.write_bytes(data)
            if path.stat().st_size > 0:
                return str(path.resolve())
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    return None


def save_remote_asset_with_curl(asset: str, output_dir: Path, index: int) -> str | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    extension = extension_from_url(asset) or ".bin"
    path = output_dir / f"lingtu-output-{index}{extension}"
    command = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "--connect-timeout",
        "30",
        "--max-time",
        "300",
        "-A",
        "Mozilla/5.0",
        "-o",
        str(path),
        asset,
    ]
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode == 0 and path.exists() and path.stat().st_size > 0:
        return str(path.resolve())
    if path.exists():
        path.unlink()
    return None


def save_remote_asset(asset: str, output_dir: Path, index: int) -> str:
    saved = save_remote_asset_with_urllib(asset, output_dir, index)
    if saved:
        return saved

    saved = save_remote_asset_with_curl(asset, output_dir, index)
    if saved:
        return saved

    return asset


def save_assets(assets: list[str], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for index, asset in enumerate(assets, start=1):
        if asset.startswith(("http://", "https://")):
            saved.append(save_remote_asset(asset, output_dir, index))
            continue

        mime = None
        payload = asset
        if asset.startswith("data:") and "," in asset:
            meta, payload = asset.split(",", 1)
            mime = meta.split(";", 1)[0].removeprefix("data:")
        extension = mimetypes.guess_extension(mime or "") or extension_from_url(asset) or ".bin"
        path = output_dir / f"lingtu-output-{index}{extension}"
        path.write_bytes(base64.b64decode(payload))
        saved.append(str(path.resolve()))
    return saved


def build_url(base_url: str, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def format_path(path: str, **values: Any) -> str:
    quoted = {key: urllib.parse.quote(str(value), safe="") for key, value in values.items()}
    return path.format(**quoted)


def build_create_payload(args: argparse.Namespace, references: list[str]) -> dict[str, Any]:
    try:
        extra_payload = json.loads(args.payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid --payload-json: {exc}") from exc
    if not isinstance(extra_payload, dict):
        raise ValueError("--payload-json must be a JSON object.")

    params: dict[str, Any] = {
        "prompt": args.prompt,
        "model": args.model,
    }
    kind = args.kind.lower()
    if kind == "video":
        params.update(
            {
                "seconds": args.seconds,
                "size": args.size,
                "watermark": args.watermark,
            }
        )
        task_type = expected_task_type(kind)
    elif kind == "image":
        params["aspectRatio"] = args.aspect_ratio
        task_type = expected_task_type(kind)
    else:
        task_type = expected_task_type(kind)

    if kind == "image" and references:
        params["inputReferences"] = references
    elif len(references) == 1:
        params["inputReference"] = references[0]
    elif len(references) > 1:
        params["inputReferences"] = references

    payload: dict[str, Any] = {
        "type": task_type,
        "params": params,
        "nums": args.nums,
    }
    payload.update(extra_payload)
    payload.setdefault("taskId", args.client_task_id)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and poll a Lingtu AI content schedule.")
    parser.add_argument("--kind", required=True, help="Media type, such as image or video.")
    parser.add_argument("--prompt", required=True, help="Generation prompt.")
    parser.add_argument(
        "--model",
        help="Lingtu AI model name. Video: gemini-omni-video (default), veo3.1-lite-extend, veo3.1-extend, grok-imagine-1, seedance2.0-fast, seedance-2.0. Image: gpt-image-2 (default), nano-banana-2, nano-banana-2-2k, nano-banana-2-4k.",
    )
    parser.add_argument(
        "--seconds",
        type=int,
        help="Video duration in seconds. Defaults: gemini-omni-video=10, veo3.1-*=8, grok-imagine-1=15, seedance2.0-fast=10.",
    )
    parser.add_argument("--size", default="720x1280", help="Video size, such as 720x1280 or 1280x720.")
    parser.add_argument("--aspect-ratio", default="1:1", help="Image aspect ratio, such as 1:1 or 9:16.")
    parser.add_argument("--nums", type=int, default=1, help="Number of outputs to create.")
    parser.add_argument("--watermark", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--reference-image",
        action="append",
        default=[],
        help="Reference image as a remote http(s) url, or a local path that will be uploaded to /v1/file/upload first. Repeat for multiple images; order is preserved.",
    )
    parser.add_argument("--payload-json", default="{}", help="Additional top-level JSON fields merged into the create request.")
    parser.add_argument(
        "--client-task-id",
        default=os.getenv("LINGTU_AI_CLIENT_TASK_ID"),
        help="Optional caller-generated task id. Defaults to a generated 8-character id.",
    )
    parser.add_argument(
        "--create-mode",
        choices=["auto", "direct", "schedule"],
        default=os.getenv("LINGTU_AI_CREATE_MODE", "auto"),
        help="Create through the schedule API by default, or direct task API when explicitly requested.",
    )
    parser.add_argument("--base-url", default=os.getenv("LINGTU_AI_BASE_URL", "https://api.ailingtu.com"))
    parser.add_argument("--create-path", default=os.getenv("LINGTU_AI_CREATE_PATH", "/v1/ai/task/create"))
    parser.add_argument("--status-path", default=os.getenv("LINGTU_AI_STATUS_PATH", "/v1/ai/task/query?taskId={task_id}"))
    parser.add_argument("--schedule-create-path", default=os.getenv("LINGTU_AI_SCHEDULE_CREATE_PATH", "/v1/ai/schedule/create"))
    parser.add_argument(
        "--task-list-path",
        default=os.getenv(
            "LINGTU_AI_TASK_LIST_PATH",
            "/v1/ai/task/listByScheduleId?scheduleId={schedule_id}",
        ),
    )
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--output-dir", default=".")
    add_identity_arguments(parser)
    args = parser.parse_args()
    args.seconds_was_set = args.seconds is not None
    return args


def default_video_seconds(model: str) -> int:
    """Return the default duration for a given video model."""
    m = model.lower()
    if m == "gemini-omni-video":
        return 10
    if m in ("veo3.1-lite-extend", "veo3.1-extend"):
        return 8
    if m == "grok-imagine-1":
        return 15
    if m in ("seedance2.0-fast", "seedance-2.0"):
        return 10
    return 8  # conservative fallback


def resolve_create_mode(args: argparse.Namespace) -> str:
    if args.create_mode != "auto":
        return args.create_mode
    return "schedule"


def extract_assets_from_response(response: dict[str, Any], output_dir: Path) -> tuple[list[str], list[str]]:
    assets = dedupe_assets(flatten_assets(collect_values(response, ASSET_KEYS)))
    saved = save_assets(assets, output_dir) if assets else []
    return saved, markdown_for_assets(saved)


def print_success(
    identifier: dict[str, Any],
    status: Any,
    assets: list[str],
    markdown: list[str],
    response: dict[str, Any],
    output_dir: Path,
) -> None:
    print(
        json.dumps(
            {
                **identifier,
                "status": status,
                "output_dir": str(output_dir.resolve()),
                "assets": assets,
                "markdown": markdown,
                "response": response,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def error_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "contact_developer": DEVELOPER_CONTACT,
        "message": payload.get("message") or DEVELOPER_CONTACT_MESSAGE,
    }


def print_error(payload: dict[str, Any], *, stderr: bool = False) -> None:
    print(json.dumps(error_payload(payload), ensure_ascii=False, indent=2), file=sys.stderr if stderr else sys.stdout)


def validate_task_type(response: dict[str, Any], expected_type: str, identifier: dict[str, Any]) -> bool:
    actual_type = deep_get(response, ["type", "data.type", "task.type", "data.task.type"])
    if actual_type and str(actual_type).upper() != expected_type:
        print_error(
            {
                **identifier,
                "error": "Task type mismatch.",
                "expected_type": expected_type,
                "actual_type": actual_type,
                "response": response,
            }
        )
        return False
    return True


def poll_task(args: argparse.Namespace, api_key: str, task_id: Any) -> int:
    deadline = time.monotonic() + args.timeout
    last_response: dict[str, Any] = {}
    expected_type = expected_task_type(args.kind)
    while time.monotonic() < deadline:
        status_path = format_path(args.status_path, task_id=task_id)
        status_url = build_url(args.base_url, status_path)
        last_response = http_json("GET", status_url, api_key)
        status = deep_get(last_response, ["status", "state", "data.status", "data.state"])
        normalized = str(status or "").lower()

        if normalized in SUCCESS_STATUSES:
            if not validate_task_type(last_response, expected_type, {"task_id": task_id}):
                return 1
            assets, markdown = extract_assets_from_response(last_response, Path(args.output_dir))
            print_success({"task_id": task_id}, status, assets, markdown, last_response, Path(args.output_dir))
            return 0

        if normalized in FAILURE_STATUSES:
            print_error({"task_id": task_id, "status": status, "response": last_response})
            return 1

        time.sleep(args.interval)

    print_error({"task_id": task_id, "error": "Timed out while polling task.", "last_response": last_response})
    return 1


def record_matches_request(
    record: dict[str, Any],
    args: argparse.Namespace,
    create_started_at: float,
    schedule_id: Any,
    task_ids: list[str],
) -> bool:
    record_schedule_id = deep_get(record, ["scheduleId", "data.scheduleId", "schedule.scheduleId"])
    if record_schedule_id and str(record_schedule_id) != str(schedule_id):
        return False

    if task_ids:
        record_task_ids = normalize_task_ids(
            deep_get(record, ["taskId", "id", "data.taskId", "data.id", "assetDistDetail.0.taskId"])
        )
        if record_task_ids and not any(record_task_id in task_ids for record_task_id in record_task_ids):
            return False
        if record_task_ids and any(record_task_id in task_ids for record_task_id in record_task_ids):
            return True

    if args.client_task_id:
        record_ids = [
            deep_get(record, ["taskId", "data.taskId"]),
            deep_get(record, ["businessId", "data.businessId"]),
            deep_get(record, ["assetDistDetail.0.taskId"]),
        ]
        if any(str(record_id) == args.client_task_id for record_id in record_ids if record_id):
            return True

    record_type = deep_get(record, ["type", "data.type"])
    if record_type and str(record_type).upper() != expected_task_type(args.kind):
        return False

    prompt = deep_get(record, ["params.prompt", "inputData.prompt", "inputData.params.prompt", "data.params.prompt"])
    if prompt and prompt != args.prompt:
        return False

    model = deep_get(record, ["params.model", "inputData.model", "model"])
    if model and args.model and model != args.model:
        return False

    created_at = parse_created_at(deep_get(record, ["createdAt", "created_at", "data.createdAt"]))
    if created_at is not None and created_at < create_started_at - 120:
        return False

    return True


def poll_schedule(args: argparse.Namespace, api_key: str, schedule_id: Any, task_ids: list[str], create_started_at: float) -> int:
    deadline = time.monotonic() + args.timeout
    last_task_list_response: dict[str, Any] = {}
    expected_type = expected_task_type(args.kind)
    asset_type = asset_type_for_kind(args.kind)

    while time.monotonic() < deadline:
        task_list_path = format_path(args.task_list_path, asset_type=asset_type, task_type=expected_type, schedule_id=schedule_id)
        task_list_url = build_url(args.base_url, task_list_path)
        last_task_list_response = http_json("GET", task_list_url, api_key)
        records = [
            record
            for record in extract_list_response(last_task_list_response)
            if record_matches_request(record, args, create_started_at, schedule_id, task_ids)
        ]

        result_records: list[dict[str, Any]] = []
        assets: list[str] = []
        for record in records:
            if not validate_task_type(record, expected_type, {"schedule_id": schedule_id, "task_id": record.get("taskId")}):
                return 1
            status = str(record.get("status") or "").lower()
            record_assets = dedupe_assets(flatten_assets(collect_values(record, ASSET_KEYS)))
            if status in SUCCESS_STATUSES and record_assets:
                result_records.append(record)
                assets.extend(record_assets)

        assets = dedupe_assets(assets)
        if len(assets) >= max(1, args.nums):
            saved = save_assets(assets, Path(args.output_dir))
            print_success(
                {
                    "schedule_id": schedule_id,
                    "task_ids": task_ids or [record.get("taskId") for record in result_records if record.get("taskId")],
                },
                "COMPLETED",
                saved,
                markdown_for_assets(saved),
                {"tasks": result_records},
                Path(args.output_dir),
            )
            return 0

        if records and all(str(record.get("status") or "").lower() in FAILURE_STATUSES for record in records):
            print_error(
                {
                    "schedule_id": schedule_id,
                    "status": "FAILED",
                    "response": {"tasks": records},
                }
            )
            return 1

        time.sleep(args.interval)

    print_error(
        {
            "schedule_id": schedule_id,
            "error": "Timed out while polling schedule.",
            "last_response": {"task_list": last_task_list_response},
        }
    )
    return 1


def main() -> int:
    args = parse_args()
    configure_identity(args.channel, args.user_id)
    resolved_mode = resolve_create_mode(args)
    if not args.client_task_id:
        args.client_task_id = generate_client_task_id()
    if not args.model:
        args.model = "gpt-image-2" if args.kind.lower() == "image" else "gemini-omni-video"
    if args.kind.lower() == "video" and not args.seconds_was_set:
        args.seconds = default_video_seconds(args.model)
    try:
        api_key = require_api_key()
    except SystemExit as exc:
        print_error({"error": str(exc)}, stderr=True)
        return 2
    try:
        reference_images = [
            resolve_reference_image(path_or_url, args.base_url, api_key)
            for path_or_url in args.reference_image
        ]
        payload = build_create_payload(args, reference_images)
    except (OSError, ValueError, RuntimeError) as exc:
        print_error({"error": str(exc)}, stderr=True)
        return 2

    create_started_at = time.time()
    created: dict[str, Any] | None = None
    if resolved_mode == "direct":
        create_url = build_url(args.base_url, args.create_path)
        try:
            created = http_json("POST", create_url, api_key, payload)
        except RuntimeError as exc:
            print_error({"error": str(exc), "create_mode": resolved_mode}, stderr=True)
            return 1

    if resolved_mode == "schedule":
        schedule_create_url = build_url(args.base_url, args.schedule_create_path)
        try:
            created = http_json("POST", schedule_create_url, api_key, payload)
        except RuntimeError as exc:
            print_error({"error": str(exc), "create_mode": resolved_mode})
            return 1

    if created is None:
        print_error({"error": "No create response.", "create_mode": resolved_mode})
        return 1

    task_id = deep_get(created, ["task_id", "taskId", "id", "data.task_id", "data.taskId", "data.id"])
    schedule_id = deep_get(created, ["schedule_id", "scheduleId", "data.schedule_id", "data.scheduleId"])
    task_ids = normalize_task_ids(deep_get(created, ["taskIds", "task_ids", "data.taskIds", "data.task_ids"]))
    if task_id:
        return poll_task(args, api_key, task_id)
    if schedule_id:
        return poll_schedule(args, api_key, schedule_id, task_ids, create_started_at)

    print_error(
        {
            "error": "Could not find task id or schedule id in create response.",
            "create_mode": resolved_mode,
            "response": created,
        }
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
