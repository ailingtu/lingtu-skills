from __future__ import annotations
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lib import api, cli, services
from lib.publish_options import parse_options, validate_scenario, settings_from_config
from lib.plan import read_json


class ScenarioRequestTests(unittest.TestCase):
    def create(self, platform, media='VIDEO', **kwargs):
        with mock.patch.object(api, '_request_json', return_value={'data': {'postId': 'p1'}}) as request:
            api.create_post(creator_id='creator-gid', title='Caption 😀! #tag', business_id='100',
                            platform=platform, media_type=media, **kwargs)
            self.assertEqual(request.call_args.args, ('POST', '/v1/creator/post/create'))
            return request.call_args.kwargs['body']

    def test_shop_video_music_precheck_ai_and_zero_frame(self):
        body = self.create('tiktok_shop', product_id='p1', product_title='Name', product_source='SHOP',
                           options={'musicInfo': {'id': 'song', 'title': 'Tune'}, 'preCheck': True,
                                    'preCheckOvertime': 1800, 'isAiGenerated': True, 'coverTimestampMs': 0})
        self.assertEqual(body['title'], 'Caption 😀! #tag')
        self.assertEqual(body['tiktokShop']['musicInfo']['id'], 'song')
        self.assertEqual(body['tiktokShop']['coverTimestampMs'], 0)
        self.assertTrue(body['tiktokShop']['isAiGenerated'])
        self.assertNotIn('tiktokBusiness', body)

    def test_business_video_maps_sound_volumes_and_location(self):
        body = self.create('tiktok_business', options={
            'musicInfo': {'id': 'clip123', 'title': 'Tune', 'musicSoundVolume': 0, 'videoOriginalSoundVolume': 100},
            'locationInfo': {'locationId': 'loc', 'locationName': 'London'}, 'aigc': True})
        self.assertEqual(body['platform'], 'TIKTOK_BUSINESS')
        self.assertEqual(body['tiktokBusiness']['musicSoundInfo']['musicSoundId'], 'clip123')
        self.assertEqual(body['tiktokBusiness']['musicSoundInfo']['musicSoundVolume'], 0)
        self.assertNotIn('privacyLevel', body['tiktokBusiness'])
        self.assertNotIn('tiktokShop', body)

    def test_business_photo_integer_order_privacy_and_music(self):
        body = self.create('tiktok_business', 'PHOTO', business_ids=['102', '100'], options={
            'privacyLevel': 'SELF_ONLY', 'autoAddMusic': False, 'musicInfo': {'id': 'clip123'}})
        self.assertEqual(body['businessId'], '102')
        self.assertEqual(body['tiktokBusinessPhoto']['businessIds'], [102, 100])
        self.assertEqual(body['tiktokBusinessPhoto']['musicSoundInfo']['musicSoundId'], 'clip123')
        self.assertNotIn('tiktokShopPhoto', body)

    def test_business_photo_rejects_volumes_and_missing_privacy(self):
        for options in ({}, {'privacyLevel': 'SELF_ONLY', 'musicInfo': {'id': 'clip', 'musicSoundVolume': 50}}):
            with mock.patch.object(api, '_request_json') as request:
                with self.assertRaises(SystemExit):
                    api.create_post(creator_id='c', title='Caption', business_id='100',
                                    platform='tiktok_business', media_type='PHOTO', options=options)
                request.assert_not_called()

    def test_uploaded_shop_cover_not_frame(self):
        body = self.create('tiktok_shop', options={'coverFile': '/cover.jpg'},
                           cover={'coverFileId': '900', 'photoFile': {'photoUri': 'uri'}})
        self.assertEqual(body['coverFileId'], '900')
        self.assertEqual(body['tiktokShop']['coverUri'], 'uri')
        self.assertNotIn('coverTimestampMs', body['tiktokShop'])

    def test_login_rejects_music(self):
        with self.assertRaises(SystemExit):
            self.create('tiktok', options={'musicInfo': {'id': 'song'}})

    def test_shop_photo_rejects_video_fields(self):
        with self.assertRaises(SystemExit):
            self.create('tiktok_shop', 'PHOTO', product_id='p', product_source='SHOP',
                        options={'preCheck': True})

    def test_capability_default_and_forbidden_interaction(self):
        config = {'privacyLevelOptions': ['SELF_ONLY'], 'commentDisabled': True}
        result = settings_from_config({}, config, 'tiktok', 'video')
        self.assertEqual(result['privacyLevel'], 'SELF_ONLY')
        self.assertTrue(result['disableComment'])
        with self.assertRaises(SystemExit):
            settings_from_config({'privacyLevel': 'PUBLIC_TO_EVERYONE'}, config, 'tiktok', 'video')
        with self.assertRaises(SystemExit):
            settings_from_config({'disableComment': False}, config, 'tiktok', 'video')

    def test_settings_reject_invalid_types(self):
        for options in ({'musicInfo': {'id': 'a', 'musicSoundVolume': 101}},
                        {'locationInfo': {'locationId': 'loc'}}, {'preCheck': 'false'},
                        {'musicInfo': {'commercialMusicId': 'wrong'}}, {'coverTimestampMs': -1}):
            with self.assertRaises(SystemExit):
                parse_options(options)


