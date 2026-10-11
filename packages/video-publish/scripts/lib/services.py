"""Migrated frontend endpoints; all use /v1 and the shared x-api-key client."""
from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path

from . import api

# method, path, required fields. No arbitrary URL forwarding or admin fallback.
OPERATIONS = {
    'music-search': ('GET', '/v1/creator/tiktokshop/searchMusic', ('id', 'keyword', 'pageSize')),
    'music-trending': ('GET', '/v1/creator/tiktokBusiness/trendingMusic', ('id',)),
    'music-favorites': ('GET', '/v1/creator/tiktokshop/music/favorites', ()),
    'music-favorite': ('POST', '/v1/creator/tiktokshop/music/favorite', ('musicId',)),
    'music-unfavorite': ('POST', '/v1/creator/tiktokshop/music/unfavorite', ('musicId',)),
    'location-search': ('GET', '/v1/creator/tiktokBusiness/searchLocation', ('id', 'searchQuery')),
    'publish-config': ('GET', '/v1/creatorAccount/tiktok/publishConfig', ('id',)),
    'quota': ('GET', '/v1/creator/post/monthlyAccountQuota', ()),
    'account-sync': ('POST', '/v1/creatorAccount/sync', ('id',)),
    'managers': ('GET', '/v1/businessManager/pageList', ('pageNumber', 'pageSize')),
    'showcase-add': ('POST', '/v1/creator/tiktokshop/product/addToShowcase', ('id', 'addType')),
    'posts-list': ('GET', '/v1/creator/post/pageList', ('pageNumber', 'pageSize')),
    'posts-detail': ('GET', '/v1/creator/post/detail', ('postId',)),
    'posts-stats': ('GET', '/v1/creator/post/stats', ()),
    'posts-daily': ('GET', '/v1/creator/post/stats/dailyAccount', ()),
    'posts-cancel': ('POST', '/v1/creator/post/cancel', ('postId',)),
    'posts-delete': ('POST', '/v1/creator/post/delete', ('postId',)),
    'posts-submit': ('POST', '/v1/creator/post/submit', ('postId',)),
    'posts-sync': ('POST', '/v1/creator/post/sync', ('postId',)),
    'posts-update': ('POST', '/v1/creator/post/update', ('postId', 'title', 'scheduledAt', 'scheduledTz')),
    'posts-reschedule': ('POST', '/v1/creator/post/reschedule', ('postIds',)),
    'posts-bind-video': ('POST', '/v1/creator/post/bindVideoId', ('postId', 'videoUrl')),
    'posts-to-library': ('POST', '/v1/creator/post/toLibrary', ('postId', 'shopId')),
    'draft-list': ('GET', '/v1/creator/postDraft/pageList', ('pageNumber', 'pageSize')),
    'draft-detail': ('GET', '/v1/creator/postDraft/detail', ('draftId',)),
    'draft-create': ('POST', '/v1/creator/postDraft/create', ('title', 'publishTarget', 'resumeStep', 'payload', 'fileIds', 'taskCount', 'accountCount')),
    'draft-update': ('POST', '/v1/creator/postDraft/update', ('draftId', 'lockVersion', 'title', 'publishTarget', 'resumeStep', 'payload', 'fileIds', 'taskCount', 'accountCount')),
    'draft-rename': ('POST', '/v1/creator/postDraft/rename', ('draftId', 'lockVersion', 'title')),
    'draft-delete': ('POST', '/v1/creator/postDraft/delete', ('draftId', 'lockVersion')),
    'draft-complete': ('POST', '/v1/creator/postDraft/complete', ('draftId', 'lockVersion', 'title', 'publishTarget', 'resumeStep', 'payload', 'fileIds', 'taskCount', 'accountCount')),
    'ai-schedule': ('POST', '/v1/relay/chat/completions', ('model', 'messages')),
}


