import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lingtu_video_remake.py"
SPEC = importlib.util.spec_from_file_location("lingtu_video_remake", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class TranscriptTests(unittest.TestCase):
    def test_json_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.json"
            path.write_text(json.dumps({"data": {"segments": [
                {"start": 0, "end": 3.2, "text": "第一句。"},
                {"start": 3.2, "end": 8.5, "text": "第二句"},
            ]}}, ensure_ascii=False), encoding="utf-8")
            segments = MODULE.load_transcript(path)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["text"], "第一句。")

    def test_srt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.srt"
            path.write_text(
                "1\n00:00:00,000 --> 00:00:03,000\n你好\n\n"
                "2\n00:00:03,000 --> 00:00:07,500\n世界\n",
                encoding="utf-8",
            )
            segments = MODULE.load_transcript(path)
        self.assertEqual([item["text"] for item in segments], ["你好", "世界"])

    def test_vtt_minute_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.vtt"
            path.write_text(
                "WEBVTT\n\n00:00.000 --> 00:04.250\n第一段\n\n"
                "00:04.250 --> 00:09.000\n第二段\n",
                encoding="utf-8",
            )
            segments = MODULE.load_transcript(path)
        self.assertEqual(segments[-1]["end"], 9.0)

    def test_http_asr_uses_only_lingtu_api_key(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"video")
            response = {"segments": [{"start": 0, "end": 1, "text": "ok"}]}
            with mock.patch.dict(
                MODULE.os.environ,
                {"LINGTU_API_KEY": "lingtu-key", "ASR_API_KEY": "legacy-key"},
                clear=True,
            ), mock.patch.object(MODULE, "request_json", return_value=response) as request:
                segments = MODULE.transcribe_http(source, "https://example.test/asr", None, None)

        self.assertEqual(segments[0]["text"], "ok")
        self.assertEqual(request.call_args.kwargs["api_key"], "lingtu-key")


class SegmentPlannerTests(unittest.TestCase):
    def test_never_exceeds_fifteen_and_covers_timeline(self):
        transcript = [
            {"start": 0.0, "end": 6.0, "text": "第一句。"},
            {"start": 6.0, "end": 14.0, "text": "第二句。"},
            {"start": 14.0, "end": 21.0, "text": "第三句。"},
            {"start": 21.0, "end": 31.2, "text": "第四句。"},
        ]
        planned = MODULE.plan_segments(transcript, 31.2)
        self.assertEqual(planned[0]["start"], 0.0)
        self.assertEqual(planned[-1]["end"], 31.2)
        self.assertTrue(all(item["duration"] <= 15 for item in planned))
        for left, right in zip(planned, planned[1:]):
            self.assertEqual(left["end"], right["start"])

    def test_hard_cut_when_no_boundary(self):
        transcript = [{"start": 0.0, "end": 40.0, "text": "一段很长的文字"}]
        planned = MODULE.plan_segments(transcript, 40.0)
        self.assertEqual([item["duration"] for item in planned], [15.0, 15.0, 10.0])


class ReviewGateTests(unittest.TestCase):
    def test_next_segment_blocks_unreviewed_previous(self):
        manifest = {"segments": [
            {"id": "segment-001", "status": "waiting_review"},
            {"id": "segment-002", "status": "cut_ready"},
        ]}
        with self.assertRaises(MODULE.WorkflowError):
            MODULE.next_segment(manifest)


if __name__ == "__main__":
    unittest.main()

