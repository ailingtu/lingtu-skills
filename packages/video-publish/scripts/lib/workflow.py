"""Folder-first commands. Imports CLI lazily to keep the legacy entry point."""
from __future__ import annotations

from pathlib import Path

from .plan import (scan_media, build_media_rows, render_plan, read_json, write_json, batch_lock)


def command_plan(args):
    from . import cli
    source = Path(args.media_folder).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f'素材文件夹不存在：{source}')
    if not 1 <= args.count <= 7:
        raise SystemExit('每日条数需在 1～7 之间，以保证早晚排期不跨日。')
    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    with batch_lock(output):
        if any((output / name).exists() for name in ('schedule.csv', 'plan.json', 'publish-journal.json')):
            raise SystemExit('方案目录已有排期或记录，请修改原方案，或指定新目录。')
        groups = scan_media(source, args.media_type)
        if not groups:
            raise SystemExit('没有找到可发布的素材。')
        usernames = [name.strip().lstrip('@') for name in args.creators.split(',') if name.strip()]
        usernames = list(dict.fromkeys(name.lower() for name in usernames))
        if len(usernames) > 1 and not args.distribution:
            raise SystemExit('多个达人需明确素材分配：--distribution distribute（每份一次）或 all（每人全部）。')
        if args.media_type == 'photo' and args.platform not in ('tiktok_shop', 'tiktok_business'):
            raise SystemExit('图文只支持 tiktok_shop。')
        cli.require_api_key()
        info, missing = cli.resolve_creator_batch(usernames, platform=args.platform,
                                                  has_photo_permission=True if args.media_type == 'photo' and args.platform == 'tiktok_shop' else None)
        if missing:
            raise SystemExit('以下达人未授权或不满足权限，请处理后再生成方案：' + ', '.join(missing))
        if args.media_type == 'photo' and args.platform == 'tiktok_shop':
            for creator in info.values():
                ok, reason = cli.creator_can_publish_photo(creator)
                if not ok:
                    raise SystemExit(reason)
        product_title = args.product_title
        if args.platform == 'tiktok_shop' and args.product_id and not product_title:
            titles = {cli.sanitize_product_title(cli.find_product_title(name, args.product_id)) for name in usernames}
            if len(titles) == 1:
                product_title = titles.pop()
        timezone = cli.parse_timezone(args.timezone) if args.timezone else ''
        zones = cli._timezone_map_for_creators(usernames, info, timezone, args.region)
        preferred_times = None
        if args.times:
            import re
            preferred_times = [value.strip() for value in args.times.split(',')]
            if len(preferred_times) != args.count or len(set(preferred_times)) != len(preferred_times) or any(not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value) for value in preferred_times):
                raise SystemExit('--times需填写每日条数个互不重复的HH:MM时间')
            preferred_times.sort()
        existing_dates = {}
        if args.skip_existing_days:
            from .services import call_service
            from datetime import datetime
            from zoneinfo import ZoneInfo
            active = {'WAITING_SUBMIT', 'SUBMITTING', 'PRE_CHECK_SUBMITTING', 'PRE_CHECK', 'PRE_CHECK_PASSED', 'PENDING', 'PROCESSING', 'SCHEDULED'}
            for username in usernames:
                blocked = set()
                page = 1
                while True:
                    data = call_service('posts-list', {'creatorUsername': username, 'pageSize': 200, 'pageNumber': page}) or {}
                    records = data.get('list') or []
                    for record in records:
                        stamp = record.get('scheduledAt')
                        if record.get('status') in active and stamp:
                            try:
                                date = datetime.fromtimestamp(int(stamp) / 1000, ZoneInfo(zones[username])).strftime('%Y-%m-%d')
                            except (ValueError, TypeError, OverflowError) as exc:
                                raise SystemExit('已有排期时间无法解析，不能自动跳过日期') from exc
                            blocked.add(date)
                    if not records or page >= data.get('totalPages', (int(data.get('total', len(records))) + 199) // 200):
                        break
                    page += 1
                existing_dates[username] = blocked
        rows = build_media_rows(groups, usernames, distribution=args.distribution or 'distribute',
                                date=cli.parse_date_for_filename(args.date), count=args.count,
                                platform=args.platform, media_type=args.media_type,
                                timezone_by_creator=zones, title=args.title,
                                product_id=args.product_id, product_title=product_title,
                                preferred_times=preferred_times, existing_dates=existing_dates)
        cli.write_csv_schedule(str(output / 'schedule.csv'), rows,
                               columns=cli._csv_columns_for_platform(args.platform, args.media_type))
        write_json(output / 'plan.json', {'version': 1, 'source': str(source),
                                         'distribution': args.distribution or 'distribute',
                                         'preferredTimes': preferred_times, 'skipExistingDays': args.skip_existing_days})
        (output / '发布方案.md').write_text(render_plan(rows, args.distribution or 'distribute'), encoding='utf-8')
        cli.print_json({'folder': str(output), 'rows': len(rows), 'materials': len(groups),
                        'creators': usernames, 'distribution': args.distribution or 'distribute',
                        'preview': str(output / '发布方案.md'), 'state': 'draft',
                        'next': '补全草稿，运行 publish 校验并展示明细，用户确认后提交。'})


def command_status(args):
    from . import cli
    from .api import list_posts
    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        raise SystemExit('批次文件夹不存在。')
    with batch_lock(folder):
        journal_path = folder / 'publish-journal.json'
        journal = read_json(journal_path, {'entries': {}})
        if args.refresh:
            cli.require_api_key()
            for entry in journal['entries'].values():
                post_id = entry.get('post_id')
                if not post_id:
                    continue  # Unknown submission cannot safely be matched by caption.
                try:
                    records = list_posts(str(post_id))
                    record = next((r for r in records if str(r.get('postId')) == str(post_id)), None)
                    if record:
                        entry['post_status'] = record.get('status')
                        entry['reason'] = record.get('reason')
                        entry['platform_post_id'] = record.get('platformPostId')
                        entry.pop('refresh_error', None)
                    else:
                        entry['refresh_error'] = '未查到记录，保留原状态；不能据此重发。'
                except SystemExit as exc:
                    entry['refresh_error'] = str(exc)
                write_json(journal_path, journal)
        cli.print_json({'records_url': cli.PUBLISH_RECORDS_URL, 'entries': list(journal['entries'].values()),
                        'note': 'success 表示任务已提交；仅 SUCCESS / COMPLETED 表示平台成功，PRE_CHECK_PASSED 仅为预检通过。'})