def validate_operation(operation: str, params: dict) -> None:
    if not isinstance(params, dict):
        raise SystemExit('参数文件必须为JSON对象')
    required = OPERATIONS[operation][2]
    missing = [key for key in required if params.get(key) is None or params.get(key) == '']
    if missing:
        raise SystemExit('缺少参数：' + ', '.join(missing))
    if operation == 'posts-reschedule':
        if not isinstance(params['postIds'], list) or not params['postIds']:
            raise SystemExit('postIds 必须是非空数组')
        hours = params.get('durationHours')
        if hours is not None and (type(hours) is not int or not 1 <= hours <= 24):
            raise SystemExit('durationHours 必须为1～24小时')
    if operation == 'showcase-add':
        if params['addType'] == 'PRODUCT_ID':
            ids = params.get('productIds')
            if not isinstance(ids, list) or not 1 <= len(ids) <= 20:
                raise SystemExit('productIds 必须含1～20个商品ID')
        elif params['addType'] == 'PRODUCT_LINK':
            if not params.get('productLink'):
                raise SystemExit('缺少productLink')
        else:
            raise SystemExit('addType 必须为 PRODUCT_ID 或 PRODUCT_LINK')
    if operation in ('draft-create', 'draft-update', 'draft-complete'):
        payload = params['payload']
        if not isinstance(payload, dict) or type(payload.get('schemaVersion')) is not int or payload['schemaVersion'] != 1:
            raise SystemExit('只支持完整网页草稿V1，不支持本地plan.json或未知版本')
        for key in ('accountSelections', 'publishTasks', 'unassignedMedia'):
            if not isinstance(payload.get(key), list):
                raise SystemExit(f'网页草稿缺少数组 {key}')
        if not isinstance(payload.get('scheduleSettings'), dict) or 'lastAiScheduleResult' not in payload:
            raise SystemExit('网页草稿缺少排期设置或AI结果')
        if params['resumeStep'] not in (2, 3):
            raise SystemExit('resumeStep 必须为2或3')
        if params['taskCount'] != len(payload['publishTasks']):
            raise SystemExit('taskCount 与草稿任务数不一致')
    if operation == 'posts-update':
        from .excel_utils import parse_timezone
        if not str(params['title']).strip() or type(params['scheduledAt']) is not int:
            raise SystemExit('修改任务需要非空文案和整数毫秒时间')
        parse_timezone(params['scheduledTz'])
        scenario_keys = {'tiktokShop', 'tiktokShopPhoto', 'tiktok', 'tiktokBusiness', 'tiktokBusinessPhoto'} & params.keys()
        if len(scenario_keys) > 1:
            raise SystemExit('更新任务不能混用不同发布场景配置')
    if operation.startswith('draft-') and 'lockVersion' in params and (type(params['lockVersion']) is not int or params['lockVersion'] < 0):
        raise SystemExit('lockVersion 必须为非负整数，不能猜测或自动覆盖')
    if operation == 'music-trending' and params.get('dateRange', '7DAY') not in ('1DAY', '7DAY', '30DAY', '90DAY'):
        raise SystemExit('dateRange 无效')
    if operation == 'ai-schedule' and params.get('stream'):
        raise SystemExit('CLI排期接口仅支持stream=false，请保存JSON结果后审核，不自动套用')
    forbidden = {'LINGTU_API_KEY', 'apiKey', 'x-api-key', 'Authorization', 'token'} & params.keys()
    if forbidden:
        raise SystemExit('参数文件不得包含认证凭据')


def call_service(operation: str, params: dict):
    validate_operation(operation, params)
    method, path, _ = OPERATIONS[operation]
    if operation == 'ai-schedule':
        from lingtu_http import request_json, LingtuHttpError, raise_system_exit
        try:
            result = request_json('POST', path, body={**params, 'stream': False}, expect_envelope=False)
        except LingtuHttpError as exc:
            raise_system_exit(exc)
        if not isinstance(result, dict) or ('code' in result and result['code'] != 0):
            raise SystemExit('AI排期请求失败')
        completion = result.get('data') if result.get('code') == 0 else result
        if not isinstance(completion, dict) or not isinstance(completion.get('choices'), list):
            raise SystemExit('AI排期响应缺少choices，不能应用到方案')
        return completion
    result = api._request_json(method, path, query_params=params if method == 'GET' else None,
                               body=params if method == 'POST' else None)
    return result.get('data')


def upload_cover(account_id: str, path: Path) -> dict:
    from lingtu_http import auth_headers, build_url, request_bytes, LingtuHttpError, raise_system_exit
    if not path.is_file():
        raise SystemExit(f'封面文件不存在：{path}')
    boundary = 'lingtu-' + uuid.uuid4().hex
    chunks = []
    for key, value in (('id', account_id), ('returnCoverFileId', 'true')):
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    # Avoid header injection through local names.
    name = path.name.replace('"', '_').replace('\r', '_').replace('\n', '_')
    ct = mimetypes.guess_type(path.name)[0] or 'image/jpeg'
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: {ct}\r\n\r\n'.encode())
    chunks.extend([path.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()])
    try:
        _, raw = request_bytes('POST', build_url(api.base_url(), '/v1/creator/tiktokshop/uploadPhoto'),
                               headers=auth_headers(content_type=f'multipart/form-data; boundary={boundary}'),
                               data=b''.join(chunks), timeout=600)
    except LingtuHttpError as exc:
        raise_system_exit(exc)
    try:
        result = json.loads(raw)
    except ValueError as exc:
        raise SystemExit('封面接口响应不是JSON') from exc
    if not isinstance(result, dict) or result.get('code') != 0 or not isinstance(result.get('data'), dict):
        raise SystemExit('上传封面失败：' + str(result.get('message') if isinstance(result, dict) else '响应格式错误'))
    return result['data']


def get_publish_config(account_id: str) -> dict:
    result = call_service('publish-config', {'id': account_id})
    if not isinstance(result, dict):
        raise SystemExit('发布配置响应无效')
    return result
