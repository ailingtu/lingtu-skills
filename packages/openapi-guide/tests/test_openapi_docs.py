from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "lingtu_openapi_docs.py"
SPEC = importlib.util.spec_from_file_location("lingtu_openapi_docs", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


INDEX = {
    "version": "1.9.0",
    "lastUpdated": "2026-09-01",
    "operations": [
        {
            "operationId": "createFileUpload",
            "method": "POST",
            "path": "/v1/file/presign",
            "summary": "Create a presigned file upload",
            "tags": ["File Upload"],
        },
        {
            "operationId": "listCreatorAccounts",
            "method": "GET",
            "path": "/v1/creatorAccount/pageList",
            "summary": "List authorized creator accounts",
            "tags": ["Commerce Publishing"],
        },
    ],
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def fake_urlopen(request, timeout):
    del timeout
    assert request.headers.get("X-api-key") is None
    path = request.full_url.removeprefix("https://docs.example")
    payloads = {
        "/openapi/operations/index.json": json.dumps(INDEX).encode(),
        "/openapi/operations/createFileUpload.md": b"# Create a presigned file upload\n",
        "/openapi/operations/createFileUpload.json": json.dumps(
            {"openapi": "3.1.2", "paths": {}}
        ).encode(),
        "/openapi/workflows/ai-generation.md": b"# AI generation workflow\n",
    }
    return FakeResponse(payloads[path])


class OpenApiDocsTest(unittest.TestCase):
    def run_main(self, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(MODULE, "urlopen", fake_urlopen),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = MODULE.main(["--base-url", "https://docs.example", *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_searches_operation_index(self):
        code, stdout, stderr = self.run_main("search", "file upload")
        self.assertEqual(code, 0)
        self.assertIn("createFileUpload", stdout)
        self.assertNotIn("listCreatorAccounts", stdout)
        self.assertEqual(stderr, "")

    def test_reads_markdown_and_json_operation_documents(self):
        code, stdout, _ = self.run_main("get", "createFileUpload")
        self.assertEqual(code, 0)
        self.assertIn("presigned file upload", stdout)

        code, stdout, _ = self.run_main("get", "createFileUpload", "--format", "json")
        self.assertEqual(code, 0)
        self.assertIn('"openapi": "3.1.2"', stdout)

    def test_reads_workflow(self):
        code, stdout, _ = self.run_main("workflow", "ai-generation")
        self.assertEqual(code, 0)
        self.assertIn("AI generation workflow", stdout)


if __name__ == "__main__":
    unittest.main()
