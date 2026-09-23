import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "catalog", Path(__file__).resolve().parents[1] / "scripts/lingtu_skill_catalog.py")
CATALOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CATALOG)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.skill = {"slug": "future-skill", "packageName": "lingtu-future-skill",
                      "version": "1.0.0", "locales": {"zh-CN": {"title": "新技能"}}}

    def test_fetch_future_entries_without_authentication(self):
        with patch.object(CATALOG, "urlopen", return_value=io.BytesIO(
            json.dumps({"skills": [self.skill]}).encode())) as request:
            self.assertEqual(CATALOG.fetch_catalog(), [self.skill])
        self.assertEqual(request.call_args.args[0].full_url, CATALOG.CATALOG_URL)
        self.assertEqual(request.call_args.args[0].header_items(), [("Accept", "application/json")])

    def test_invalid_response_is_not_empty_catalog(self):
        for data in ({}, {"skills": None}, {"skills": [{}]}):
            with self.subTest(data=data), patch.object(CATALOG, "urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
                with self.assertRaises(ValueError):
                    CATALOG.fetch_catalog()

    def test_get_exact_identity_and_locale_fallback(self):
        for name in ("future-skill", "lingtu-future-skill"):
            output = io.StringIO()
            with patch.object(CATALOG, "fetch_catalog", return_value=[self.skill]), contextlib.redirect_stdout(output):
                self.assertEqual(CATALOG.main(["get", name, "--locale", "en-US"]), 0)
            skill = json.loads(output.getvalue())["skills"][0]
            self.assertEqual(skill["title"], "新技能")
            self.assertEqual(skill["locale"], "zh-CN")
            self.assertIsNone(skill["auth"])

    def test_not_found_and_network_failure_have_distinct_exit_codes(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with patch.object(CATALOG, "fetch_catalog", return_value=[self.skill]):
                self.assertEqual(CATALOG.main(["get", "future"]), 2)
            with patch.object(CATALOG, "fetch_catalog", side_effect=OSError("offline")):
                self.assertEqual(CATALOG.main(["list"]), 1)


if __name__ == "__main__":
    unittest.main()
