import importlib.util
import json
import tempfile
import unittest
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
