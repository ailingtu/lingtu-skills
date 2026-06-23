from pathlib import Path
import sys
import unittest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.utils import parse_creator_handle, slugify_handle  # noqa: E402


class HandleParsingTests(unittest.TestCase):
    def test_slugify_preserves_trailing_underscores(self) -> None:
        self.assertEqual(slugify_handle("arianaguerrero__"), "arianaguerrero__")
        self.assertEqual(slugify_handle("user.name_"), "user.name_")

    def test_slugify_handles_mentions_and_leading_noise(self) -> None:
        self.assertEqual(slugify_handle("@mrbeast"), "mrbeast")
        self.assertEqual(slugify_handle("_leading_dash"), "leading_dash")

    def test_instagram_url_preserves_trailing_underscores(self) -> None:
        self.assertEqual(
            parse_creator_handle(
                "https://www.instagram.com/arianaguerrero__/",
                platform="instagram",
            ),
            "arianaguerrero__",
        )


if __name__ == "__main__":
    unittest.main()
