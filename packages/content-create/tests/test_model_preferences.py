import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'lingtu_content_task.py'
spec = importlib.util.spec_from_file_location('content_task', SCRIPT)
CONTENT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CONTENT)


class ModelPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.home_patch = patch.object(CONTENT.Path, 'home', return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def cli(self, *args):
        env = dict(os.environ, HOME=str(self.home))
        env.pop('LINGTU_API_KEY', None)
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=env,
                              capture_output=True, text=True)

    def test_builtin_defaults_without_creating_file(self):
        self.assertEqual(CONTENT.selected_model('video', None), 'wan3.0-video')
        self.assertEqual(CONTENT.selected_model('image', None), 'gpt-image-2.5-ext-flare')
        self.assertFalse(CONTENT.model_preferences_path().exists())

    def test_new_image_model_is_supported_and_used_by_default(self):
        self.assertIn('gpt-image-2.5-ext-flare', CONTENT.IMAGE_MODELS)
        argv = [str(SCRIPT), '--kind', 'image', '--prompt', 'demo']
        with patch.object(sys, 'argv', argv), patch.object(CONTENT, 'require_api_key', return_value='test'), \
             patch.object(CONTENT, 'http_json', return_value={'data': {'scheduleId': 's'}}) as request, \
             patch.object(CONTENT, 'poll_schedule', return_value=0):
            self.assertEqual(CONTENT.main(), 0)
        self.assertEqual(request.call_args.args[3]['params']['model'], 'gpt-image-2.5-ext-flare')

    def test_persistence_across_processes_without_auth(self):
        result = self.cli('--kind', 'video', '--set-default-model', 'gemini-omni-video')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli('--kind', 'video', '--show-default-model')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['model'], 'gemini-omni-video')
        self.assertEqual(CONTENT.selected_model('video', None), 'gemini-omni-video')

    def test_explicit_override_does_not_change_saved_model(self):
        CONTENT.update_model_preference('video', 'gemini-omni-video')
        self.assertEqual(CONTENT.selected_model('video', 'wan3.0-video'), 'wan3.0-video')
        self.assertEqual(CONTENT.selected_model('video', None), 'gemini-omni-video')

    def test_reset_preserves_other_kind(self):
        CONTENT.update_model_preference('video', 'gemini-omni-video')
        CONTENT.update_model_preference('image', 'nano-banana-2')
        result = self.cli('--kind', 'video', '--reset-default-model')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(CONTENT.selected_model('video', None), 'wan3.0-video')
        self.assertEqual(CONTENT.selected_model('image', None), 'nano-banana-2')

    def test_wrong_kind_and_unknown_model_do_not_overwrite(self):
        CONTENT.update_model_preference('video', 'gemini-omni-video')
        for model in ('gpt-image-2', 'unknown'):
            result = self.cli('--kind', 'video', '--set-default-model', model)
            self.assertEqual(result.returncode, 2)
        self.assertEqual(CONTENT.selected_model('video', None), 'gemini-omni-video')

    def test_bad_config_fails_creation_but_not_poll_or_explicit_override(self):
        path = CONTENT.model_preferences_path()
        path.parent.mkdir(parents=True)
        path.write_text('{broken')
        with self.assertRaises(ValueError):
            CONTENT.selected_model('video', None)
        self.assertIsNone(CONTENT.selected_model('video', None, poll_only=True))
        self.assertEqual(CONTENT.selected_model('video', 'wan3.0-video'), 'wan3.0-video')

    def test_preference_command_rejects_generation(self):
        result = self.cli('--kind', 'video', '--set-default-model', 'gemini-omni-video', '--prompt', 'demo')
        self.assertEqual(result.returncode, 2)
        self.assertFalse(CONTENT.model_preferences_path().exists())

    def test_main_uses_saved_model_and_its_duration(self):
        CONTENT.update_model_preference('video', 'gemini-omni-video')
        argv = [str(SCRIPT), '--kind', 'video', '--prompt', 'demo', '--size', '720x1280']
        with patch.object(sys, 'argv', argv), patch.object(CONTENT, 'require_api_key', return_value='test'), \
             patch.object(CONTENT, 'http_json', return_value={'data': {'scheduleId': 's'}}) as request, \
             patch.object(CONTENT, 'poll_schedule', return_value=0):
            self.assertEqual(CONTENT.main(), 0)
        payload = request.call_args.args[3]
        self.assertEqual(payload['params']['model'], 'gemini-omni-video')
        self.assertEqual(payload['params']['seconds'], 10)

    def test_image_ratio_default_and_explicit_override(self):
        for flags, expected in (([], '9:16'), (['--aspect-ratio', '1:1'], '1:1')):
            with self.subTest(expected=expected):
                argv = [str(SCRIPT), '--kind', 'image', '--prompt', 'demo', *flags]
                with patch.object(sys, 'argv', argv), patch.object(CONTENT, 'require_api_key', return_value='test'), \
                     patch.object(CONTENT, 'http_json', return_value={'data': {'scheduleId': 's'}}) as request, \
                     patch.object(CONTENT, 'poll_schedule', return_value=0):
                    self.assertEqual(CONTENT.main(), 0)
                self.assertEqual(request.call_args.args[3]['params']['aspectRatio'], expected)

    def test_default_video_payload_is_480p(self):
        argv = [str(SCRIPT), '--kind', 'video', '--prompt', 'demo']
        with patch.object(sys, 'argv', argv), patch.object(CONTENT, 'require_api_key', return_value='test'), \
             patch.object(CONTENT, 'http_json', return_value={'data': {'scheduleId': 's'}}) as request, \
             patch.object(CONTENT, 'poll_schedule', return_value=0):
            self.assertEqual(CONTENT.main(), 0)
        self.assertEqual(request.call_args.args[3]['params']['size'], '480x854')

    def test_unsupported_default_resolution_stops_before_auth(self):
        CONTENT.update_model_preference('video', 'gemini-omni-video')
        argv = [str(SCRIPT), '--kind', 'video', '--prompt', 'demo']
        with patch.object(sys, 'argv', argv), patch.object(CONTENT, 'require_api_key') as auth, \
             patch.object(CONTENT, 'print_error') as error:
            self.assertEqual(CONTENT.main(), 2)
        auth.assert_not_called()
        self.assertIn('480x854', error.call_args.args[0]['error'])

    def test_main_poll_does_not_filter_by_new_preference(self):
        CONTENT.update_model_preference('video', 'gemini-omni-video')
        argv = [str(SCRIPT), '--kind', 'video', '--poll-schedule-id', 'old']
        with patch.object(sys, 'argv', argv), patch.object(CONTENT, 'require_api_key', return_value='test'), \
             patch.object(CONTENT, 'poll_schedule', return_value=0) as poll:
            self.assertEqual(CONTENT.main(), 0)
        self.assertIsNone(poll.call_args.args[0].model)


if __name__ == '__main__':
    unittest.main()
