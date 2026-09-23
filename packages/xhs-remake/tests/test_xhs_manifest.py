import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lingtu_xhs_manifest.py"
spec = importlib.util.spec_from_file_location("lingtu_xhs_manifest", SCRIPT)
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415408d763f8cfc0f01f00050001ff89993d1d0000000049454e44ae426082"
)


class ManifestTests(unittest.TestCase):
    def test_scans_images_and_marks_content_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.png").write_bytes(PNG_1X1)
            (root / "a.png").write_bytes(PNG_1X1)
            (root / "notes.txt").write_text("ignore", encoding="utf-8")

            manifest = MODULE.build_manifest([str(root)])

            self.assertEqual(manifest["assetCount"], 2)
            self.assertEqual(manifest["uniqueAssetCount"], 1)
            self.assertEqual(manifest["assets"][0]["filename"], "a.png")
            self.assertEqual(manifest["assets"][0]["width"], 1)
            self.assertIsNone(manifest["assets"][0]["duplicateOf"])
            self.assertTrue(manifest["assets"][1]["duplicateOf"].endswith("a.png"))

    def test_repeated_path_is_not_listed_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "one.png"
            image.write_bytes(PNG_1X1)
            manifest = MODULE.build_manifest([str(image), str(image)])
            self.assertEqual(manifest["assetCount"], 1)

    def test_missing_path_is_a_warning(self):
        manifest = MODULE.build_manifest(["/definitely/not/here"])
        self.assertEqual(manifest["assetCount"], 0)
        self.assertEqual(len(manifest["warnings"]), 1)

    def test_cli_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "one.png"
            image.write_bytes(PNG_1X1)
            output = root / "manifest.json"
            output.write_text(json.dumps({}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                MODULE.main(["--material", str(image), "--output", str(output)])


if __name__ == "__main__":
    unittest.main()