class MigratedCommandTests(unittest.TestCase):
    def command(self, *args):
        parser = cli.build_parser()
        parsed = parser.parse_args(args)
        with redirect_stdout(io.StringIO()) as out:
            parsed.func(parsed)
        return json.loads(out.getvalue())

    def test_all_migrated_routes_use_v1(self):
        for _, path, _ in services.OPERATIONS.values():
            self.assertTrue(path.startswith('/v1/'))
            self.assertNotIn('/admin/', path)

    def test_music_search_account_primary_id_and_pagination(self):
        with mock.patch.object(api, 'resolve_creator_id', return_value={'id': '10', 'creatorId': 'gid'}), \
             mock.patch.object(api, '_request_json', return_value={'data': {'music': [], 'hasMore': False}}) as request:
            self.command('music', 'search', '--creator', 'alice', '--keyword', 'summer',
                         '--region', 'US', '--page-token', 'next', '--search-id', 'session')
        self.assertEqual(request.call_args.args[1], '/v1/creator/tiktokshop/searchMusic')
        params = request.call_args.kwargs['query_params']
        self.assertEqual(params['id'], '10')
        self.assertEqual(params['searchId'], 'session')

    def test_trending_uses_business_account(self):
        with mock.patch.object(api, 'resolve_creator_id', return_value={'id': '20'}) as resolve, \
             mock.patch.object(api, '_request_json', return_value={'data': {'music': []}}) as request:
            self.command('music', 'trending', '--creator', 'alice', '--country-code', 'GB', '--date-range', '30DAY')
        resolve.assert_called_once_with('alice', platform='tiktok_business')
        self.assertEqual(request.call_args.args[1], '/v1/creator/tiktokBusiness/trendingMusic')

    def test_task_mutation_preview_does_not_call_api(self):
        with mock.patch.object(api, '_request_json') as request:
            result = self.command('posts', 'cancel', '--post-id', 'p1')
            self.assertEqual(result['params']['postId'], 'p1')
            request.assert_not_called()

    def test_confirm_cancel_exact_task(self):
        with mock.patch.object(api, '_request_json', return_value={'data': None}) as request:
            self.command('posts', 'cancel', '--post-id', 'p1', '--confirm')
        self.assertEqual(request.call_args.args, ('POST', '/v1/creator/post/cancel'))
        self.assertEqual(request.call_args.kwargs['body'], {'postId': 'p1'})

    def test_reschedule_validates_window(self):
        with self.assertRaises(SystemExit):
            services.validate_operation('posts-reschedule', {'postIds': ['p1'], 'durationHours': 25})

    def test_cloud_draft_rejects_local_plan(self):
        params = {'title': 'Batch', 'publishTarget': 'TIKTOK_PRODUCT_VIDEO', 'resumeStep': 2,
                  'payload': {'version': 1}, 'fileIds': [], 'taskCount': 0, 'accountCount': 0}
        with self.assertRaises(SystemExit):
            services.validate_operation('draft-create', params)

    def test_configure_invalidation_and_case_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            csv = folder / 'schedule.csv'
            cli.write_csv_schedule(str(csv), [{'creator_username': 'alice', 'platform': 'tiktok_shop',
                'media_type': 'video', 'title': 'Caption', 'video_file': 'a.mp4'}],
                columns=cli._csv_columns_for_platform('tiktok_shop'))
            (folder / 'review.json').write_text('{}')
            settings = folder / 'options.json'
            settings.write_text(json.dumps({'musicInfo': {'id': 'song'}}))
            result = self.command('configure', '--folder', str(folder), '--row', '0', '--settings-file', str(settings))
            self.assertEqual(result['updated'], 1)
            self.assertFalse((folder / 'review.json').exists())
            row = cli.parse_excel_or_csv(str(csv))[0]
            self.assertEqual(json.loads(row['publish_options'])['musicInfo']['id'], 'song')

    def test_cover_multipart_uses_v1_and_key_header(self):
        import lingtu_http
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'cover.jpg'
            image.write_bytes(b'cover-bytes')
            with mock.patch.object(lingtu_http, 'auth_headers', return_value={'x-api-key': 'test'}), \
                 mock.patch.object(lingtu_http, 'request_bytes', return_value=(200, b'{"code":0,"data":{"coverFileId":"900","photoFile":{"photoUri":"uri"}}}')) as request:
                result = services.upload_cover('10', image)
                self.assertEqual(result['coverFileId'], '900')
            args = request.call_args
            self.assertTrue(args.args[1].endswith('/v1/creator/tiktokshop/uploadPhoto'))
            self.assertIn(b'name="returnCoverFileId"', args.kwargs['data'])
            self.assertIn(b'cover-bytes', args.kwargs['data'])


