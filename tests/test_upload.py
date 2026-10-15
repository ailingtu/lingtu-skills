import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared/scripts"))
import lingtu_upload as UPLOAD


class UploadTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.file = Path(directory.name) / "reference.png"
        self.raw = bytes(range(256)) * 600
        self.file.write_bytes(self.raw)
        self.data = {
            "fileId": 42, "url": "https://cdn.example.test/reference.png",
            "uploadUrl": "https://storage.example.test/object?signature=test", "isNew": True,
        }

    def test_hash_preserves_java_contract_without_reading_whole_file(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("whole-file read")):
            actual = UPLOAD.compute_content_hash(self.file)
        self.assertEqual(actual, hashlib.sha256(self.raw.hex().encode()).hexdigest())

    def test_new_file_uploads_before_confirmation(self):
        events = []
        def request(method, path, **kwargs):
            events.append(path)
            self.assertEqual(method, "POST")
            self.assertEqual(kwargs["api_key"], "test-placeholder")
            if path == "/custom/presign":
                self.assertEqual(kwargs["body"], {
                    "fileName": self.file.name, "size": len(self.raw), "contentType": "image/png",
                    "hash": hashlib.sha256(self.raw.hex().encode()).hexdigest(),
                })
                return {"code": 0, "data": self.data}
            self.assertEqual(path, "/custom/confirm")
            self.assertEqual(kwargs["body"], {"fileId": 42})
            return {"code": 0}
        with patch.object(UPLOAD, "request_json", side_effect=request), \
                patch.object(UPLOAD, "put_file", side_effect=lambda *a, **kw: events.append("PUT")) as put:
            result = UPLOAD.presign_upload(self.file, api_key="test-placeholder",
                presign_path="/custom/presign", confirm_path="/custom/confirm", as_system_exit=False)
        self.assertEqual(events, ["/custom/presign", "PUT", "/custom/confirm"])
        self.assertEqual(result, {"id": "42", "url": self.data["url"]})
        self.assertEqual(put.call_args.args, (self.data["uploadUrl"], self.file, "image/png"))

    def test_existing_file_skips_put_and_confirm(self):
        for flag in (False, "false", 0):
            with self.subTest(isNew=flag), \
                    patch.object(UPLOAD, "request_json", return_value={"data": dict(self.data, isNew=flag)}) as request, \
                    patch.object(UPLOAD, "put_file") as put:
                self.assertEqual(UPLOAD.presign_upload(self.file, api_key="test")["id"], "42")
                self.assertEqual(request.call_count, 1)
                put.assert_not_called()

    def test_malformed_presign_response_never_reports_success(self):
        for data in (None, [], {}, dict(self.data, fileId=0), dict(self.data, fileId=True),
                     dict(self.data, uploadUrl="")):
            with self.subTest(data=data), patch.object(UPLOAD, "request_json", return_value={"data": data}), \
                    patch.object(UPLOAD, "put_file") as put:
                with self.assertRaises(UPLOAD.LingtuHttpError):
                    UPLOAD.presign_upload(self.file, api_key="test", as_system_exit=False)
                put.assert_not_called()

    def test_put_failure_prevents_confirm(self):
        with patch.object(UPLOAD, "request_json", return_value={"data": self.data}) as request, \
                patch.object(UPLOAD, "put_file", side_effect=UPLOAD.LingtuHttpError("PUT failed")):
            with self.assertRaisesRegex(UPLOAD.LingtuHttpError, "PUT failed"):
                UPLOAD.presign_upload(self.file, api_key="test", as_system_exit=False)
            self.assertEqual(request.call_count, 1)

    def test_confirm_failure_is_reported_to_cli(self):
        with patch.object(UPLOAD, "request_json", side_effect=[
                {"data": self.data}, UPLOAD.LingtuHttpError("confirm failed")]), \
                patch.object(UPLOAD, "put_file"):
            with self.assertRaisesRegex(SystemExit, "confirm failed"):
                UPLOAD.presign_upload(self.file, api_key="test")

    def test_put_streams_bytes_and_reports_progress_without_api_key(self):
        connection = Mock()
        connection.getresponse.return_value.status = 200
        progress = Mock()
        with patch.object(UPLOAD.http.client, "HTTPSConnection", return_value=connection) as factory, \
                patch.object(Path, "read_bytes", side_effect=AssertionError("whole-file read")):
            UPLOAD.put_file(self.data["uploadUrl"], self.file, "image/png", on_progress=progress)
        self.assertEqual(factory.call_args.args, ("storage.example.test", 443))
        connection.putrequest.assert_called_once_with("PUT", "/object?signature=test")
        headers = dict(call.args for call in connection.putheader.call_args_list)
        self.assertEqual(headers, {"Content-Type": "image/png", "Content-Length": str(len(self.raw))})
        chunks = [call.args[0] for call in connection.send.call_args_list]
        self.assertEqual(b"".join(chunks), self.raw)
        self.assertTrue(all(len(chunk) <= UPLOAD.UPLOAD_CHUNK_SIZE for chunk in chunks))
        self.assertEqual(progress.call_args.args, (len(self.raw), len(self.raw)))
        connection.close.assert_called_once()

    def test_network_and_http_failures_are_upload_errors(self):
        for status in (403, None):
            with self.subTest(status=status):
                connection = Mock()
                if status:
                    connection.getresponse.return_value.status = status
                else:
                    connection.send.side_effect = OSError("connection lost")
                with patch.object(UPLOAD.http.client, "HTTPSConnection", return_value=connection):
                    with self.assertRaises(UPLOAD.LingtuHttpError):
                        UPLOAD.put_file(self.data["uploadUrl"], self.file, "image/png")
                connection.close.assert_called_once()


