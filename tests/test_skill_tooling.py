import importlib.util
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


BUILD = load_module("lingtu_build_package", ROOT / "scripts" / "build_package.py")
CREATE = load_module("lingtu_create_package", ROOT / "scripts" / "create_package.py")


class SkillAuthContractTests(unittest.TestCase):
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
                    binding_script = destination / "shared" / "scripts" / "user_keys.py"
                    self.assertEqual(
                        binding_script.is_file(),
                        metadata["auth"] == "lingtu-api-key",
                    )
                    if metadata["auth"] == "none":
                        self.assertFalse((destination / "shared").exists())

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


if __name__ == "__main__":
    unittest.main()
