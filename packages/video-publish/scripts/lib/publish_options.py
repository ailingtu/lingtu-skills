"""Five publishing scenarios: validate settings and map them to API bodies."""
from __future__ import annotations
import json
import subprocess
import shutil
from pathlib import Path
from typing import Any

BOOL_FIELDS = {'preCheck', 'isAiGenerated', 'aigc', 'disableComment', 'disableDuet',
               'disableStitch', 'brandContentToggle', 'brandOrganicToggle', 'autoAddMusic', 'publishImmediately'}
ALLOWED = BOOL_FIELDS | {'preCheckOvertime', 'privacyLevel', 'coverTimestampMs', 'coverFile', 'musicInfo', 'locationInfo'}
PRIVACY = {'PUBLIC_TO_EVERYONE', 'MUTUAL_FOLLOW_FRIENDS', 'FOLLOWER_OF_CREATOR', 'SELF_ONLY'}


def parse_options(raw: str | dict | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (ValueError, TypeError) as exc:
        raise SystemExit('发布设置必须是 JSON 对象') from exc
    if not isinstance(value, dict) or set(value) - ALLOWED:
        message = '发布设置含未知字段：' + ', '.join(sorted(set(value) - ALLOWED)) if isinstance(value, dict) else '发布设置必须是对象'
        raise SystemExit(message)
    for key in BOOL_FIELDS & value.keys():
        if not isinstance(value[key], bool):
            raise SystemExit(f'{key} 必须为布尔值')
    if 'privacyLevel' in value and value['privacyLevel'] not in PRIVACY:
        raise SystemExit('privacyLevel 无效')
    if 'coverTimestampMs' in value and (type(value['coverTimestampMs']) is not int or value['coverTimestampMs'] < 0):
        raise SystemExit('截帧时间必须为非负整数毫秒，0是有效值')
    if value.get('preCheckOvertime') not in (None, 1800):
        raise SystemExit('预审超时只支持 null 或 1800 秒')
    if value.get('coverFile') and not isinstance(value['coverFile'], str):
        raise SystemExit('coverFile 必须为本地文件路径')
    music = value.get('musicInfo')
    if music is not None:
        allowed_music = {'id', 'title', 'author', 'duration', 'musicSoundVolume', 'videoOriginalSoundVolume'}
        if not isinstance(music, dict) or set(music) - allowed_music or not str(music.get('id') or '').strip():
            raise SystemExit('musicInfo 需要发布用 id，仅支持曲目信息和音量；不能使用 commercialMusicId')
        for key in ('musicSoundVolume', 'videoOriginalSoundVolume'):
            if key in music and (type(music[key]) not in (int, float) or not 0 <= music[key] <= 100):
                raise SystemExit(f'{key} 必须在0～100之间')
    location = value.get('locationInfo')
    if location is not None:
        if not isinstance(location, dict) or set(location) - {'locationId', 'locationName', 'locationAddress'}:
            raise SystemExit('locationInfo 格式无效')
        if not str(location.get('locationId') or '').strip() or not str(location.get('locationName') or '').strip():
            raise SystemExit('地域ID和名称必须成对填写')
    return value


def validate_scenario(options: dict, platform: str, media: str) -> None:
    if platform == 'tiktok' and media == 'photo':
        raise SystemExit('Login Kit 不支持图文，请使用 tiktok_business')
    allowed = {'publishImmediately'}
    if platform == 'tiktok_shop' and media == 'video':
        allowed |= {'preCheck', 'preCheckOvertime', 'isAiGenerated', 'coverFile', 'coverTimestampMs', 'musicInfo'}
    elif platform == 'tiktok_shop':
        allowed |= {'musicInfo'}
    elif platform == 'tiktok':
        allowed |= {'privacyLevel', 'coverTimestampMs', 'disableComment', 'disableDuet', 'disableStitch', 'brandContentToggle', 'brandOrganicToggle', 'aigc'}
    elif platform == 'tiktok_business':
        allowed |= {'disableComment', 'brandContentToggle', 'brandOrganicToggle', 'musicInfo', 'locationInfo'}
        allowed |= {'privacyLevel', 'autoAddMusic'} if media == 'photo' else {'coverFile', 'coverTimestampMs', 'disableDuet', 'disableStitch', 'aigc'}
    if set(options) - allowed:
        raise SystemExit('此发布场景不支持设置：' + ', '.join(sorted(set(options) - allowed)))
    music = options.get('musicInfo') or {}
    if (platform != 'tiktok_business' or media == 'photo') and any(k in music for k in ('musicSoundVolume', 'videoOriginalSoundVolume')):
        raise SystemExit('音乐和原声音量仅用于高级版视频')
    if options.get('coverFile') and 'coverTimestampMs' in options:
        raise SystemExit('上传封面和截帧只能选一种')


def settings_from_config(options: dict, config: dict, platform: str, media: str) -> dict:
    result = dict(options)
    if platform == 'tiktok' or media == 'photo':
        choices = config.get('privacyLevelOptions') or []
        if not choices:
            raise SystemExit('账号没有可用隐私范围，不能发布')
        privacy = result.get('privacyLevel') or choices[0]
        if privacy not in choices:
            raise SystemExit('账号不允许此隐私范围，请重新选择')
        result['privacyLevel'] = privacy
    for option, flag in (('disableComment', 'commentDisabled'), ('disableDuet', 'duetDisabled'), ('disableStitch', 'stitchDisabled')):
        if media == 'photo' and option != 'disableComment':
            continue
        if config.get(flag):
            if result.get(option) is False:
                raise SystemExit(f'账号已禁止此互动，{option} 不能设为 false')
            result[option] = True
    return result


def video_duration(path: Path) -> float | None:
    executable = shutil.which('ffprobe')
    if not executable:
        return None
    try:
        result = subprocess.run([executable, '-v', 'error', '-show_entries', 'format=duration',
                                 '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                                capture_output=True, text=True, timeout=30, check=True)
        return float(result.stdout.strip())
    except (ValueError, subprocess.SubprocessError):
        return None


def apply_options(body: dict, options: dict, platform: str, media: str, *, cover: dict | None = None) -> dict:
    options = parse_options(options)
    validate_scenario(options, platform, media)
    key = {('tiktok_shop', 'video'): 'tiktokShop', ('tiktok_shop', 'photo'): 'tiktokShopPhoto',
           ('tiktok', 'video'): 'tiktok', ('tiktok_business', 'video'): 'tiktokBusiness',
           ('tiktok_business', 'photo'): 'tiktokBusinessPhoto'}[(platform, media)]
    target = body.setdefault(key, {})
    for field in ALLOWED - {'coverFile', 'musicInfo', 'locationInfo', 'publishImmediately'}:
        if field in options:
            target[field] = options[field]
    music = options.get('musicInfo')
    if music:
        if platform == 'tiktok_business':
            target['musicSoundInfo'] = {'musicSoundId': str(music['id']),
                                        'musicSoundName': str(music.get('title') or ''),
                                        'musicSoundArtist': str(music.get('author') or '')}
            if media == 'video':
                for field in ('musicSoundVolume', 'videoOriginalSoundVolume'):
                    if field in music:
                        target['musicSoundInfo'][field] = music[field]
        else:
            target['musicInfo'] = {field: str(music.get(field) or '') for field in ('id', 'title', 'author', 'duration')}
    if options.get('locationInfo'):
        target['locationInfo'] = dict(options['locationInfo'])
    if cover:
        if not cover.get('coverFileId'):
            raise SystemExit('上传封面未返回 coverFileId')
        body['coverFileId'] = cover['coverFileId']
        if platform == 'tiktok_shop':
            uri = (cover.get('photoFile') or {}).get('photoUri')
            if not uri:
                raise SystemExit('Shop封面未返回photoUri')
            target['coverUri'] = uri
        target.pop('coverTimestampMs', None)
    return body
