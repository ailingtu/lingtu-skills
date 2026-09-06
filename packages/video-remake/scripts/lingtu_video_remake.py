#!/usr/bin/env python3
"""Self-contained long-video transcription, Wan3.0 remake, review, and merge workflow."""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SUCCESS_STATUSES = {"succeeded", "success", "completed", "complete", "done", "finished"}
FAILURE_STATUSES = {"failed", "failure", "error", "cancelled", "canceled", "expired", "submit_failed"}
PROCESSING_STATUSES = {"waiting_submit", "submitting", "pending", "processing", "queued", "running"}
TERMINAL_SEGMENT_STATUSES = {"approved", "skipped", "merged"}
DEFAULT_PROMPT = (
    "Regenerate the reference video while preserving its subject motion, camera movement, "
    "timing, composition, and visual continuity. Do not add subtitles, logos, watermarks, "
    "or new text."
)
CONTACT_MESSAGE = "生成失败或遇到未知问题，请联系开发者：微信 yh8000m"


class WorkflowError(RuntimeError):
    pass


def emit(payload: dict[str, Any], *, error: bool = False) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr if error else sys.stdout)


def require_binary(name: str) -> str:
    binary = shutil.which(name)
    if not binary:
        raise WorkflowError(f"缺少系统命令 {name}，请先安装并确保它位于 PATH 中。")
    return binary


def run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise WorkflowError(f"命令执行失败（{completed.returncode}）：{' '.join(command[:3])}\n{detail}")
    return completed


def probe_media(path: Path) -> dict[str, Any]:
    ffprobe = require_binary("ffprobe")
    completed = run([
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration:stream=index,codec_type,width,height,r_frame_rate",
        "-of", "json",
        str(path),
    ])
    parsed = json.loads(completed.stdout)
    duration = float(parsed.get("format", {}).get("duration") or 0)
    streams = parsed.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if not video or duration <= 0:
        raise WorkflowError(f"无法从视频读取有效时长或视频流：{path}")
    return {
        "duration": duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "has_audio": any(item.get("codec_type") == "audio" for item in streams),
    }


