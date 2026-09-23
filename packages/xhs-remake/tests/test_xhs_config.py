import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lingtu_xhs_config.py"
spec = importlib.util.spec_from_file_location("xhs_config", SCRIPT)
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


class MaterialLibraryConfigTests(unittest.TestCase):
    def test_init_creates_default_and_preserves_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            default_library = root / "Lingtu" / "xhs-material-library"

            library, created = MODULE.initialize_material_library(config, default_library)
            self.assertTrue(created)
            self.assertTrue(library.is_dir())
            self.assertEqual(
                MODULE.read_config(config),
                {"materialLibrary": str(default_library.resolve())},
            )

            same_library, created_again = MODULE.initialize_material_library(
                config, root / "another-default"
            )
            self.assertFalse(created_again)
            self.assertEqual(same_library, default_library.resolve())
            self.assertFalse((root / "another-default").exists())

    def test_set_read_and_reset_material_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "brand"
            library.mkdir()
            config = root / "config.json"

            resolved = MODULE.set_material_library(str(library), config)
            self.assertEqual(resolved, library.resolve())
            self.assertEqual(
                MODULE.read_config(config),
                {"materialLibrary": str(library.resolve())},
            )

            MODULE.reset_material_library(config)
            self.assertFalse(config.exists())

    def test_rejects_missing_material_library(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaises(ValueError):
                MODULE.set_material_library(str(missing), Path(directory) / "config.json")


if __name__ == "__main__":
    unittest.main()