class MigrationIntegrationTests(unittest.TestCase):
    def test_business_folder_plan_settings_and_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / 'media'
            media.mkdir()
            (media / 'a.mp4').write_bytes(b'fake-video')
            batch = root / 'batch'
            settings = root / 'settings.json'
            settings.write_text(json.dumps({'musicInfo': {'id': 'clip', 'musicSoundVolume': 30}, 'aigc': True}))
            parser = cli.build_parser()
            def run(*args):
                parsed = parser.parse_args(args)
                with redirect_stdout(io.StringIO()):
                    parsed.func(parsed)
            with mock.patch.object(cli, 'require_api_key'), \
                 mock.patch.object(cli, 'resolve_creator_batch', return_value=({'alice': {'id': '10', 'creatorId': 'gid'}}, [])), \
                 mock.patch.object(cli, 'get_publish_config', return_value={'maxVideoPostDurationSec': 60}), \
                 mock.patch.object(cli, 'video_duration', return_value=10), \
                 mock.patch.object(cli, 'upload_file', return_value={'id': '100'}), \
                 mock.patch.object(api, '_request_json', return_value={'data': {'postId': 'p1'}}) as request:
                run('plan', '--media-folder', str(media), '--output-dir', str(batch), '--platform', 'tiktok_business',
                    '--creators', 'alice', '--date', '2099-10-12', '--count', '1', '--title', 'Caption 😀!')
                run('configure', '--folder', str(batch), '--settings-file', str(settings))
                run('publish', '--folder', str(batch))
                run('publish', '--folder', str(batch), '--confirm')
                body = request.call_args.kwargs['body']
                self.assertEqual(body['tiktokBusiness']['musicSoundInfo']['musicSoundId'], 'clip')
                self.assertTrue(body['tiktokBusiness']['aigc'])
                self.assertEqual(body['title'], 'Caption 😀!')
                self.assertEqual(next(iter(read_json(batch / 'publish-journal.json')['entries'].values()))['status'], 'success')

    def test_preferred_times_and_skip_existing_days(self):
        from lib.plan import build_media_rows
        rows = build_media_rows([[Path('/a.mp4')], [Path('/b.mp4')]], ['alice'], distribution='distribute',
                                date='2099-10-12', count=1, platform='tiktok', media_type='video',
                                timezone_by_creator={'alice': 'America/Los_Angeles'}, title='Caption',
                                product_id='', product_title='', preferred_times=['20:00'],
                                existing_dates={'alice': {'2099-10-12', '2099-10-14'}})
        self.assertEqual([row['scheduled_at'] for row in rows], ['2099-10-13 20:00', '2099-10-15 20:00'])

    def test_relay_accepts_openai_response_without_envelope(self):
        import lingtu_http
        with mock.patch.object(lingtu_http, 'request_json', return_value={'choices': [{'message': {'content': '{}'}}]}) as request:
            result = services.call_service('ai-schedule', {'model': 'model', 'messages': []})
            self.assertIn('choices', result)
            self.assertEqual(request.call_args.args[1], '/v1/relay/chat/completions')
            self.assertFalse(request.call_args.kwargs['expect_envelope'])

    def test_duration_failure_blocks_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a.mp4').write_bytes(b'fake-video')
            rows = [{'creator_username': 'alice', 'platform': 'tiktok_business', 'media_type': 'video',
                     'title': 'Caption', 'scheduled_at': '2099-10-12 10:00', 'timezone': 'America/Los_Angeles', 'video_file': 'a.mp4'}]
            cli.write_csv_schedule(str(root / 'schedule.csv'), rows, cli._csv_columns_for_platform('tiktok_business'))
            args = cli.build_parser().parse_args(['publish', '--folder', str(root)])
            with mock.patch.object(cli, 'resolve_creator_batch', return_value=({'alice': {'id': '10', 'creatorId': 'gid'}}, [])), \
                 mock.patch.object(cli, 'get_publish_config', return_value={'maxVideoPostDurationSec': 60}), \
                 mock.patch.object(cli, 'video_duration', return_value=61), \
                 mock.patch.object(cli, 'upload_file') as upload:
                with self.assertRaisesRegex(SystemExit, '超过账号限制'):
                    cli.command_publish(args)
                upload.assert_not_called()


if __name__ == '__main__':
    unittest.main()
