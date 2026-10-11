"""Local publishing plans, content fingerprints and durable submission journal."""
from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm', '.avi', '.mkv'}
PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.bmp'}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise SystemExit(f'无法读取 {path}，请保留记录并修复文件：{exc}') from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2))
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


@contextmanager
def batch_lock(folder: Path):
    """OS lock releases after interruption; lock file intentionally remains."""
    path = folder / '.publish.lock'
    handle = path.open('a+b')
    try:
        try:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise SystemExit('此批次正在执行，请等待当前操作完成。') from exc
        except OSError as exc:
            raise SystemExit('此批次正在执行，请等待当前操作完成。') from exc
        yield
    finally:
        handle.close()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def row_fingerprint(row: dict, folder: Path, media_names: list[str]) -> str:
    # Include resolved paths and actual content: replacing a file invalidates review.
    files = [{'path': str((folder / name).resolve()), 'sha256': file_digest(folder / name)}
             for name in media_names]
    payload = {'row': row, 'files': files}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', str(path))]


def scan_media(folder: Path, media_type: str) -> list[list[Path]]:
    """Video = one file; photo = one immediate subfolder. Never guess root grouping."""
    if media_type == 'video':
        files = sorted((p for p in folder.rglob('*') if p.is_file()
                        and p.suffix.lower() in VIDEO_EXTENSIONS), key=natural_key)
        return [[p.resolve()] for p in files]
    root_images = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in PHOTO_EXTENSIONS]
    if root_images:
        raise SystemExit('根目录图片分组不明确，请先确认图文分组，每篇放入一个子文件夹。')
    groups = []
    for sub in sorted((p for p in folder.iterdir() if p.is_dir()), key=natural_key):
        images = sorted((p.resolve() for p in sub.iterdir() if p.is_file()
                         and p.suffix.lower() in PHOTO_EXTENSIONS), key=natural_key)
        if images:
            groups.append(images)
    return groups


def build_media_rows(groups: list[list[Path]], creators: list[str], *, distribution: str,
                     date: str, count: int, platform: str, media_type: str,
                     timezone_by_creator: dict, title: str, product_id: str,
                     product_title: str, preferred_times: list[str] | None = None,
                     existing_dates: dict[str, set[str]] | None = None) -> list[dict]:
    from .scheduler import compute_schedule_times, creator_offset_minutes
    if not groups or not creators or count < 1:
        raise SystemExit('素材、达人不能为空，每日条数必须大于 0。')
    assignments = [(i % len(creators), group) for i, group in enumerate(groups)]
    if distribution == 'all':
        assignments = [(i, group) for i in range(len(creators)) for group in groups]
    used = [0] * len(creators)
    start = datetime.strptime(date, '%Y-%m-%d')
    rows = []
    effective_days = {}
    for creator_index, group in assignments:
        creator = creators[creator_index]
        position = used[creator_index]
        day_index = position // count
        day = effective_days.get((creator, day_index))
        if day is None:
            previous = effective_days.get((creator, day_index - 1))
            day = previous + timedelta(days=1) if previous else start
            blocked = (existing_dates or {}).get(creator.lower(), set())
            while f'{day:%Y-%m-%d}' in blocked:
                day += timedelta(days=1)
            effective_days[(creator, day_index)] = day
        times = preferred_times or compute_schedule_times(count, creator_offset_minutes(creator_index))
        used[creator_index] += 1
        # Separator cannot safely represent filenames containing commas.
        if any(',' in str(p) for p in group):
            raise SystemExit('素材路径含英文逗号，请重命名后生成方案。')
        rows.append({
            'creator_username': creator, 'platform': platform, 'media_type': media_type,
            'title': title, 'product_id': product_id if platform == 'tiktok_shop' else '',
            'product_title': product_title if platform == 'tiktok_shop' else '',
            'product_source': 'SHOP' if platform == 'tiktok_shop' else '',
            'timezone': timezone_by_creator[creator.lower()],
            'scheduled_at': f'{day:%Y-%m-%d} {times[position % count]}',
            'video_file': str(group[0]) if media_type == 'video' else '',
            'image_files': ','.join(str(p) for p in group) if media_type == 'photo' else '',
        })
    return rows


def render_plan(rows: list[dict], distribution: str) -> str:
    def cell(value):
        return str(value or '').replace('|', '\\|').replace('\n', ' ')
    lines = ['# 发布方案', '', f'共 {len(rows)} 条。素材分配：'
             + ('每个达人都发全部素材。' if distribution == 'all' else '素材依次分配给达人，每份只发一次。'),
             '', '文案、商品或媒体缺失时仍为草稿；确认前必须运行校验。', '',
             '| 行 | 达人 | 素材 | 文案 | 商品 / 购物车标题 | 当地时间 | 时区 | 发布设置 |',
             '|---|---|---|---|---|---|---|---|']
    for i, row in enumerate(rows):
        names = (row.get('video_file') or row.get('image_files') or '').split(',')
        media = ' '.join(f'[{Path(name).name}](<{name}>)' for name in names if name)
        values = [i + 1, row['creator_username'], media,
                  row.get('title'), f"{row.get('product_id', '')} / {row.get('product_title', '')}",
                  row.get('scheduled_at'), row.get('timezone'), json.dumps(row.get('_options', row.get('publish_options', '')), ensure_ascii=False)]
        lines.append('| ' + ' | '.join(cell(v) for v in values) + ' |')
    return '\n'.join(lines) + '\n'
