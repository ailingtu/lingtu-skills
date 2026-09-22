from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "lingtu_skillhub_publish.py"
SPEC = importlib.util.spec_from_file_location("lingtu_skillhub_publish", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

LINGTU_TOKEN = "blg_" + "A" * 43
WORKBUDDY_TOKEN = "skh_" + "a" * 32


def write_skill(root: Path, *, name: str = "lingtu-demo", auth: str = "none", display_name: str = "示例技能") -> Path:
    skill = root / "SKILL.md"
    skill.write_text(
        "\n".join([
            "---",
            f"name: {name}",
            f"slug: {name}",
            "version: 0.1.0",
            f"auth: {auth}",
            f"displayName: \"{display_name}\"",
            "summary: \"用于测试的技能包摘要。\"",
            "---",
            "",
            "# 示例",
            "",
        ]),
        encoding="utf-8",
    )
    return root


class Result:
    def __init__(self, code: int = 0, out: str = "", err: str = "") -> None:
        self.returncode = code
        self.stdout = out
        self.stderr = err


class SkillhubPublishTest(unittest.TestCase):
    def test_status_hides_secrets_and_ignores_business_key(self) -> None:
        env = {
            "LINGTU_API_KEY": "business-key",
            "BLOG_AGENT_TOKEN": LINGTU_TOKEN,
            "LINGTU_SKILLHUB_TOKEN": "skh_not_a_lingtu_token_value_here",
            "SKILLHUB_KEY": WORKBUDDY_TOKEN,
        }
        with patch.dict(os.environ, env, clear=True):
            stdout = io.StringIO()
            with patch.object(sys, "stdout", stdout):
                self.assertEqual(MODULE.main(["status"]), 0)
        payload = json.loads(stdout.getvalue())
        rendered = stdout.getvalue()
        self.assertNotIn(LINGTU_TOKEN, rendered)
        self.assertNotIn(WORKBUDDY_TOKEN, rendered)
        self.assertNotIn("business-key", rendered)
        self.assertFalse(payload["platforms"]["lingtu"]["accepted"])
        self.assertTrue(payload["platforms"]["workbuddy"]["accepted"])
        self.assertIn("LINGTU_API_KEY", payload["ignored"])
        self.assertFalse(payload["platforms"]["other"]["available"])

    def test_lingtu_dry_run_does_not_upload(self) -> None:
        def opener(*_args, **_kwargs):
            raise AssertionError("dry-run must not upload")

        with TemporaryDirectory() as raw:
            directory = write_skill(Path(raw))
            (directory / ".env").write_text("SECRET=1\n", encoding="utf-8")
            (directory / "tests").mkdir()
            (directory / "tests" / "test_hidden.py").write_text("x = 1\n", encoding="utf-8")
            with patch.dict(os.environ, {"LINGTU_SKILLHUB_TOKEN": LINGTU_TOKEN}, clear=True):
                payload = MODULE.publish_lingtu(directory, None, False, opener)
            self.assertTrue(payload["dryRun"])
            self.assertEqual(payload["packageName"], "lingtu-demo")
            body = MODULE.build_zip(directory)
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                names = set(archive.namelist())
            self.assertIn("SKILL.md", names)
            self.assertNotIn(".env", names)
            self.assertFalse(any(name.startswith("tests/") for name in names))

    def test_lingtu_confirm_uses_bearer_token_only(self) -> None:
        captured = {}

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"mode":"publish","packageName":"lingtu-demo","slug":"demo","version":"0.1.0"}'

        def opener(request, timeout):
            del timeout
            captured["authorization"] = request.get_header("Authorization")
            captured["api_key"] = request.get_header("X-api-key")
            captured["body"] = request.data
            return Response()

        with TemporaryDirectory() as raw:
            directory = write_skill(Path(raw))
            with patch.dict(os.environ, {"LINGTU_SKILLHUB_TOKEN": LINGTU_TOKEN, "LINGTU_API_KEY": "business-key"}, clear=True):
                payload = MODULE.publish_lingtu(directory, None, True, opener)
        self.assertEqual(captured["authorization"], f"Bearer {LINGTU_TOKEN}")
        self.assertIsNone(captured["api_key"])
        self.assertIn(b'name="packageName"', captured["body"])
        self.assertNotIn(b"business-key", captured["body"])
        self.assertEqual(payload["result"]["mode"], "publish")

    def test_workbuddy_redacts_key_and_rejects_lingtu_token(self) -> None:
        calls = []

        def runner(argv, cwd):
            del cwd
            calls.append(argv)
            if argv[1] == "login":
                return Result(0, f"logged in with {WORKBUDDY_TOKEN}")
            return Result(0, f"https://skillhub.cn/skills/demo {WORKBUDDY_TOKEN}")

        with TemporaryDirectory() as raw:
            directory = write_skill(Path(raw), name="demo-skill", display_name="Demo")
            with patch.dict(os.environ, {"SKILLHUB_KEY": LINGTU_TOKEN}, clear=True):
                with self.assertRaises(MODULE.PublishError) as raised:
                    MODULE.publish_workbuddy(directory, False, runner, True)
            self.assertEqual(raised.exception.code, "invalid_credential")
            with patch.dict(os.environ, {"SKILLHUB_KEY": WORKBUDDY_TOKEN}, clear=True):
                preview = MODULE.publish_workbuddy(directory, False, runner, True)
                payload = MODULE.publish_workbuddy(directory, True, runner, True)
        self.assertEqual(calls[0][:2], ["skillhub", "publish"])
        self.assertIn("--dry-run", calls[0])
        self.assertEqual(calls[0][-1], str(directory))
        self.assertEqual(calls[1][1], "login")
        self.assertNotIn("--dry-run", calls[2])
        self.assertEqual(calls[2][-1], str(directory))
        self.assertNotIn(WORKBUDDY_TOKEN, json.dumps(preview))
        self.assertNotIn(WORKBUDDY_TOKEN, json.dumps(payload))
        self.assertTrue(preview["dryRun"])
        self.assertFalse(payload["dryRun"])

    def test_missing_workbuddy_cli_asks_customer_to_install(self) -> None:
        calls = []

        def runner(argv, cwd):
            del argv, cwd
            calls.append(True)
            return Result()

        with TemporaryDirectory() as raw:
            directory = write_skill(Path(raw), name="demo-skill", display_name="Demo")
            with self.assertRaises(MODULE.PublishError) as raised:
                MODULE.publish_workbuddy(directory, True, runner, False)
        self.assertEqual(raised.exception.code, "missing_cli")
        self.assertEqual(raised.exception.details["installUrl"], "https://skillhub.cn/tutorials")
        self.assertEqual(calls, [])

    def test_lingtu_rejects_non_lingtu_package_name(self) -> None:
        with TemporaryDirectory() as raw:
            directory = write_skill(Path(raw), name="foreign-skill")
            payload = MODULE.lint_payload(directory, "lingtu")
        self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()
