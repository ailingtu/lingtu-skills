import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lingtu_content_task.py"
spec = importlib.util.spec_from_file_location("xhs_content_task", SCRIPT)
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


class PromptFileTests(unittest.TestCase):
    def test_reads_utf8_prompt_file(self):
        with tempfile.TemporaryDirectory() as directory:
            prompt = Path(directory) / "01.txt"
            prompt.write_text("  小红书第一页：保留人物身份  \n", encoding="utf-8")
            argv = [str(SCRIPT), "--kind", "image", "--prompt-file", str(prompt)]
            with patch.object(sys, "argv", argv):
                args = MODULE.parse_args()
            self.assertEqual(args.prompt, "小红书第一页：保留人物身份")

    def test_rejects_prompt_and_prompt_file_together(self):
        with tempfile.TemporaryDirectory() as directory:
            prompt = Path(directory) / "01.txt"
            prompt.write_text("内容", encoding="utf-8")
            argv = [
                str(SCRIPT), "--kind", "image", "--prompt", "inline",
                "--prompt-file", str(prompt),
            ]
            with patch.object(sys, "argv", argv), self.assertRaises(SystemExit):
                MODULE.parse_args()


class ImagePayloadTests(unittest.TestCase):
    def test_gpt_image_25_includes_concrete_quality_size(self):
        argv = [
            str(SCRIPT), "--kind", "image", "--prompt", "封面",
            "--aspect-ratio", "3:4", "--image-quality", "2K",
        ]
        with patch.object(sys, "argv", argv):
            args = MODULE.parse_args()
        args.model = "gpt-image-2.5-ext-flare"
        args.client_task_id = "testtask"
        payload = MODULE.build_create_payload(args, ["https://example.com/reference.webp"])
        self.assertEqual(payload["params"]["aspectRatio"], "3:4")
        self.assertEqual(payload["params"]["size"], "2560x1440")
        self.assertEqual(payload["params"]["inputReferences"], ["https://example.com/reference.webp"])


if __name__ == "__main__":
    unittest.main()