def parse_clock(value: str) -> float:
    normalized = value.strip().replace(",", ".")
    parts = normalized.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) != 3:
        raise ValueError(f"无效时间戳：{value}")
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def normalize_segments(items: Iterable[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        start = item.get("start", item.get("start_time", item.get("begin")))
        end = item.get("end", item.get("end_time", item.get("finish")))
        text_value = item.get("text", item.get("content", item.get("transcript", "")))
        try:
            start_value = float(start)
            end_value = float(end)
        except (TypeError, ValueError):
            continue
        text = str(text_value or "").strip()
        if end_value <= start_value or start_value < 0:
            continue
        normalized.append({"start": round(start_value, 3), "end": round(end_value, 3), "text": text})
    normalized.sort(key=lambda item: (item["start"], item["end"]))
    if not normalized:
        raise WorkflowError("转写结果中没有可用的 start/end/text 时间戳片段。")
    return normalized


def find_segment_array(value: Any) -> list[Any] | None:
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return None
    for path in (
        ("segments",),
        ("data", "segments"),
        ("result", "segments"),
        ("data", "result", "segments"),
    ):
        current: Any = value
        for part in path:
            current = current.get(part) if isinstance(current, dict) else None
        if isinstance(current, list):
            return current
    return None


def parse_json_transcript(path: Path) -> list[dict[str, Any]]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    items = find_segment_array(parsed)
    if items is None:
        raise WorkflowError(f"JSON 中未找到时间戳 segments：{path}")
    return normalize_segments(items)


def parse_subtitle_transcript(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    pattern = re.compile(
        r"(?m)^((?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
        r"((?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{3})(?:[^\n]*)\n"
        r"(.*?)(?=\n\s*\n|\Z)",
        re.DOTALL,
    )
    items = []
    for match in pattern.finditer(text):
        caption = re.sub(r"<[^>]+>", "", match.group(3))
        caption = " ".join(line.strip() for line in caption.splitlines() if line.strip())
        items.append({"start": parse_clock(match.group(1)), "end": parse_clock(match.group(2)), "text": caption})
    return normalize_segments(items)


def load_transcript(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return parse_json_transcript(path)
    if suffix in {".srt", ".vtt"}:
        return parse_subtitle_transcript(path)
    raise WorkflowError("转写文件只支持 JSON、SRT 或 VTT。")


def multipart_body(fields: dict[str, str], file_path: Path, file_field: str = "file") -> tuple[bytes, str]:
    boundary = f"----LingtuBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
            str(value).encode("utf-8"),
            b"\r\n",
        ])
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), boundary


def request_json(
    method: str,
    url: str,
    *,
    api_key: str | None = None,
    payload: dict[str, Any] | None = None,
    body: bytes | None = None,
    content_type: str | None = None,
    timeout: int = 120,
) -> Any:
    headers = {"Accept": "application/json", "User-Agent": "lingtu-video-remake/0.1.0"}
    if api_key:
        headers["x-api-key"] = api_key
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise WorkflowError(f"HTTP {exc.code} {url}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise WorkflowError(f"请求失败 {url}: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"接口没有返回合法 JSON：{url}") from exc
    return parsed


def transcribe_http(source: Path, url: str, model: str | None, language: str | None) -> list[dict[str, Any]]:
    fields = {}
    if model:
        fields["model"] = model
    if language:
        fields["language"] = language
    body, boundary = multipart_body(fields, source)
    result = request_json(
        "POST",
        url,
        api_key=os.getenv("ASR_API_KEY") or os.getenv("LINGTU_API_KEY"),
        body=body,
        content_type=f"multipart/form-data; boundary={boundary}",
        timeout=600,
    )
    items = find_segment_array(result)
    if items is None:
        raise WorkflowError("HTTP ASR 响应中未找到 segments 数组。")
    return normalize_segments(items)


def transcribe_whisper(source: Path, output_dir: Path, model: str, language: str | None) -> list[dict[str, Any]]:
    whisper = require_binary("whisper")
    command = [
        whisper,
        str(source),
        "--model", model,
        "--output_format", "json",
        "--word_timestamps", "True",
        "--output_dir", str(output_dir),
    ]
    if language:
        command.extend(["--language", language])
    run(command)
    candidates = sorted(output_dir.glob(f"{source.stem}*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise WorkflowError("Whisper 完成但没有找到 JSON 输出。")
    return parse_json_transcript(candidates[0])


def sentence_boundary_score(text: str) -> int:
    stripped = text.rstrip()
    if not stripped:
        return 0
    if stripped.endswith(("。", "！", "？", ".", "!", "?")):
        return 3
    if stripped.endswith(("，", "；", "：", ",", ";", ":")):
        return 2
    return 1


def plan_segments(
    transcript: list[dict[str, Any]],
    duration: float,
    *,
    max_seconds: float = 15.0,
    min_seconds: float = 4.0,
) -> list[dict[str, Any]]:
    if max_seconds <= 0 or max_seconds > 15:
        raise WorkflowError("max-seconds 必须大于0且不超过15。")
    if min_seconds < 0 or min_seconds >= max_seconds:
        raise WorkflowError("min-seconds 必须大于等于0且小于 max-seconds。")

    candidates: list[tuple[float, int]] = []
    for index, item in enumerate(transcript):
        end = min(float(item["end"]), duration)
        if end <= 0 or end >= duration:
            continue
        gap = 0.0
        if index + 1 < len(transcript):
            gap = max(0.0, float(transcript[index + 1]["start"]) - end)
        score = sentence_boundary_score(str(item.get("text") or "")) + (2 if gap >= 0.6 else 1 if gap >= 0.25 else 0)
        candidates.append((end, score))

    boundaries = [0.0]
    cursor = 0.0
    while duration - cursor > max_seconds + 1e-6:
        limit = min(duration, cursor + max_seconds)
        eligible = [item for item in candidates if cursor + min_seconds <= item[0] <= limit]
        if eligible:
            strong = [item for item in eligible if item[1] >= 3]
            chosen = max(strong or eligible, key=lambda item: item[0])[0]
        else:
            chosen = limit
        if chosen <= cursor + 0.05:
            chosen = limit
        boundaries.append(round(chosen, 3))
        cursor = chosen
    boundaries.append(round(duration, 3))

    if len(boundaries) >= 3:
        tail = boundaries[-1] - boundaries[-2]
        merged = boundaries[-1] - boundaries[-3]
        if tail < min_seconds and merged <= max_seconds:
            boundaries.pop(-2)

    planned = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        overlaps = [
            item["text"]
            for item in transcript
            if float(item["end"]) > start and float(item["start"]) < end and str(item.get("text") or "").strip()
        ]
        planned.append({
            "id": f"segment-{index:03d}",
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "text": " ".join(overlaps),
            "status": "pending_cut",
            "source_clip": None,
            "attempts": [],
            "approved_attempt": None,
        })
    return planned


def cut_muted_segment(source: Path, destination: Path, start: float, end: float) -> None:
    ffmpeg = require_binary("ffmpeg")
    destination.parent.mkdir(parents=True, exist_ok=True)
    run([
        ffmpeg, "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", str(source),
        "-map", "0:v:0",
        "-an",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(destination),
    ])


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def manifest_path(job_dir: Path) -> Path:
    return job_dir / "manifest.json"


def load_manifest(job_dir: Path) -> dict[str, Any]:
    path = manifest_path(job_dir)
    if not path.is_file():
        raise WorkflowError(f"任务状态不存在：{path}")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if parsed.get("schema_version") != 1:
        raise WorkflowError("不支持的任务状态版本。")
    return parsed


def save_manifest(job_dir: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    atomic_write_json(manifest_path(job_dir), manifest)


def find_segment(manifest: dict[str, Any], segment_id: str) -> dict[str, Any]:
    for segment in manifest.get("segments", []):
        if segment.get("id") == segment_id:
            return segment
    raise WorkflowError(f"未找到片段：{segment_id}")


def next_segment(manifest: dict[str, Any]) -> dict[str, Any]:
    for segment in manifest.get("segments", []):
        if segment.get("status") == "cut_ready":
            return segment
        if segment.get("status") not in TERMINAL_SEGMENT_STATUSES:
            raise WorkflowError(
                f"必须先处理 {segment.get('id')}（当前状态 {segment.get('status')}），不能跳到后续片段。"
            )
    raise WorkflowError("没有待首次生成的片段。")


def deep_get(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


def first_value(value: dict[str, Any], paths: Iterable[str]) -> Any:
    for path in paths:
        found = deep_get(value, path)
        if found not in (None, ""):
            return found
    return None


def extract_records(response: dict[str, Any]) -> list[dict[str, Any]]:
    for path in ("list", "records", "items", "data.list", "data.records", "data.items", "data.data.list"):
        found = deep_get(response, path)
        if isinstance(found, list):
            return [item for item in found if isinstance(item, dict)]
    return []


def collect_video_urls(value: Any, key: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for child_key, child in value.items():
            found.extend(collect_video_urls(child, child_key))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_video_urls(child, key))
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        lower_path = urllib.parse.urlparse(value).path.lower()
        image = lower_path.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"))
        relevant_key = key.lower() in {"videourl", "video_url", "resulturl", "url", "output"}
        if relevant_key and not image:
            found.append(value)
    deduped = []
    for item in found:
        if item not in deduped:
            deduped.append(item)
    return deduped


def build_url(base: str, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return base.rstrip("/") + "/" + path.lstrip("/")


def require_lingtu_key() -> str:
    key = os.getenv("LINGTU_API_KEY", "").strip()
    if not key:
        raise WorkflowError(
            "缺少 LINGTU_API_KEY。请从本 Skill 根目录运行 "
            "`python3 shared/scripts/user_keys.py single bind`，并打开生成的授权链接。"
        )
    return key


def upload_video(path: Path, base_url: str, upload_path: str, api_key: str) -> int:
    body, boundary = multipart_body({}, path)
    response = request_json(
        "POST",
        build_url(base_url, upload_path),
        api_key=api_key,
        body=body,
        content_type=f"multipart/form-data; boundary={boundary}",
        timeout=300,
    )
    if not isinstance(response, dict):
        raise WorkflowError("上传接口返回类型不是 JSON 对象。")
    code = response.get("code")
    if code not in (None, 0, "0"):
        raise WorkflowError(f"上传失败：{response.get('message') or response}")
    file_id = first_value(response, ("data.id", "id"))
    try:
        normalized = int(file_id)
    except (TypeError, ValueError) as exc:
        raise WorkflowError(f"上传响应缺少合法 data.id：{response}") from exc
    if normalized <= 0:
        raise WorkflowError(f"上传响应包含无效 data.id：{file_id}")
    return normalized


def client_task_id() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def create_schedule(
    *,
    base_url: str,
    create_path: str,
    api_key: str,
    file_id: int,
    seconds: int,
    size: str,
    prompt: str,
    name: str,
) -> tuple[str, list[str], str]:
    task_id = client_task_id()
    payload = {
        "taskId": task_id,
        "type": "VIDEO_GENERATION",
        "params": {
            "prompt": prompt,
            "model": "wan3.0-video",
            "seconds": seconds,
            "size": size,
            "videoFileIds": [file_id],
            "watermark": False,
        },
        "nums": 1,
        "name": name,
    }
    response = request_json("POST", build_url(base_url, create_path), api_key=api_key, payload=payload)
    if not isinstance(response, dict):
        raise WorkflowError("创建接口返回类型不是 JSON 对象。")
    schedule_id = first_value(response, ("scheduleId", "schedule_id", "data.scheduleId", "data.schedule_id"))
    task_ids_value = first_value(response, ("taskIds", "task_ids", "data.taskIds", "data.task_ids"))
    task_ids = [str(item) for item in task_ids_value] if isinstance(task_ids_value, list) else []
    if schedule_id in (None, ""):
        raise WorkflowError(f"创建响应缺少 schedule_id：{response}")
    return str(schedule_id), task_ids, task_id


def task_matches(record: dict[str, Any], task_ids: list[str], client_id: str) -> bool:
    record_id = first_value(record, ("taskId", "id", "data.taskId", "assetDistDetail.0.taskId"))
    if task_ids and record_id not in (None, ""):
        return str(record_id) in task_ids
    if record_id not in (None, "") and str(record_id) == client_id:
        return True
    record_type = first_value(record, ("type", "data.type"))
    return record_type in (None, "", "VIDEO_GENERATION")


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=300) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        if temporary.exists():
            temporary.unlink()
        raise WorkflowError(f"下载生成视频失败：{exc}") from exc
    if temporary.stat().st_size <= 0:
        temporary.unlink()
        raise WorkflowError("下载到的生成视频为空。")
    temporary.replace(destination)


def poll_attempt(job_dir: Path, manifest: dict[str, Any], segment: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    attempts = segment.get("attempts") or []
    if not attempts:
        raise WorkflowError(f"{segment['id']} 没有可轮询的生成记录。")
    attempt = attempts[-1]
    schedule_id = attempt.get("schedule_id")
    if not schedule_id:
        raise WorkflowError(f"{segment['id']} 当前 attempt 缺少 schedule_id，不能安全重试创建。")

    base_url = str(attempt.get("base_url") or args.base_url)
    stored_task_list_path = str(attempt.get("task_list_path") or args.task_list_path)
    task_list_path = stored_task_list_path.format(schedule_id=urllib.parse.quote(str(schedule_id), safe=""))
    deadline = time.monotonic() + args.timeout
    api_key = require_lingtu_key()
    last_response: dict[str, Any] = {}
    consecutive_errors = 0
    while time.monotonic() < deadline:
        try:
            received = request_json("GET", build_url(base_url, task_list_path), api_key=api_key, timeout=90)
            if not isinstance(received, dict):
                raise WorkflowError("任务查询接口返回类型不是 JSON 对象。")
            last_response = received
            consecutive_errors = 0
        except WorkflowError as exc:
            consecutive_errors += 1
            attempt["last_error"] = str(exc)
            save_manifest(job_dir, manifest)
            if consecutive_errors >= 5:
                raise WorkflowError(
                    f"连续轮询失败，任务可能仍在运行。请使用 poll 恢复，禁止直接重建。最后错误：{exc}"
                ) from exc
            time.sleep(args.interval)
            continue

        records = [
            record for record in extract_records(last_response)
            if task_matches(record, [str(item) for item in attempt.get("task_ids") or []], str(attempt.get("client_task_id") or ""))
        ]
        for record in records:
            status = str(first_value(record, ("status", "state", "data.status")) or "").lower()
            if status in SUCCESS_STATUSES:
                urls = collect_video_urls(record)
                if not urls:
                    continue
                output = job_dir / "generated" / f"{segment['id']}-attempt-{attempt['number']}.mp4"
                download(urls[0], output)
                attempt.update({
                    "status": "completed",
                    "result_url": urls[0],
                    "output": str(output.resolve()),
                    "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "last_error": None,
                })
                segment["status"] = "waiting_review"
                save_manifest(job_dir, manifest)
                return attempt
            if status in FAILURE_STATUSES:
                attempt.update({"status": "failed", "response": record})
                segment["status"] = "failed"
                save_manifest(job_dir, manifest)
                raise WorkflowError(f"Wan3.0 明确返回失败：{record}")

        time.sleep(args.interval)

    attempt["last_error"] = "poll_timeout"
    segment["status"] = "generating"
    save_manifest(job_dir, manifest)
    raise WorkflowError("轮询超时，任务可能仍在运行。请使用 poll 恢复，禁止直接重建。")


def resolve_size(info: dict[str, Any], requested: str | None) -> str:
    if requested:
        if requested not in {"480x854", "854x480", "720x1280", "1280x720"}:
            raise WorkflowError("Wan3.0 size 仅支持 480x854、854x480、720x1280、1280x720。")
        return requested
    return "720x1280" if info["height"] >= info["width"] else "1280x720"


def generate_segment(job_dir: Path, manifest: dict[str, Any], segment: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if segment.get("status") == "generating":
        raise WorkflowError(f"{segment['id']} 已有运行中的任务，请使用 poll，不能重复创建。")
    allowed = {"cut_ready"}
    if getattr(args, "allow_regenerate", False):
        allowed |= {"rejected", "failed"}
    if segment.get("status") not in allowed:
        raise WorkflowError(f"{segment['id']} 当前状态 {segment.get('status')} 不允许生成。")

    source_clip = Path(str(segment.get("source_clip") or ""))
    if not source_clip.is_file():
        raise WorkflowError(f"消音参考片段不存在：{source_clip}")
    api_key = require_lingtu_key()
    info = probe_media(source_clip)
    size = resolve_size(info, args.size)
    seconds = max(1, min(15, math.ceil(float(segment["duration"]))))
    attempt_number = len(segment.get("attempts") or []) + 1
    prompt = args.prompt or manifest.get("prompt") or DEFAULT_PROMPT
    if getattr(args, "allow_regenerate", False):
        previous = (segment.get("attempts") or [])[-1] if segment.get("attempts") else {}
        note = previous.get("review_note")
        if note:
            prompt = f"{prompt}\nUser correction for this segment: {note}"

    file_id = upload_video(source_clip, args.base_url, args.upload_path, api_key)
    schedule_id, task_ids, task_id = create_schedule(
        base_url=args.base_url,
        create_path=args.schedule_create_path,
        api_key=api_key,
        file_id=file_id,
        seconds=seconds,
        size=size,
        prompt=prompt,
        name=f"{manifest['job_id']}-{segment['id']}-attempt-{attempt_number}",
    )
    attempt = {
        "number": attempt_number,
        "client_task_id": task_id,
        "schedule_id": schedule_id,
        "task_ids": task_ids,
        "reference_file_id": file_id,
        "seconds": seconds,
        "size": size,
        "prompt": prompt,
        "base_url": args.base_url,
        "task_list_path": args.task_list_path,
        "status": "generating",
        "output": None,
        "result_url": None,
        "review_note": None,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    segment.setdefault("attempts", []).append(attempt)
    segment["status"] = "generating"
    save_manifest(job_dir, manifest)
    return poll_attempt(job_dir, manifest, segment, args)


def command_prepare(args: argparse.Namespace) -> None:
    source = args.source.expanduser().resolve()
    if not source.is_file():
        raise WorkflowError(f"源视频不存在：{source}")
    job_dir = args.job_dir.expanduser().resolve()
    if job_dir.exists() and any(job_dir.iterdir()) and not args.force:
        raise WorkflowError(f"任务目录非空：{job_dir}。如确认覆盖准备阶段，使用 --force。")
    job_dir.mkdir(parents=True, exist_ok=True)
    info = probe_media(source)

    transcript_source: str
    if args.transcript:
        transcript_file = args.transcript.expanduser().resolve()
        transcript = load_transcript(transcript_file)
        transcript_source = transcript_file.suffix.lower().lstrip(".")
    elif args.asr_url:
        transcript = transcribe_http(source, args.asr_url, args.asr_model, args.language)
        transcript_source = "http"
    elif args.whisper:
        transcript = transcribe_whisper(source, job_dir, args.whisper_model, args.language)
        transcript_source = "whisper"
    else:
        raise WorkflowError("必须提供 --transcript、--whisper 或 --asr-url 之一。")

    transcript_path = job_dir / "transcript.json"
    atomic_write_json(transcript_path, {"segments": transcript})
    planned = plan_segments(
        transcript,
        info["duration"],
        max_seconds=args.max_seconds,
        min_seconds=args.min_seconds,
    )
    for segment in planned:
        destination = job_dir / "segments" / f"{segment['id']}-muted.mp4"
        cut_muted_segment(source, destination, float(segment["start"]), float(segment["end"]))
        segment["source_clip"] = str(destination.resolve())
        segment["status"] = "cut_ready"

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest = {
        "schema_version": 1,
        "job_id": args.job_id or f"remake-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "source": str(source),
        "source_duration": round(info["duration"], 3),
        "source_media": info,
        "transcription": {"source": transcript_source, "path": str(transcript_path.resolve())},
        "max_seconds": args.max_seconds,
        "min_seconds": args.min_seconds,
        "prompt": args.prompt or DEFAULT_PROMPT,
        "segments": planned,
        "final_output": None,
        "created_at": now,
        "updated_at": now,
    }
    save_manifest(job_dir, manifest)
    emit({
        "status": "prepared",
        "job_dir": str(job_dir),
        "manifest": str(manifest_path(job_dir)),
        "transcription_source": transcript_source,
        "segment_count": len(planned),
        "segments": [
            {key: segment[key] for key in ("id", "start", "end", "duration", "text", "source_clip", "status")}
            for segment in planned
        ],
    })


def add_network_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=os.getenv("LINGTU_AI_BASE_URL", "https://api.ailingtu.com"))
    parser.add_argument("--upload-path", default=os.getenv("LINGTU_FILE_UPLOAD_PATH", "/v1/file/upload"))
    parser.add_argument("--schedule-create-path", default=os.getenv("LINGTU_AI_SCHEDULE_CREATE_PATH", "/v1/ai/schedule/create"))
    parser.add_argument(
        "--task-list-path",
        default=os.getenv("LINGTU_AI_TASK_LIST_PATH", "/v1/ai/task/listByScheduleId?scheduleId={schedule_id}"),
    )
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--interval", type=int, default=5)


def command_generate(args: argparse.Namespace) -> None:
    job_dir = args.job_dir.expanduser().resolve()
    manifest = load_manifest(job_dir)
    segment = find_segment(manifest, args.segment) if args.segment else next_segment(manifest)
    attempt = generate_segment(job_dir, manifest, segment, args)
    emit({
        "status": "waiting_review",
        "job_dir": str(job_dir),
        "segment": segment["id"],
        "time_range": [segment["start"], segment["end"]],
        "text": segment["text"],
        "attempt": attempt["number"],
        "output": attempt["output"],
        "result_url": attempt["result_url"],
        "message": "请用户预览并明确确认、拒绝或跳过这一段；确认前不要生成下一段。",
    })


def command_poll(args: argparse.Namespace) -> None:
    job_dir = args.job_dir.expanduser().resolve()
    manifest = load_manifest(job_dir)
    segment = find_segment(manifest, args.segment)
    if segment.get("status") != "generating":
        raise WorkflowError(f"{segment['id']} 当前状态不是 generating。")
    attempt = poll_attempt(job_dir, manifest, segment, args)
    emit({
        "status": "waiting_review",
        "segment": segment["id"],
        "time_range": [segment["start"], segment["end"]],
        "text": segment["text"],
        "attempt": attempt["number"],
        "output": attempt["output"],
        "result_url": attempt["result_url"],
    })


def command_review_state(args: argparse.Namespace, action: str) -> None:
    job_dir = args.job_dir.expanduser().resolve()
    manifest = load_manifest(job_dir)
    segment = find_segment(manifest, args.segment)
    attempts = segment.get("attempts") or []
    if action == "approve":
        if segment.get("status") != "waiting_review" or not attempts:
            raise WorkflowError("只有 waiting_review 状态的片段可以确认。")
        attempt_number = args.attempt or attempts[-1]["number"]
        attempt = next((item for item in attempts if item.get("number") == attempt_number), None)
        if not attempt or attempt.get("status") != "completed" or not attempt.get("output"):
            raise WorkflowError(f"attempt {attempt_number} 没有可确认的完整输出。")
        segment["approved_attempt"] = attempt_number
        segment["status"] = "approved"
    elif action == "reject":
        if segment.get("status") != "waiting_review" or not attempts:
            raise WorkflowError("只有 waiting_review 状态的片段可以拒绝。")
        attempts[-1]["review_note"] = args.note
        segment["status"] = "rejected"
    elif action == "skip":
        if segment.get("status") in {"generating", "approved", "merged"}:
            raise WorkflowError(f"当前状态 {segment.get('status')} 不能跳过。")
        segment["status"] = "skipped"
    save_manifest(job_dir, manifest)
    emit({"status": segment["status"], "segment": segment["id"], "approved_attempt": segment.get("approved_attempt")})


def command_regenerate(args: argparse.Namespace) -> None:
    args.allow_regenerate = True
    command_generate(args)


def escape_concat_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")


def normalize_for_merge(source: Path, destination: Path, width: int, height: int, fps: int, keep_audio: bool) -> None:
    ffmpeg = require_binary("ffmpeg")
    info = probe_media(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps},setsar=1"
    )
    command = [ffmpeg, "-y", "-i", str(source)]
    if keep_audio and not info["has_audio"]:
        command.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])
    command.extend(["-map", "0:v:0", "-vf", video_filter, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"])
    if keep_audio:
        command.extend(["-map", "0:a:0" if info["has_audio"] else "1:a:0", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest"])
    else:
        command.append("-an")
    command.extend(["-movflags", "+faststart", str(destination)])
    run(command)


def command_merge(args: argparse.Namespace) -> None:
    job_dir = args.job_dir.expanduser().resolve()
    manifest = load_manifest(job_dir)
    blockers = [
        {"id": segment.get("id"), "status": segment.get("status")}
        for segment in manifest.get("segments", [])
        if segment.get("status") not in TERMINAL_SEGMENT_STATUSES
    ]
    if blockers:
        raise WorkflowError(f"仍有未确认片段，拒绝合成：{json.dumps(blockers, ensure_ascii=False)}")

    approved_sources: list[tuple[dict[str, Any], Path]] = []
    for segment in manifest.get("segments", []):
        if segment.get("status") == "skipped":
            continue
        attempt_number = segment.get("approved_attempt")
        attempt = next((item for item in segment.get("attempts", []) if item.get("number") == attempt_number), None)
        source = Path(str(attempt.get("output") if attempt else ""))
        if not attempt or not source.is_file():
            raise WorkflowError(f"{segment.get('id')} 的批准版本文件不存在。")
        approved_sources.append((segment, source))
    if not approved_sources:
        raise WorkflowError("没有任何已确认片段可供合成。")

    output = args.output.expanduser().resolve() if args.output else job_dir / "final" / "final-remake.mp4"
    if output.exists() and not args.force:
        raise WorkflowError(f"最终文件已存在：{output}。如确认覆盖，使用 --force。")
    output.parent.mkdir(parents=True, exist_ok=True)
    size = args.size or next(
        (
            item.get("size")
            for item in approved_sources[0][0].get("attempts", [])
            if item.get("number") == approved_sources[0][0].get("approved_attempt")
        ),
        None,
    ) or "720x1280"
    try:
        width, height = (int(value) for value in size.lower().split("x", 1))
    except (TypeError, ValueError) as exc:
        raise WorkflowError(f"无效合成尺寸：{size}") from exc

    normalized_files = []
    for index, (_, source) in enumerate(approved_sources, start=1):
        destination = job_dir / "normalized" / f"segment-{index:03d}.mp4"
        normalize_for_merge(source, destination, width, height, args.fps, not args.final_mute)
        normalized_files.append(destination)

    concat_file = job_dir / "normalized" / "concat.txt"
    concat_file.write_text("".join(f"file '{escape_concat_path(path)}'\n" for path in normalized_files), encoding="utf-8")
    ffmpeg = require_binary("ffmpeg")
    run([
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output),
    ])
    for segment, _ in approved_sources:
        segment["status"] = "merged"
    manifest["final_output"] = str(output)
    save_manifest(job_dir, manifest)
    emit({"status": "merged", "output": str(output), "segment_count": len(approved_sources), "final_mute": args.final_mute})


def command_status(args: argparse.Namespace) -> None:
    job_dir = args.job_dir.expanduser().resolve()
    manifest = load_manifest(job_dir)
    counts: dict[str, int] = {}
    rows = []
    for segment in manifest.get("segments", []):
        status = str(segment.get("status"))
        counts[status] = counts.get(status, 0) + 1
        attempts = segment.get("attempts") or []
        rows.append({
            "id": segment.get("id"),
            "start": segment.get("start"),
            "end": segment.get("end"),
            "text": segment.get("text"),
            "status": status,
            "attempts": len(attempts),
            "latest_output": attempts[-1].get("output") if attempts else None,
            "approved_attempt": segment.get("approved_attempt"),
        })
    emit({
        "job_id": manifest.get("job_id"),
        "job_dir": str(job_dir),
        "counts": counts,
        "segments": rows,
        "final_output": manifest.get("final_output"),
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Long-video transcription, muted segmentation, Wan3.0 remake, review, and merge.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Transcribe, plan <=15s segments, and create muted clips.")
    prepare.add_argument("source", type=Path)
    prepare.add_argument("--job-dir", type=Path, required=True)
    prepare.add_argument("--job-id")
    transcription = prepare.add_mutually_exclusive_group()
    transcription.add_argument("--transcript", type=Path, help="Timestamped JSON, SRT, or VTT transcript.")
    transcription.add_argument("--whisper", action="store_true", help="Use an installed Whisper CLI.")
    transcription.add_argument("--asr-url", default=os.getenv("LINGTU_ASR_URL"))
    prepare.add_argument("--whisper-model", default="small")
    prepare.add_argument("--asr-model", default=os.getenv("LINGTU_ASR_MODEL"))
    prepare.add_argument("--language")
    prepare.add_argument("--max-seconds", type=float, default=15.0)
    prepare.add_argument("--min-seconds", type=float, default=4.0)
    prepare.add_argument("--prompt", default=DEFAULT_PROMPT)
    prepare.add_argument("--force", action="store_true")
    prepare.set_defaults(func=command_prepare)

    generate = subparsers.add_parser("generate", help="Generate exactly one cut-ready segment.")
    generate.add_argument("--job-dir", type=Path, required=True)
    generate.add_argument("--segment")
    generate.add_argument("--prompt")
    generate.add_argument("--size")
    add_network_args(generate)
    generate.set_defaults(func=command_generate, allow_regenerate=False)

    regenerate = subparsers.add_parser("regenerate", help="Explicitly create a new attempt for a rejected/failed segment.")
    regenerate.add_argument("--job-dir", type=Path, required=True)
    regenerate.add_argument("--segment", required=True)
    regenerate.add_argument("--prompt")
    regenerate.add_argument("--size")
    add_network_args(regenerate)
    regenerate.set_defaults(func=command_regenerate, allow_regenerate=True)

    poll = subparsers.add_parser("poll", help="Resume polling an existing schedule without recreating it.")
    poll.add_argument("--job-dir", type=Path, required=True)
    poll.add_argument("--segment", required=True)
    add_network_args(poll)
    poll.set_defaults(func=command_poll)

    approve = subparsers.add_parser("approve", help="Approve one completed attempt.")
    approve.add_argument("--job-dir", type=Path, required=True)
    approve.add_argument("--segment", required=True)
    approve.add_argument("--attempt", type=int)
    approve.set_defaults(func=lambda args: command_review_state(args, "approve"))

    reject = subparsers.add_parser("reject", help="Reject the latest attempt and record a correction note.")
    reject.add_argument("--job-dir", type=Path, required=True)
    reject.add_argument("--segment", required=True)
    reject.add_argument("--note", required=True)
    reject.set_defaults(func=lambda args: command_review_state(args, "reject"))

    skip = subparsers.add_parser("skip", help="Explicitly skip one segment.")
    skip.add_argument("--job-dir", type=Path, required=True)
    skip.add_argument("--segment", required=True)
    skip.set_defaults(func=lambda args: command_review_state(args, "skip"))

    merge = subparsers.add_parser("merge", help="Merge only after every segment is approved or skipped.")
    merge.add_argument("--job-dir", type=Path, required=True)
    merge.add_argument("--output", type=Path)
    merge.add_argument("--size")
    merge.add_argument("--fps", type=int, default=30)
    merge.add_argument("--final-mute", action="store_true")
    merge.add_argument("--force", action="store_true")
    merge.set_defaults(func=command_merge)

    status = subparsers.add_parser("status", help="Print resumable job status.")
    status.add_argument("--job-dir", type=Path, required=True)
    status.set_defaults(func=command_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except (WorkflowError, OSError, ValueError, json.JSONDecodeError) as exc:
        emit({"error": str(exc), "message": CONTACT_MESSAGE}, error=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