class ReferenceParameterTests(unittest.TestCase):
    def test_combined_schedule_payload_and_legacy_defaults(self):
        for references in ({}, {"image_references": ["https://example.test/a.png", "https://example.test/b.png"], "audio_file_ids": [123]}):
            with mock.patch.object(MODULE, "request_json", return_value={"data": {"scheduleId": "schedule"}}) as request:
                MODULE.create_schedule(base_url="https://example.test", create_path="/v1/ai/schedule/create",
                    api_key="test", file_id=456, seconds=-1, size="480x854", prompt="@图1 @视频1 @音频1", name="test", **references)
            payload = request.call_args.kwargs["payload"]
            self.assertEqual(payload["params"]["seconds"], -1)
            self.assertEqual(payload["params"]["videoFileIds"], [456])
            self.assertEqual(payload["nums"], 1)
            if references:
                self.assertEqual(payload["params"]["inputReferences"], references["image_references"])
                self.assertEqual(payload["params"]["audioFileIds"], [123])
            else:
                self.assertNotIn("inputReferences", payload["params"])
                self.assertNotIn("audioFileIds", payload["params"])

    def test_local_upload_response_mapping_and_remote_reuse(self):
        args = MODULE.build_parser().parse_args(["generate", "--job-dir", "job", "--seconds", "-1"])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reference.png"
            source.write_bytes(b"test")
            # 上传现在由 shared/scripts/lingtu_upload.py 的 presign_upload 发起，MODULE.request_json 不再参与上传，
            # 因此在这里拦截 presign_upload，避免单元测试真的去调线上接口。
            with mock.patch.object(MODULE, "presign_upload", return_value={"id": "42", "url": "https://example.test/image.png"}) as upload:
                self.assertEqual(MODULE.resolve_references([str(source)], args, "test", image=True), ["https://example.test/image.png"])
                self.assertEqual(MODULE.resolve_references([str(source)], args, "test", image=False), [42])
                self.assertEqual(upload.call_count, 2)
                self.assertEqual(upload.call_args.kwargs["presign_path"], "/v1/file/presign")
                self.assertEqual(upload.call_args.kwargs["confirm_path"], "/v1/file/confirm")
            with mock.patch.object(MODULE, "presign_upload") as upload:
                self.assertEqual(MODULE.resolve_references(["42"], args, "test", image=False), [42])
                self.assertEqual(MODULE.resolve_references(["https://example.test/a.png"], args, "test", image=True), ["https://example.test/a.png"])
                upload.assert_not_called()
            with mock.patch.object(MODULE, "presign_upload", return_value={"id": "42", "url": ""}):
                with self.assertRaises(MODULE.WorkflowError):
                    MODULE.upload_media(source, args.base_url, args.presign_path, args.confirm_path, "test", image=True)
            with mock.patch.object(MODULE, "presign_upload", side_effect=MODULE.LingtuHttpError("上传超时", url="https://example.test")):
                with self.assertRaises(MODULE.WorkflowError):
                    MODULE.upload_media(source, args.base_url, args.presign_path, args.confirm_path, "test", image=False)

    def test_reference_validation_and_cli_order(self):
        args = MODULE.build_parser().parse_args(["regenerate", "--job-dir", "job", "--segment", "segment-001",
            "--reference-image", "https://example.test/one.png", "--reference-image", "https://example.test/two.png",
            "--reference-audio", "123", "--seconds", "-1"])
        self.assertEqual(args.seconds, -1)
        self.assertEqual(args.reference_image, ["https://example.test/one.png", "https://example.test/two.png"])
        for invalid in ("0", "-1", "data:audio/mp3;base64,AAA"):
            with self.assertRaises(MODULE.WorkflowError):
                MODULE.validate_references([invalid], image=False)

    def test_regenerate_reuses_parameters_and_blocks_running_attempt(self):
        args = MODULE.build_parser().parse_args(["regenerate", "--job-dir", "job", "--segment", "segment-001"])
        with tempfile.TemporaryDirectory() as directory:
            clip = Path(directory) / "clip.mp4"
            clip.write_bytes(b"video")
            segment = {"id": "segment-001", "duration": 10.9, "status": "rejected", "source_clip": str(clip),
                "attempts": [{"image_references": ["https://example.test/image.png"], "audio_file_ids": [42],
                    "seconds": -1, "size": "480x854", "prompt": "@图1 @音频1 本段台词", "review_note": "保持动作"}]}
            manifest = {"job_id": "test", "segments": [segment]}
            with mock.patch.object(MODULE, "require_lingtu_key", return_value="test"), \
                 mock.patch.object(MODULE, "probe_media", return_value={"width": 720, "height": 960}), \
                 mock.patch.object(MODULE, "upload_video", return_value=99), \
                 mock.patch.object(MODULE, "create_schedule", return_value=("schedule", [], "task")) as create, \
                 mock.patch.object(MODULE, "poll_attempt", return_value={}), \
                 mock.patch.object(MODULE, "request_json") as network:
                MODULE.generate_segment(Path(directory), manifest, segment, args)
                self.assertEqual(create.call_args.kwargs["audio_file_ids"], [42])
                self.assertEqual(create.call_args.kwargs["image_references"], ["https://example.test/image.png"])
                self.assertEqual(create.call_args.kwargs["seconds"], -1)
                self.assertEqual(create.call_args.kwargs["size"], "480x854")
                self.assertIn("本段台词", create.call_args.kwargs["prompt"])
                self.assertEqual(segment["attempts"][-1]["audio_file_ids"], [42])
                with self.assertRaises(MODULE.WorkflowError):
                    MODULE.generate_segment(Path(directory), manifest, segment, args)
                self.assertEqual(create.call_count, 1)
                network.assert_not_called()

