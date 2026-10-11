from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lib import cli, api, workflow
from lib.plan import scan_media, build_media_rows, read_json, write_json, batch_lock, row_fingerprint


class FolderWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.media = self.root / 'media'
        self.media.mkdir()
        for name in ('v10.mp4', 'v2.mp4', 'v1.mp4'):
            (self.media / name).write_bytes(name.encode())
        self.batch = self.root / 'batch'
        self.parser = cli.build_parser()
        self.resolver = mock.patch.object(cli, 'resolve_creator_batch', side_effect=lambda names, **kw:
            ({n.lower(): {'id': '10', 'creatorId': 'id-' + n, 'username': n} for n in names}, []))
        self.resolver.start()
        self.auth = mock.patch.object(cli, 'require_api_key', return_value='test')
        self.auth.start()
        config = mock.patch.object(cli, 'get_publish_config', return_value={'privacyLevelOptions': ['PUBLIC_TO_EVERYONE']})
        config.start()
        self.addCleanup(config.stop)
        self.addCleanup(self.resolver.stop)
        self.addCleanup(self.auth.stop)
        self.addCleanup(self.temp.cleanup)

    def run_cli(self, *args):
        parsed = self.parser.parse_args(args)
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
            parsed.func(parsed)
        return json.loads(out.getvalue()) if out.getvalue().lstrip().startswith('{') else out.getvalue()

    def plan(self):
        return self.run_cli('plan', '--media-folder', str(self.media), '--output-dir', str(self.batch),
                            '--platform', 'tiktok', '--creators', 'alice,bob', '--distribution', 'distribute',
                            '--date', '2099-10-12', '--count', '1', '--title', 'Caption')

    def publish(self, *extra):
        return self.run_cli('publish', '--folder', str(self.batch), '--sleep-ms', '0', '--format', 'json', *extra)

    def test_natural_order_distribution_and_no_copy(self):
        result = self.plan()
        rows = cli.parse_excel_or_csv(str(self.batch / 'schedule.csv'))
        self.assertEqual(result['rows'], 3)
        self.assertEqual([Path(r['video_file']).name for r in rows], ['v1.mp4', 'v2.mp4', 'v10.mp4'])
        self.assertEqual([r['creator_username'] for r in rows], ['alice', 'bob', 'alice'])
        self.assertTrue(rows[2]['scheduled_at'].startswith('2099-10-13'))
        self.assertFalse(list(self.batch.glob('*.mp4')))

    def test_all_explicitly_repeats_each_material(self):
        groups = scan_media(self.media, 'video')
        rows = build_media_rows(groups, ['alice', 'bob'], distribution='all', date='2099-10-12',
                                count=2, platform='tiktok', media_type='video',
                                timezone_by_creator={'alice': 'America/Los_Angeles', 'bob': 'America/Los_Angeles'},
                                title='Caption', product_id='', product_title='')
        self.assertEqual(len(rows), 6)
        self.assertEqual(len({r['video_file'] for r in rows}), 3)

    def test_ambiguous_root_photo_group_rejected(self):
        (self.media / 'p.jpg').write_bytes(b'image')
        with self.assertRaisesRegex(SystemExit, '分组不明确'):
            scan_media(self.media, 'photo')

    def test_confirm_requires_review_then_changed_file_rejected(self):
        self.plan()
        with mock.patch.object(cli, 'upload_file') as upload:
            with self.assertRaisesRegex(SystemExit, '重新运行 publish'):
                self.publish('--confirm')
            self.publish()
            (self.media / 'v1.mp4').write_bytes(b'changed')
            with self.assertRaisesRegex(SystemExit, '重新运行 publish'):
                self.publish('--confirm')
            upload.assert_not_called()

    def test_changed_creator_requires_new_review(self):
        self.plan()
        self.publish()
        with mock.patch.object(cli, 'resolve_creator_batch', return_value=(
                {'alice': {'id': '10', 'creatorId': 'changed'}, 'bob': {'id': '11', 'creatorId': 'id-bob'}}, [])), \
             mock.patch.object(cli, 'upload_file') as upload:
            with self.assertRaisesRegex(SystemExit, '重新运行 publish'):
                self.publish('--confirm')
            upload.assert_not_called()

    def test_changed_caption_invalidates_review(self):
        self.plan()
        self.publish()
        self.run_cli('fill', '--folder', str(self.batch), '--col', 'title', '--row', '0', '--value', 'Changed')
        with mock.patch.object(cli, 'upload_file') as upload:
            with self.assertRaisesRegex(SystemExit, '重新运行 publish'):
                self.publish('--confirm')
            upload.assert_not_called()

    def test_previous_version_journal_still_blocks_duplicate(self):
        self.plan()
        rows = cli.parse_excel_or_csv(str(self.batch / 'schedule.csv'))
        legacy_entries = {}
        for row in rows:
            fingerprint = row_fingerprint(row, self.batch, [row['video_file']])
            legacy_entries[fingerprint] = {'status': 'success', 'post_id': 'old-post'}
        write_json(self.batch / 'publish-journal.json', {'entries': legacy_entries})
        self.publish()
        with mock.patch.object(cli, 'upload_file') as upload, mock.patch.object(cli, 'create_post') as create:
            self.assertEqual(self.publish('--confirm')['skipped_count'], 3)
            upload.assert_not_called()
            create.assert_not_called()

    def test_repeated_confirm_does_not_upload_or_create_again(self):
        self.plan()
        self.publish()
        with mock.patch.object(cli, 'upload_file', return_value={'id': 'f1'}) as upload, \
             mock.patch.object(cli, 'create_post', return_value={'postId': 'p1', 'status': 'PENDING'}) as create:
            first = self.publish('--confirm')
            second = self.publish('--confirm')
            self.assertEqual(first['succeeded'], 3)
            self.assertEqual(second['skipped_count'], 3)
            self.assertEqual(upload.call_count, 3)
            self.assertEqual(create.call_count, 3)
        self.assertEqual(len(read_json(self.batch / 'publish-journal.json')['entries']), 3)

    def test_unknown_submission_never_retried(self):
        self.plan()
        self.publish()
        with mock.patch.object(cli, 'upload_file', return_value={'id': 'f1'}), \
             mock.patch.object(cli, 'create_post', side_effect=SystemExit('timeout')) as create:
            with self.assertRaises(SystemExit):
                self.publish('--confirm')
            second = self.publish('--confirm', '--retry-failed')
            self.assertEqual(second['skipped_count'], 3)
            self.assertEqual(create.call_count, 3)
        self.assertEqual({v['status'] for v in read_json(self.batch / 'publish-journal.json')['entries'].values()}, {'unknown'})

    def test_interruption_keeps_intent_and_blocks_duplicate(self):
        self.plan()
        self.publish()
        with mock.patch.object(cli, 'upload_file', return_value={'id': 'f1'}), \
             mock.patch.object(cli, 'create_post', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.publish('--confirm')
        entries = read_json(self.batch / 'publish-journal.json')['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(next(iter(entries.values()))['status'], 'unknown')
        with mock.patch.object(cli, 'upload_file', return_value={'id': 'f1'}), \
             mock.patch.object(cli, 'create_post', return_value={'postId': 'p2'}) as create:
            result = self.publish('--confirm')
            self.assertEqual(result['skipped_count'], 1)
            self.assertEqual(create.call_count, 2)

    def test_missing_task_id_is_unknown(self):
        self.plan()
        self.publish()
        with mock.patch.object(cli, 'upload_file', return_value={'id': 'f1'}), \
             mock.patch.object(cli, 'create_post', return_value={'id': 123}):
            with self.assertRaises(SystemExit):
                self.publish('--confirm')
        entries = read_json(self.batch / 'publish-journal.json')['entries']
        self.assertEqual({v['status'] for v in entries.values()}, {'unknown'})

    def test_concurrent_batch_lock_rejected(self):
        self.batch.mkdir()
        with batch_lock(self.batch):
            with self.assertRaises(SystemExit):
                with batch_lock(self.batch):
                    self.fail('second publisher acquired lock')

    def test_retry_only_upload_failure(self):
        self.plan()
        self.publish()
        with mock.patch.object(cli, 'upload_file', side_effect=SystemExit('upload failed')), \
             mock.patch.object(cli, 'create_post') as create:
            with self.assertRaises(SystemExit):
                self.publish('--confirm')
            create.assert_not_called()
        with mock.patch.object(cli, 'upload_file', return_value={'id': 'f1'}), \
             mock.patch.object(cli, 'create_post', return_value={'postId': 'p1'}):
            self.assertEqual(self.publish('--confirm')['skipped_count'], 3)
            self.assertEqual(self.publish('--confirm', '--retry-failed')['succeeded'], 3)

    def test_status_refresh_exact_id_retains_failed_query(self):
        self.batch.mkdir()
        write_json(self.batch / 'publish-journal.json', {'entries': {
            'a': {'status': 'success', 'post_id': 'p1', 'post_status': 'PENDING'},
            'b': {'status': 'unknown'}}})
        with mock.patch.object(api, 'list_posts', return_value=[{'postId': 'p1', 'status': 'PRE_CHECK_PASSED'}]) as posts:
            result = self.run_cli('status', '--folder', str(self.batch), '--refresh')
            posts.assert_called_once_with('p1')
            self.assertEqual(result['entries'][0]['post_status'], 'PRE_CHECK_PASSED')
        with mock.patch.object(api, 'list_posts', side_effect=SystemExit('network error')):
            result = self.run_cli('status', '--folder', str(self.batch), '--refresh')
            self.assertEqual(result['entries'][0]['post_status'], 'PRE_CHECK_PASSED')
            self.assertIn('refresh_error', result['entries'][0])

    def test_csv_auto_title_exact_product(self):
        self.plan()
        self.run_cli('fill', '--folder', str(self.batch), '--col', 'platform', '--value', 'tiktok_shop')
        # Use a shop CSV because non-shopping templates intentionally omit product columns.
        rows = cli.parse_excel_or_csv(str(self.batch / 'schedule.csv'))
        for row in rows:
            row.update(product_id='p1', product_title='', product_source='SHOWCASE')
        cli.write_csv_schedule(str(self.batch / 'schedule.csv'), rows, cli._csv_columns_for_platform('tiktok_shop'))
        with mock.patch.object(cli, 'find_product_title', return_value='Product Name') as lookup:
            result = self.run_cli('fill', '--folder', str(self.batch), '--col', 'product_title',
                                  '--auto-product-title', '--format', 'json')
            self.assertEqual(result['updated'], 3)
            self.assertEqual(lookup.call_count, 2)
            self.assertEqual(cli.parse_excel_or_csv(str(self.batch / 'schedule.csv'))[0]['product_title'], 'Product Name')


class ApiPaginationTests(unittest.TestCase):
    def test_creator_pages_preserve_filters(self):
        with mock.patch.object(api, '_request_json', side_effect=[
            {'data': {'list': [{'username': 'a'}], 'totalPages': 2}},
            {'data': {'list': [{'username': 'b'}], 'totalPages': 2}},
        ]) as request:
            result = api.list_creator_accounts(platform='tiktok_shop', has_photo_permission=True)
            self.assertEqual(len(result['data']['list']), 2)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args.kwargs['query_params']['hasPhotoPermission'], 'true')

    def test_product_title_reads_next_page_by_id(self):
        with mock.patch.object(api, 'resolve_creator_id', return_value={'id': '10'}), \
             mock.patch.object(api, 'list_shop_products', side_effect=[
                 {'data': {'products': [{'id': 'wrong', 'title': 'Wrong'}], 'nextPageToken': 'next'}},
                 {'data': {'products': [{'id': 'p1', 'title': 'Correct'}]}},
             ]) as products:
            self.assertEqual(api.find_product_title('alice', 'p1'), 'Correct')
            self.assertEqual(products.call_args.kwargs['page_token'], 'next')


if __name__ == '__main__':
    unittest.main()
