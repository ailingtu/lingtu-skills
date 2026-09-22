import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lingtu_video_download.py"
spec = importlib.util.spec_from_file_location("lingtu_video_download", SCRIPT)
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


PAGE = "https://www.tiktok.com/@creator/video/7123456789012345678"


class MediaUrlTests(unittest.TestCase):
    def test_prefers_download_address(self):
        data = {
            "downloadAddr": "https://cdn.example.com/no-watermark.mp4",
            "playAddr": "https://cdn.example.com/play.mp4",
            "videoUrl": PAGE,
        }
        self.assertEqual(
            MODULE.media_url(data, PAGE),
            ("https://cdn.example.com/no-watermark.mp4", "downloadAddr"),
        )

    def test_falls_back_to_play_address(self):
        data = {"playAddr": "https://cdn.example.com/play.mp4", "videoUrl": PAGE}
        self.assertEqual(MODULE.media_url(data, PAGE)[1], "playAddr")

    def test_ignores_page_url_echoed_as_video_url(self):
        self.assertEqual(MODULE.media_url({"videoUrl": PAGE}, PAGE), (None, None))

    def test_accepts_distinct_response_video_url(self):
        data = {"videoUrl": "https://cdn.example.com/video.mp4"}
        self.assertEqual(MODULE.media_url(data, PAGE)[0], data["videoUrl"])

    def test_collects_image_list_in_order(self):
        data = {
            "imageList": [
                {"url": "https://cdn.example.com/1.webp", "width": 1, "height": 1},
                {"url": "https://cdn.example.com/1.webp"},
                "https://cdn.example.com/2.webp",
            ],
            "coverUrl": "https://cdn.example.com/cover.webp",
        }
        self.assertEqual(
            MODULE.image_urls(data),
            ["https://cdn.example.com/1.webp", "https://cdn.example.com/2.webp"],
        )

    def test_uses_cover_when_photo_note_has_no_image_list(self):
        self.assertEqual(
            MODULE.image_urls({
                "materialType": "PHOTO",
                "coverUrl": "https://cdn.example.com/cover.webp",
            }),
            ["https://cdn.example.com/cover.webp"],
        )

    def test_video_cover_is_not_a_photo_set(self):
        self.assertEqual(
            MODULE.image_urls({
                "materialType": "VIDEO",
                "downloadAddr": "https://cdn.example.com/video.mp4",
                "coverUrl": "https://cdn.example.com/cover.webp",
            }),
            [],
        )

    def test_fetch_prints_metrics_without_downloading(self):
        data = {
            "videoId": "7624922739500993822",
            "playCount": 10,
            "diggCount": 2,
            "videoUrl": PAGE,
        }
        stdout = io.StringIO()
        with patch.object(MODULE, "fetch_material", return_value=data), \
                patch("sys.stdout", stdout):
            code = MODULE.main(["fetch", "--video-url", PAGE])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["playCount"], 10)
        self.assertIsNone(payload["media"])
        self.assertEqual(payload["data"]["videoId"], data["videoId"])


if __name__ == "__main__":
    unittest.main()
