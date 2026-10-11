"""User-facing selection, configuration and task management commands."""
from __future__ import annotations
import json
from pathlib import Path

from . import api
from .plan import read_json, write_json, batch_lock
from .publish_options import parse_options, validate_scenario
from .services import OPERATIONS, call_service, validate_operation


def command_service(args):
    from .cli import print_json
    operation = args.operation
    params = read_json(Path(args.params_file).expanduser()) if args.params_file else {}
    if not isinstance(params, dict):
        raise SystemExit('参数文件必须为JSON对象')
    for attr, key in [('post_id', 'postId'), ('keyword', 'keyword'), ('region', 'region'),
                      ('language', 'language'), ('genre', 'genre'), ('country_code', 'countryCode'),
                      ('date_range', 'dateRange'), ('music_id', 'musicId'), ('search_query', 'searchQuery'),
                      ('page_token', 'pageToken'), ('search_id', 'searchId'), ('draft_id', 'draftId')]:
        value = getattr(args, attr, None)
        if value is not None:
            params[key] = value
    if operation in ('music-search', 'music-favorites', 'posts-list', 'draft-list', 'managers'):
        params.setdefault('pageSize', 20)
    if operation in ('music-favorites', 'posts-list', 'draft-list', 'managers'):
        params.setdefault('pageNumber', 1)
    if getattr(args, 'creator', None):
        platform = 'tiktok_business' if operation in ('music-trending', 'location-search') else getattr(args, 'platform', 'tiktok_shop')
        info = api.resolve_creator_id(args.creator, platform=platform)
        if not info or not info.get('id'):
            raise SystemExit('达人未找到或缺少账号主键，请先查询creators')
        params['id'] = info['id']
    if operation == 'music-favorites' and 'keyword' in params:
        params['title'] = params.pop('keyword')
    validate_operation(operation, params)
    method, path, _ = OPERATIONS[operation]
    if method == 'POST' and not args.confirm:
        print_json({'mode': 'dry-run', 'operation': operation, 'method': method, 'path': path, 'params': params,
                    'note': '向用户展示后确认再加--confirm执行；不会自动重试写操作。'})
        return
    result = call_service(operation, params)
    output = {'operation': operation, 'data': result}
    if args.output:
        write_json(Path(args.output).expanduser(), output)
    print_json(output)


def command_configure(args):
    from . import cli
    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        raise SystemExit('方案目录不存在')
    with batch_lock(folder):
        schedule = folder / 'schedule.csv'
        if not schedule.exists():
            raise SystemExit('发布设置编辑要求schedule.csv；旧XLSX先转换为CSV')
        rows = cli.parse_excel_or_csv(str(schedule))
        selected = [args.row] if args.row is not None else list(range(len(rows)))
        if not selected or any(index < 0 or index >= len(rows) for index in selected):
            raise SystemExit('行号超出范围')
        options = parse_options(read_json(Path(args.settings_file).expanduser()))
        for index in selected:
            validate_scenario(options, rows[index]['platform'], cli._row_media_type(rows[index]))
            rows[index]['publish_options'] = json.dumps(options, ensure_ascii=False, separators=(',', ':'))
        columns = cli.read_csv_columns(str(schedule))
        if 'publish_options' not in columns:
            columns.append('publish_options')
        cli.write_csv_schedule(str(schedule), rows, columns)
        (folder / 'review.json').unlink(missing_ok=True)
        cli.print_json({'updated': len(selected), 'settings': options, 'next': '重新预览并让用户确认设置'})


def add_commands(subparsers):
    p = subparsers.add_parser('configure', help='给方案逐条或全批设置音乐、封面、互动等')
    p.add_argument('--folder', required=True)
    p.add_argument('--row', type=int, help='0为第一条；不传应用到全批')
    p.add_argument('--settings-file', required=True, help='发布设置JSON对象；替换所选行的设置')
    p.set_defaults(func=command_configure)

    def common(p):
        p.add_argument('--params-file', help='完整参数JSON文件；其他选项覆盖同名字段')
        p.add_argument('--confirm', action='store_true')
        p.add_argument('--output', help='保存查询结果JSON')
        p.set_defaults(func=command_service)

    p = subparsers.add_parser('service', help='通过固定/v1接口管理账号、发布统计、云草稿或AI排期')
    p.add_argument('operation', choices=tuple(OPERATIONS))
    common(p)
    for group, operations in {
        'music': {'search': 'music-search', 'trending': 'music-trending', 'favorites': 'music-favorites',
                  'favorite': 'music-favorite', 'unfavorite': 'music-unfavorite'},
        'posts': {name: 'posts-' + name for name in ('list', 'detail', 'stats', 'daily', 'cancel', 'delete', 'submit', 'sync', 'update', 'reschedule', 'bind-video', 'to-library')},
        'draft': {name: 'draft-' + name for name in ('list', 'detail', 'create', 'update', 'rename', 'delete', 'complete')},
    }.items():
        p = subparsers.add_parser(group, help={'music': '搜索、试听链接、收藏和高级版热门音乐', 'posts': '查询、修改或管理服务端发布任务', 'draft': '管理网页兼容的云端草稿JSON'}[group])
        children = p.add_subparsers(dest='action', required=True)
        for name, operation in operations.items():
            c = children.add_parser(name)
            common(c)
            c.set_defaults(operation=operation)
            if group == 'music':
                c.add_argument('--creator')
                for flag in ('keyword', 'region', 'language', 'genre', 'country-code', 'date-range', 'music-id', 'page-token', 'search-id'):
                    c.add_argument('--' + flag)
            elif group == 'posts':
                c.add_argument('--post-id')
            else:
                c.add_argument('--draft-id')
    p = subparsers.add_parser('location', help='搜索高级版账号可用的地域标签')
    common(p)
    p.add_argument('--creator', required=True)
    p.add_argument('--search-query', required=True)
    p.set_defaults(operation='location-search')
    p = subparsers.add_parser('publish-config', help='查看账号当前发布能力')
    common(p)
    p.add_argument('--creator', required=True)
    p.add_argument('--platform', choices=('tiktok', 'tiktok_business'), default='tiktok')
    p.set_defaults(operation='publish-config')
    p = subparsers.add_parser('quota', help='查询本月可发布账号额度')
    common(p)
    p.set_defaults(operation='quota')
