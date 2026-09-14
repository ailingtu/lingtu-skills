import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
from email.message import Message
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/lingtu_video_understand.py'
spec = importlib.util.spec_from_file_location('video_understand', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def response(body, content_type='text/event-stream'):
    result = io.BytesIO(body)
    result.headers = Message()
    result.headers['Content-Type'] = content_type
    return result


class StreamTests(unittest.TestCase):
    def run_stream(self, body, **kwargs):
        out = io.StringIO()
        with patch.object(m, 'api_key', return_value='test-placeholder'), patch.object(
            m.urllib.request, 'urlopen', return_value=response(body)
        ), contextlib.redirect_stdout(out):
            result = m.stream_replication({'type': 'REPLICATION', 'url': 'https://example.com/video'}, **kwargs)
        return result, out.getvalue()

    def test_normal_eof_and_metadata(self):
        result, text = self.run_stream(b': ping\r\nevent: message\r\nid: 1\r\nretry: 3000\r\ndata:{"status":"streaming","result":"hello ","id":1}\r\ndata: {"status":"streaming","result":"world","id":1}\r\n')
        self.assertEqual(result, {'id': 1, 'prompt': 'hello world'})
        self.assertEqual(text, 'hello world\n')

    def test_multiline_json_and_done(self):
        result, _ = self.run_stream(b'data: {"status":"streaming",\ndata: "result":"hello"}\n\ndata: [DONE]\n')
        self.assertEqual(result['prompt'], 'hello')

    def test_invalid_responses_emit_no_prompt(self):
        valid = b'data:{"status":"streaming","result":"partial","id":1}\n'
        for body in [b'', b'<html>error</html>\n', b'data:{bad}\n\n',
                     b'data:{"status":"error","message":"failed"}\n',
                     b'data:{"code":1,"message":"failed"}\n', b'data:[]\n',
                     b'data:{"status":"streaming","result":42}\n',
                     b'data:{"status":"streaming","result":"  "}\n',
                     b'data:{"status":"streaming","result":"\xff"}\n',
                     valid + b'data:{"status":"error"}\n',
                     valid + b'data:{"status":"streaming","result":"wrong","id":2}\n',
                     valid + b'data:{"status":']:
            with self.subTest(body=body):
                out = io.StringIO()
                with patch.object(m, 'api_key', return_value='test-placeholder'), patch.object(
                    m.urllib.request, 'urlopen', return_value=response(body)
                ), contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                    m.stream_replication({})
                self.assertEqual(out.getvalue(), '')

    def test_raw_still_rejects_failure(self):
        with self.assertRaises(SystemExit):
            self.run_stream(b'data:{"status":"error"}\n', raw=True)

    def test_network_http_and_content_type_errors(self):
        errors = [TimeoutError('timeout'), urllib.error.URLError('offline'),
                  urllib.error.HTTPError('https://example.com', 429, 'rate limit', {}, io.BytesIO(b'busy'))]
        for error in errors:
            with self.subTest(error=error), patch.object(m, 'api_key', return_value='test-placeholder'), patch.object(m.urllib.request, 'urlopen', side_effect=error), self.assertRaises(SystemExit):
                m.stream_replication({})
        with patch.object(m, 'api_key', return_value='test-placeholder'), patch.object(m.urllib.request, 'urlopen', return_value=response(b'{}', 'application/json')), self.assertRaises(SystemExit):
            m.stream_replication({})

    def test_three_input_shapes_and_json(self):
        with tempfile.NamedTemporaryFile() as file:
            for source in [{'url': 'https://example.com/v'}, {'file': file.name}, {'business_id': '7', 'business_type': 'MATERIAL'}]:
                args = argparse.Namespace(url=None, file=None, business_id=None, business_type=None, raw=False, json=True, timeout=42)
                for key, value in source.items():
                    setattr(args, key, value)
                out = io.StringIO()
                with patch.object(m, 'upload_file', return_value={'id': 9}), patch.object(m, 'stream_replication', return_value={'id': 1, 'prompt': 'ok'}) as stream, contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    m.replicate(args)
                payload = stream.call_args.args[0]
                expected = {'type': 'REPLICATION', **({'url': args.url} if args.url else {'businessId': '9' if args.file else '7', 'businessType': 'FILE' if args.file else 'MATERIAL'})}
                self.assertEqual(payload, expected)
                self.assertEqual(json.loads(out.getvalue())['prompt'], 'ok')
                self.assertEqual(stream.call_args.kwargs['timeout'], 42)

    def test_input_exclusivity(self):
        args = argparse.Namespace(url='a', file='b', business_id=None, business_type=None)
        with self.assertRaises(SystemExit):
            m.replicate(args)
        args.url = args.file = None
        args.business_id = '7'
        with self.assertRaises(SystemExit):
            m.replicate(args)

    def test_connection_break_after_partial_result(self):
        class BrokenResponse:
            headers = response(b'').headers
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def __iter__(self):
                yield b'data:{"status":"streaming","result":"partial"}\n'
                raise m.http.client.IncompleteRead(b'', 10)
        out = io.StringIO()
        with patch.object(m, 'api_key', return_value='test-placeholder'), patch.object(m.urllib.request, 'urlopen', return_value=BrokenResponse()), contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            m.stream_replication({})
        self.assertEqual(out.getvalue(), '')

    def test_cli_rejects_invalid_options_before_request(self):
        for args in [
            ['batch', '--urls', 'missing', '--output-dir', 'unused', '--workers', '11'],
            ['replicate', '--url', 'unused', '--raw', '--json'],
            ['replicate', '--url', 'unused', '--timeout', '0'],
        ]:
            result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)

    def test_batch_isolation_failure_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            urls = root / 'urls.txt'
            urls.write_text('https://example.com/a\nhttps://example.com/b\nhttps://example.com/a\n')
            args = argparse.Namespace(urls=str(urls), output_dir=str(root / 'results'), workers=2, resume=False, timeout=1)
            def first(payload, **kwargs):
                if payload['url'].endswith('/b'):
                    raise SystemExit('failed')
                return {'id': 1, 'prompt': 'first'}
            with patch.object(m, 'api_key', return_value='test-placeholder'), patch.object(m, 'stream_replication', side_effect=first), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                m.batch(args)
            records = [json.loads(p.read_text()) for p in (root / 'results').glob('*.json')]
            self.assertEqual(len(records), 2)
            self.assertEqual({r['status'] for r in records}, {'success', 'failed'})
            args.resume = True
            with patch.object(m, 'api_key', return_value='test-placeholder'), patch.object(m, 'stream_replication', return_value={'id': 2, 'prompt': 'retried'}) as stream, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                m.batch(args)
            self.assertEqual(stream.call_count, 1)
            self.assertTrue(stream.call_args.args[0]['url'].endswith('/b'))


if __name__ == '__main__':
    unittest.main()
