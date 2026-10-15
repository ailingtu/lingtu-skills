import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED_SCRIPTS = ROOT / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


BUILD = load_module("lingtu_build_package", ROOT / "scripts" / "build_package.py")
CREATE = load_module("lingtu_create_package", ROOT / "scripts" / "create_package.py")
AUTH = load_module("lingtu_auth", ROOT / "shared" / "scripts" / "lingtu_auth.py")


class SkillAuthContractTests(unittest.TestCase):
    def test_missing_key_reports_configuration_without_binding(self):
        for value in ("", "   "):
            with self.subTest(value=value), patch.dict("os.environ", {"LINGTU_API_KEY": value}, clear=True):
                with self.assertRaises(SystemExit) as error:
                    AUTH.require_api_key()
                message = str(error.exception)
                self.assertIn("https://ailingtu.com/api-keys", message)
                self.assertIn("LINGTU_API_KEY", message)
                self.assertNotIn("bind", message)

    def test_configured_key_is_returned_without_output(self):
        with patch.dict("os.environ", {"LINGTU_API_KEY": " test-placeholder "}, clear=True):
            self.assertEqual(AUTH.require_api_key(), "test-placeholder")

    def test_production_scripts_do_not_reference_alternate_api_key_variables(self):
        roots = [ROOT / "shared" / "scripts"] + [
            path for path in (ROOT / "packages").glob("*/scripts") if path.is_dir()
        ]
        pattern = re.compile(r"\b[A-Z][A-Z0-9_]*API_KEY\b")
        for scripts_dir in roots:
            for script in scripts_dir.rglob("*.py"):
                with self.subTest(script=script.relative_to(ROOT)):
                    variables = set(pattern.findall(script.read_text(encoding="utf-8")))
                    self.assertLessEqual(variables, {"LINGTU_API_KEY"})

    def test_every_package_declares_a_valid_auth_mode(self):
        for skill_md in sorted((ROOT / "packages").glob("*/SKILL.md")):
            with self.subTest(skill=skill_md.parent.name):
                metadata = BUILD.parse_frontmatter(skill_md)
                BUILD.validate_metadata(metadata, skill_md)
                BUILD.validate_auth_instructions(metadata, skill_md)
                self.assertIn(metadata["auth"], BUILD.AUTH_MODES)

    def test_built_packages_follow_declared_auth_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for package_id in BUILD.PACKAGE_IDS:
                with self.subTest(package=package_id):
                    destination, _ = BUILD.build_package(package_id, output)
                    metadata = BUILD.parse_frontmatter(destination / "SKILL.md")
                    auth_script = destination / "shared" / "scripts" / "lingtu_auth.py"
                    self.assertEqual(
                        auth_script.is_file(),
                        metadata["auth"] == "lingtu-api-key",
                    )
                    self.assertFalse((destination / "shared" / "scripts" / "user_keys.py").exists())
                    for path in destination.rglob("*"):
                        if path.suffix in {".md", ".py"}:
                            self.assertNotIn("user_keys.py single bind", path.read_text())
                            self.assertNotIn("/binduser", path.read_text())
                    if metadata["auth"] == "none":
                        self.assertFalse((destination / "shared").exists())
                    else:
                        with patch.dict("os.environ", {"LINGTU_API_KEY": ""}, clear=True):
                            result = subprocess.run(
                                [sys.executable, "-c", "from lingtu_auth import require_api_key; require_api_key()"],
                                cwd=auth_script.parent, capture_output=True, text=True,
                            )
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("Command", result.stderr)
                        self.assertIn("Win + R", result.stderr)
                        self.assertIn("launchctl setenv", result.stderr)
                        self.assertIn("SetEnvironmentVariable", result.stderr)
                        self.assertNotIn("Traceback", result.stderr)

    def test_generation_and_remake_bundles_run_without_sibling_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            remake, _ = BUILD.build_package("video-remake", output)
            content, _ = BUILD.build_package("content-create", output)
            self.assertTrue((content / "references/viral-remake-workflow.md").is_file())
            self.assertTrue((content / "references/video-understand-api.md").is_file())
            self.assertFalse((remake / "references/viral-remake-workflow.md").exists())
            self.assertTrue((remake / "references/long-video-workflow.md").is_file())
            for package, scripts in (
                (content, ("lingtu_video_understand.py", "lingtu_content_task.py")),
                (remake, ("lingtu_video_remake.py",)),
            ):
                for script in scripts:
                    result = subprocess.run(
                        [sys.executable, str(package / "scripts" / script), "--help"],
                        cwd=package, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                for reference in (package / "references").glob("*.md"):
                    self.assertNotIn("../content-create/", reference.read_text())
                    self.assertNotIn("../video-understand/", reference.read_text())

    def test_scaffold_emits_auth_contract_and_ui_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            packages_dir = Path(directory)
            destination = CREATE.create_package(
                "creator-insights",
                display_name="灵途达人洞察",
                summary="分析达人数据并生成可执行的洞察建议。",
                description="通过灵途 AI 业务接口查询达人数据并生成分析结果。",
                packages_dir=packages_dir,
            )
            metadata = BUILD.parse_frontmatter(destination / "SKILL.md")
            BUILD.validate_metadata(metadata, destination / "SKILL.md")
            BUILD.validate_auth_instructions(metadata, destination / "SKILL.md")
            self.assertEqual(metadata["auth"], "lingtu-api-key")
            self.assertIn("$lingtu-creator-insights", (destination / "agents" / "openai.yaml").read_text())

            public_destination = CREATE.create_package(
                "public-guide",
                display_name="Lingtu Public Guide",
                summary="Read public Lingtu documentation without calling business APIs.",
                description="Guide developers using public Lingtu documentation only.",
                auth="none",
                packages_dir=packages_dir,
            )
            public_metadata = BUILD.parse_frontmatter(public_destination / "SKILL.md")
            BUILD.validate_metadata(public_metadata, public_destination / "SKILL.md")
            BUILD.validate_auth_instructions(public_metadata, public_destination / "SKILL.md")
            self.assertEqual(public_metadata["auth"], "none")
            self.assertNotIn(
                "user_keys.py single bind",
                (public_destination / "SKILL.md").read_text(encoding="utf-8"),
            )


class SkillUploadContractTests(unittest.TestCase):
    def test_no_skill_still_uses_the_gateway_multipart_upload_endpoint(self):
        current = Path(__file__).resolve()
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT)
            if not path.is_file() or path.suffix not in {".md", ".py"}:
                continue
            if ".git" in relative.parts or "dist" in relative.parts or path.resolve() == current:
                continue
            with self.subTest(path=relative):
                self.assertNotIn("/v1/file/upload", path.read_text(encoding="utf-8"))

    def test_shared_upload_module_exposes_only_the_presign_flow(self):
        import lingtu_upload

        self.assertEqual(lingtu_upload.FILE_PRESIGN_PATH, "/v1/file/presign")
        self.assertEqual(lingtu_upload.FILE_CONFIRM_PATH, "/v1/file/confirm")
        self.assertTrue(callable(lingtu_upload.presign_upload))
        self.assertFalse(hasattr(lingtu_upload, "multipart_upload"))
        self.assertFalse(hasattr(lingtu_upload, "UPLOAD_PATH"))


if __name__ == "__main__":
    unittest.main()
