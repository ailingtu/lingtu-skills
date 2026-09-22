#!/usr/bin/env python3
"""Fetch public video data and download the direct media URL."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _shared_scripts_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "shared" / "scripts"
        if candidate.is_dir():
            return candidate
    raise RuntimeError("未找到 shared/scripts 目录。请确认 skill 安装完整。")


sys.path.insert(0, str(_shared_scripts_dir()))
from lingtu_http import LingtuHttpError, request_json

FETCH_PATH = "/v1/material/fetch"
MEDIA_FIELDS = ("downloadAddr", "playAddr")
DEFAULT_API_TIMEOUT = 60
DEFAULT_DOWNLOAD_TIMEOUT = 180
DEFAULT_RETRIES = 2
DEFAULT_RETRY_SLEEP_MS = 1500


def is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def media_url(data: dict[str, Any], page_url: str) -> tuple[str | None, str | None]:
    """Pick the direct video URL from additional response fields."""
    for field in MEDIA_FIELDS:
        value = data.get(field)
        if is_http_url(value):
            return value, field
    value = data.get("videoUrl")
    if is_http_url(value) and value != page_url:
        return value, "videoUrl"
    return None, None


def present(page_url: str, data: dict[str, Any], media: tuple[str | None, str | None]) -> dict[str, Any]:
    url, field = media
    return {
        "sourceUrl": page_url,
        "videoId": data.get("videoId"),
        "uniqueId": data.get("uniqueId"),
        "playCount": data.get("playCount"),
        "diggCount": data.get("diggCount"),
        "commentCount": data.get("commentCount"),
        "shareCount": data.get("shareCount"),
        "collectCount": data.get("collectCount"),
        "coverUrl": data.get("coverUrl"),
        "videoDesc": data.get("videoDesc"),
        "releaseAt": data.get("releaseAt"),
        "media": None if url is None else {"field": field, "url": url},
        "imageCount": len(image_urls(data)),
        "data": data,
    }


def fetch_material(
    page_url: str,
    *,
    timeout: float,
    retries: int,
    retry_sleep_ms: int,
) -> dict[str, Any]:
    last_error: LingtuHttpError | None = None
    for attempt in range(retries + 1):
        try:
            data = request_json(
                "POST",
                FETCH_PATH,
                body={"videoUrl": page_url},
                timeout=timeout,
                expect_envelope=True,
                return_data=True,
            )
        except LingtuHttpError as exc:
            last_error = exc
            transient = exc.status is None or exc.status == 429 or exc.status >= 500
            if not transient or attempt >= retries:
                raise SystemExit(f"视频数据接口调用失败：{exc}") from exc
            wait_seconds = retry_sleep_ms * (2**attempt) / 1000
            sys.stderr.write(
                f"请求暂时失败，{wait_seconds:g} 秒后重试 ({attempt + 1}/{retries})。\n"
            )
            time.sleep(wait_seconds)
            continue
        if not isinstance(data, dict):
            raise SystemExit("视频数据接口调用失败：缺少 data 对象")
        return data
    raise SystemExit(f"视频数据接口调用失败：{last_error}")


IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/heic": ".heic",
}
VIDEO_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}
KNOWN_SUFFIXES = set(IMAGE_EXTENSIONS.values()) | set(VIDEO_EXTENSIONS.values()) | {".jpeg", ".m4v"}


def image_urls(data: dict[str, Any]) -> list[str]:
    """Collect 图文 image URLs. Video covers are not photo-note images."""
    if str(data.get("materialType") or "").upper() == "VIDEO":
        return []
    urls: list[str] = []
    seen: set[str] = set()
    raw = data.get("imageList") or []
    if isinstance(raw, list):
        for item in raw:
            value = item.get("url") if isinstance(item, dict) else item
            if is_http_url(value) and value not in seen:
                seen.add(value)
                urls.append(value)
    has_video = is_http_url(data.get("downloadAddr")) or is_http_url(data.get("playAddr"))
    cover = data.get("coverUrl")
    if not urls and not has_video and is_http_url(cover):
        urls.append(cover)
    return urls


def extension_for(content_type: str, media: str, fallback: str) -> str:
    lowered = content_type.split(";", 1)[0].strip().lower()
    mapped = IMAGE_EXTENSIONS.get(lowered) or VIDEO_EXTENSIONS.get(lowered)
    if mapped:
        return mapped
    suffix = Path(urlparse(media).path).suffix.lower()
    if suffix == ".jpeg":
        return ".jpg"
    if suffix in KNOWN_SUFFIXES:
        return suffix
    return fallback


def refuse_existing(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"文件已存在：{path}。确认覆盖后再加 --force。")


def write_json(path: Path, payload: dict[str, Any], force: bool) -> None:
    refuse_existing(path, force)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def download_file(
    media: str,
    destination: Path,
    timeout: float,
    force: bool,
    *,
    label: str,
    fallback_suffix: str,
) -> Path:
    request = urllib.request.Request(media, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = response.read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"下载{label}失败：HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"下载{label}失败：{exc.reason}") from exc

    kind = content_type.split(";", 1)[0].strip().lower()
    if kind.startswith("text/") or kind in {"application/json", "application/xml"}:
        raise SystemExit(f"下载地址返回的不是{label}文件（{kind or 'unknown'}）。")
    if not payload:
        raise SystemExit(f"下载地址返回了空{label}。")

    target = destination
    if target.suffix == "":
        target = target.with_suffix(extension_for(content_type, media, fallback_suffix))
    refuse_existing(target, force)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target


def download_images(urls: list[str], directory: Path, timeout: float, force: bool) -> list[Path]:
    saved: list[Path] = []
    for index, url in enumerate(urls, start=1):
        saved.append(
            download_file(
                url,
                directory / f"{index:02d}",
                timeout,
                force,
                label="图片",
                fallback_suffix=".jpg",
            )
        )
    return saved


def dump_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="获取公开作品数据，并下载无水印视频和图文图片。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(command: argparse.ArgumentParser, timeout: int) -> None:
        command.add_argument("--video-url", required=True, help="公开视频的 http/https 链接")
        command.add_argument("--output", help="fetch 写入 JSON；download 写入视频文件，或在无视频时作为图片目录")
        command.add_argument("--force", action="store_true", help="覆盖已存在的输出文件")
        command.add_argument("--timeout", type=float, default=timeout)
        command.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
        command.add_argument("--retry-sleep-ms", type=int, default=DEFAULT_RETRY_SLEEP_MS)

    fetch = subparsers.add_parser("fetch", help="只获取播放和互动数据")
    add_common(fetch, DEFAULT_API_TIMEOUT)

    download = subparsers.add_parser("download", help="获取数据并下载无水印视频和图文图片")
    add_common(download, DEFAULT_DOWNLOAD_TIMEOUT)
    download.add_argument("--metadata", help="数据 JSON 路径；默认与视频文件同名")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    page_url = args.video_url.strip()
    if not is_http_url(page_url):
        raise SystemExit("videoUrl 必须是 http 或 https 链接。")

    data = fetch_material(
        page_url,
        timeout=args.timeout if args.command == "fetch" else DEFAULT_API_TIMEOUT,
        retries=args.retries,
        retry_sleep_ms=args.retry_sleep_ms,
    )
    chosen = media_url(data, page_url)
    payload = present(page_url, data, chosen)

    if args.command == "fetch":
        if args.output:
            write_json(Path(args.output), payload, args.force)
            payload = {**payload, "savedJson": str(Path(args.output))}
        dump_json(payload)
        return 0

    url, _field = chosen
    images = image_urls(data)
    note_id = str(data.get("videoId") or "material")
    if url is None and not images:
        dump_json(payload)
        raise SystemExit("接口已返回数据，但这次响应里没有可下载的视频直链或图片。")

    output = Path(args.output) if args.output else None
    saved_video: Path | None = None
    if url is None:
        directory = output if output is not None else Path(note_id)
        if directory.suffix:
            directory = directory.with_suffix("")
        metadata_path = Path(args.metadata) if args.metadata else directory / f"{note_id}.json"
    else:
        video_output = output if output is not None else Path(f"{note_id}.mp4")
        if video_output.suffix == "":
            video_output = video_output / f"{note_id}.mp4"
        if video_output.suffix:
            refuse_existing(video_output, args.force)
        metadata_path = Path(args.metadata) if args.metadata else video_output.with_suffix(".json")
        refuse_existing(metadata_path, args.force)
        saved_video = download_file(
            url,
            video_output,
            args.timeout,
            args.force,
            label="视频",
            fallback_suffix=".mp4",
        )
        if not args.metadata and saved_video != video_output:
            metadata_path = saved_video.with_suffix(".json")
            refuse_existing(metadata_path, args.force)
        directory = saved_video.parent / f"{saved_video.stem}-images"

    if url is None:
        refuse_existing(metadata_path, args.force)
    saved_images = download_images(images, directory, args.timeout, args.force) if images else []
    result = {
        **payload,
        "savedVideo": None if saved_video is None else str(saved_video),
        "savedImages": [str(path) for path in saved_images],
    }
    write_json(metadata_path, result, args.force)
    result["savedJson"] = str(metadata_path)
    dump_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
