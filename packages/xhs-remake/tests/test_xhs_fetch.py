import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lingtu_video_download.py"
spec = importlib.util.spec_from_file_location("xhs_fetch", SCRIPT)
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


class PhotoOnlyTests(unittest.TestCase):
    def test_photo_only_rejects_video_before_download(self):
        data = {
            "materialType": "VIDEO",
            "downloadAddr": "https://cdn.example.com/video.mp4",
            "coverUrl": "https://cdn.example.com/cover.jpg",
        }
        stdout = io.StringIO()
        with patch.object(MODULE, "fetch_material", return_value=data), \
                patch.object(MODULE, "download_file") as download, \
                patch("sys.stdout", stdout), \
                self.assertRaises(SystemExit):
            MODULE.main([
                "download", "--video-url", "https://www.xiaohongshu.com/explore/example",
                "--photo-only",
            ])
        download.assert_not_called()
        self.assertEqual(json.loads(stdout.getvalue())["imageCount"], 0)


if __name__ == "__main__":
    unittest.main()