class AutomaticTranscriptTests(unittest.TestCase):
    def args(self, *extra):
        return MODULE.build_parser().parse_args(["prepare", "source.mp4", "--job-dir", "job", *extra])

    def test_short_text_bypasses_all_asr_and_records_real_duration(self):
        with mock.patch.object(MODULE, "transcribe_http") as http, mock.patch.object(MODULE, "transcribe_whisper") as whisper:
            transcript, origin = MODULE.prepare_transcript(self.args("--script-text", "原话不改"), Path("source"), Path("job"), 10.913)
            self.assertEqual(transcript, [{"start": 0.0, "end": 10.913, "text": "原话不改"}])
            self.assertEqual(origin, "provided-text-whole-clip")
            self.assertEqual(len(MODULE.plan_segments(transcript, 10.913)), 1)
            http.assert_not_called()
            whisper.assert_not_called()

    def test_txt_file_alias_and_empty_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "台词.txt"
            path.write_text("完整台词", encoding="utf-8-sig")
            for flag in ("--script-file", "--transcript"):
                transcript, _ = MODULE.prepare_transcript(self.args(flag, str(path)), Path("source"), Path(directory), 15)
                self.assertEqual(transcript[0]["text"], "完整台词")
            with self.assertRaises(MODULE.WorkflowError):
                MODULE.prepare_transcript(self.args("--script-text", "  "), Path("source"), Path(directory), 10)

    def test_auto_local_first_and_long_text_requires_real_asr(self):
        real = [{"start": 0, "end": 4, "text": "转写原话"}]
        with mock.patch.dict(MODULE.os.environ, {"LINGTU_ASR_URL": "https://example.test/asr"}), \
             mock.patch.object(MODULE.shutil, "which", return_value="/mock/whisper"), \
             mock.patch.object(MODULE, "transcribe_whisper", return_value=real) as whisper, \
             mock.patch.object(MODULE, "transcribe_http") as http:
            transcript, origin = MODULE.prepare_transcript(self.args("--script-text", "长视频台词"), Path("source"), Path("job"), 16)
            self.assertEqual((transcript, origin), (real, "whisper"))
            whisper.assert_called_once()
            http.assert_not_called()

    def test_explicit_local_overrides_env_and_http_fallback(self):
        with mock.patch.dict(MODULE.os.environ, {"LINGTU_ASR_URL": "https://example.test/asr"}), \
             mock.patch.object(MODULE.shutil, "which", return_value=None), \
             mock.patch.object(MODULE, "transcribe_whisper", return_value=[]) as whisper, \
             mock.patch.object(MODULE, "transcribe_http", return_value=[]) as http:
            MODULE.prepare_transcript(self.args("--whisper"), Path("source"), Path("job"), 20)
            whisper.assert_called_once()
            http.assert_not_called()
            _, origin = MODULE.prepare_transcript(self.args(), Path("source"), Path("job"), 20)
            self.assertEqual(origin, "http")
            http.assert_called_once()

    def test_missing_transcriber_reports_capability_gap(self):
        with mock.patch.dict(MODULE.os.environ, {}, clear=True), mock.patch.object(MODULE.shutil, "which", return_value=None):
            with self.assertRaisesRegex(MODULE.WorkflowError, "无法自动转写"):
                MODULE.prepare_transcript(self.args(), Path("source"), Path("job"), 20)

class NoSpeechTests(unittest.TestCase):
    def test_explicit_no_speech_never_calls_asr_and_covers_timeline(self):
        args = MODULE.build_parser().parse_args(["prepare", "source.mp4", "--job-dir", "job", "--no-speech"])
        with mock.patch.dict(MODULE.os.environ, {"LINGTU_ASR_URL": "https://example.test/asr"}), \
             mock.patch.object(MODULE, "transcribe_whisper") as whisper, \
             mock.patch.object(MODULE, "transcribe_http") as http:
            for duration, expected in ((38, [15, 15, 8]), (10.9, [10.9]), (30, [15, 15]), (30.2, [15, 15, 0.2])):
                transcript, origin = MODULE.prepare_transcript(args, Path("source"), Path("job"), duration)
                self.assertEqual((transcript, origin), ([], "no-speech"))
                planned = MODULE.plan_segments(transcript, duration)
                self.assertEqual(len(planned), len(expected))
                for segment, seconds in zip(planned, expected):
                    self.assertAlmostEqual(segment["duration"], seconds)
                    self.assertEqual(segment["text"], "")
                self.assertEqual(planned[0]["start"], 0)
                self.assertEqual(planned[-1]["end"], duration)
                for left, right in zip(planned, planned[1:]):
                    self.assertEqual(left["end"], right["start"])
            whisper.assert_not_called()
            http.assert_not_called()

    def test_no_speech_conflicts_with_transcription_inputs(self):
        for option in (["--script-text", "hello"], ["--script-file", "speech.txt"], ["--transcript", "speech.srt"],
                       ["--whisper"], ["--asr-url", "https://example.test/asr"]):
            with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                MODULE.build_parser().parse_args(["prepare", "source.mp4", "--job-dir", "job", "--no-speech", *option])

    def test_prepare_persists_no_speech_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"test")
            job = Path(directory) / "job"
            args = MODULE.build_parser().parse_args(["prepare", str(source), "--job-dir", str(job), "--no-speech"])
            with mock.patch.object(MODULE, "probe_media", return_value={"duration": 38}), \
                 mock.patch.object(MODULE, "cut_muted_segment") as cut, \
                 mock.patch.object(MODULE, "emit"), mock.patch.object(MODULE, "request_json") as network:
                MODULE.command_prepare(args)
                self.assertEqual(cut.call_count, 3)
                network.assert_not_called()
            manifest = MODULE.load_manifest(job)
            self.assertEqual(manifest["transcription"]["source"], "no-speech")
            self.assertEqual(json.loads((job / "transcript.json").read_text()), {"segments": []})
            self.assertTrue(all(segment["status"] == "cut_ready" for segment in manifest["segments"]))