class InstalledUploadTests(unittest.TestCase):
    def test_bundled_callers_use_the_installed_shared_runtime(self):
        spec = importlib.util.spec_from_file_location("upload_build", ROOT / "scripts/build_package.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        # A fresh process and an unrelated cwd prevent repository imports from
        # hiding a missing helper in an independently installed package.
        script = '''
import importlib.util
from pathlib import Path
import sys
from unittest.mock import patch
package, source = Path(sys.argv[1]).resolve(), sys.argv[2]
spec = importlib.util.spec_from_file_location("installed_caller", package / "scripts" / source)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
import lingtu_upload
assert Path(lingtu_upload.__file__).is_relative_to(package)
image = package / "reference.png"
image.write_bytes(b"test image")
with patch.object(lingtu_upload, "request_json", return_value={"code": 0, "data": {
        "fileId": 42, "url": "https://cdn.example.test/image.png", "isNew": False}}):
    if hasattr(module, "upload_reference_image"):
        assert module.upload_reference_image(str(image), "https://api.example.test", "test") == "https://cdn.example.test/image.png"
        assert module.upload_reference_file_id(str(image), "https://api.example.test", "test", "audio") == 42
    elif hasattr(module, "upload_media"):
        assert module.upload_media(image, "https://api.example.test", "/v1/file/presign", "/v1/file/confirm", "test") == 42
    else:
        with patch.dict("os.environ", {"LINGTU_API_KEY": "test"}, clear=True):
            assert module.upload_file(str(image))["id"] == "42"
'''
        with tempfile.TemporaryDirectory() as directory:
            for package, source in (
                ("content-create", "lingtu_content_task.py"),
                ("content-create", "lingtu_video_understand.py"),
                ("tiktok-carousel", "lingtu_content_task.py"),
                ("xhs-remake", "lingtu_content_task.py"),
                ("video-understand", "lingtu_video_understand.py"),
                ("video-remake", "lingtu_video_remake.py"),
            ):
                with self.subTest(package=package, source=source):
                    destination, _ = build.build_package(package, Path(directory))
                    result = subprocess.run([sys.executable, "-c", script, str(destination), source],
                        cwd=directory, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
