from pathlib import Path
import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from typing import Optional


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.normalize import normalize_instagram_response  # noqa: E402
from lib.cli import command_batch_tag  # noqa: E402
from lib.utils import parse_creator_handle, slugify_handle  # noqa: E402


class HandleParsingTests(unittest.TestCase):
    def test_slugify_preserves_trailing_underscores(self) -> None:
        self.assertEqual(slugify_handle("arianaguerrero__"), "arianaguerrero__")
        self.assertEqual(slugify_handle("user.name_"), "user.name_")

    def test_slugify_handles_mentions_and_leading_noise(self) -> None:
        self.assertEqual(slugify_handle("@mrbeast"), "mrbeast")
        self.assertEqual(slugify_handle("_leading_dash"), "_leading_dash")

    def test_instagram_url_preserves_leading_and_trailing_underscores(self) -> None:
        self.assertEqual(
            parse_creator_handle(
                "https://www.instagram.com/arianaguerrero__/",
                platform="instagram",
            ),
            "arianaguerrero__",
        )
        self.assertEqual(
            parse_creator_handle(
                "https://www.instagram.com/_sophia.wellness_/",
                platform="instagram",
            ),
            "_sophia.wellness_",
        )


class InstagramNormalizeTests(unittest.TestCase):
    def test_instagram_author_counts_accept_legacy_edge_objects(self) -> None:
        normalized = normalize_instagram_response({
            "author": {
                "id": "1",
                "username": "creator",
                "edgeFollowedBy": {"count": "1234"},
                "edgeFollow": {"count": 56},
                "edgeOwnerToTimelineMedia": {"count": 78},
            },
            "posts": [],
        })

        self.assertEqual(normalized["creator"]["follower_count"], 1234)
        self.assertEqual(normalized["creator"]["following_count"], 56)
        self.assertEqual(normalized["creator"]["aweme_count"], 78)

    def test_instagram_author_counts_accept_direct_fields(self) -> None:
        normalized = normalize_instagram_response({
            "author": {
                "id": "1",
                "username": "arianaguerrero__",
                "followerCount": 24680,
                "followingCount": "135",
                "postsCount": "42",
            },
            "posts": [],
        })

        self.assertEqual(normalized["creator"]["username"], "arianaguerrero__")
        self.assertEqual(normalized["creator"]["follower_count"], 24680)
        self.assertEqual(normalized["creator"]["following_count"], 135)
        self.assertEqual(normalized["creator"]["aweme_count"], 42)


class BatchTagTests(unittest.TestCase):
    def test_batch_tag_replaces_tags_from_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "monitors.json"
            csv_path = Path(tmp) / "tags.csv"
            self._write_store(store_path)
            csv_path.write_text('input,tags\nalice,"小明,重点"\nbob,小红\n', encoding="utf-8")

            old_store = os.environ.get("LINGTU_SOCIAL_MONITOR_STORE")
            os.environ["LINGTU_SOCIAL_MONITOR_STORE"] = str(store_path)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    command_batch_tag(argparse.Namespace(
                        platform="instagram",
                        group_id="group",
                        input_file=str(csv_path),
                        append=False,
                        format="json",
                    ))
            finally:
                self._restore_store_env(old_store)

            data = json.loads(store_path.read_text(encoding="utf-8"))
            tags_by_user = {m["creator"]["username"]: m["tags"] for m in data["monitors"]}
            self.assertEqual(tags_by_user["alice"], ["小明", "重点"])
            self.assertEqual(tags_by_user["bob"], ["小红"])

    def test_batch_tag_accepts_unquoted_comma_separated_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "monitors.json"
            csv_path = Path(tmp) / "tags.csv"
            self._write_store(store_path)
            csv_path.write_text("input,tags\nalice,小明,重点\n", encoding="utf-8")

            old_store = os.environ.get("LINGTU_SOCIAL_MONITOR_STORE")
            os.environ["LINGTU_SOCIAL_MONITOR_STORE"] = str(store_path)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    command_batch_tag(argparse.Namespace(
                        platform="instagram",
                        group_id="group",
                        input_file=str(csv_path),
                        append=False,
                        format="json",
                    ))
            finally:
                self._restore_store_env(old_store)

            data = json.loads(store_path.read_text(encoding="utf-8"))
            alice = next(m for m in data["monitors"] if m["creator"]["username"] == "alice")
            self.assertEqual(alice["tags"], ["小明", "重点"])

    def test_batch_tag_accepts_whitespace_in_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "monitors.json"
            csv_path = Path(tmp) / "tags.csv"
            self._write_store(store_path)
            csv_path.write_text(" input , tags \nalice,小明,重点\n", encoding="utf-8")

            old_store = os.environ.get("LINGTU_SOCIAL_MONITOR_STORE")
            os.environ["LINGTU_SOCIAL_MONITOR_STORE"] = str(store_path)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    command_batch_tag(argparse.Namespace(
                        platform="instagram",
                        group_id="group",
                        input_file=str(csv_path),
                        append=False,
                        format="json",
                    ))
            finally:
                self._restore_store_env(old_store)

            data = json.loads(store_path.read_text(encoding="utf-8"))
            alice = next(m for m in data["monitors"] if m["creator"]["username"] == "alice")
            self.assertEqual(alice["tags"], ["小明", "重点"])

    def test_batch_tag_appends_and_deduplicates_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "monitors.json"
            csv_path = Path(tmp) / "tags.csv"
            self._write_store(store_path)
            csv_path.write_text('input,tags\nalice,"旧标签,重点"\n', encoding="utf-8")

            old_store = os.environ.get("LINGTU_SOCIAL_MONITOR_STORE")
            os.environ["LINGTU_SOCIAL_MONITOR_STORE"] = str(store_path)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    command_batch_tag(argparse.Namespace(
                        platform="instagram",
                        group_id="group",
                        input_file=str(csv_path),
                        append=True,
                        format="json",
                    ))
            finally:
                self._restore_store_env(old_store)

            data = json.loads(store_path.read_text(encoding="utf-8"))
            alice = next(m for m in data["monitors"] if m["creator"]["username"] == "alice")
            self.assertEqual(alice["tags"], ["旧标签", "小明", "重点"])

    def _write_store(self, path: Path) -> None:
        path.write_text(json.dumps({
            "monitors": [
                {
                    "monitor_id": "m1",
                    "source": "test",
                    "group_id": "group",
                    "team_id": "",
                    "operator_id": "tester",
                    "remark": "",
                    "tags": ["旧标签", "小明"],
                    "added_at": "2026-06-23T00:00:00Z",
                    "updated_at": "2026-06-23T00:00:00Z",
                    "daily_enabled": True,
                    "alert_config": {},
                    "creator": {"platform": "instagram", "username": "alice", "creator_id": "1"},
                },
                {
                    "monitor_id": "m2",
                    "source": "test",
                    "group_id": "group",
                    "team_id": "",
                    "operator_id": "tester",
                    "remark": "",
                    "tags": [],
                    "added_at": "2026-06-23T00:00:00Z",
                    "updated_at": "2026-06-23T00:00:00Z",
                    "daily_enabled": True,
                    "alert_config": {},
                    "creator": {"platform": "instagram", "username": "bob", "creator_id": "2"},
                },
            ]
        }, ensure_ascii=False), encoding="utf-8")

    def _restore_store_env(self, old_store: Optional[str]) -> None:
        if old_store is None:
            os.environ.pop("LINGTU_SOCIAL_MONITOR_STORE", None)
        else:
            os.environ["LINGTU_SOCIAL_MONITOR_STORE"] = old_store


if __name__ == "__main__":
    unittest.main()
