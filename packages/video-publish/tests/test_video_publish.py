from pathlib import Path
import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib import api as api_module  # noqa: E402
from lib import cli as cli_module  # noqa: E402
from lib.cli import _timezone_from_creator_info, _validate_row, command_fill, command_gen_csv  # noqa: E402
from lib.config import PUBLISH_RECORDS_URL  # noqa: E402
from lib.excel_utils import parse_excel_or_csv, sanitize_post_title, sanitize_product_title  # noqa: E402
from lib.report import format_publish_results  # noqa: E402
from lib.scheduler import build_schedule_rows  # noqa: E402


class TimezoneInferenceTests(unittest.TestCase):
    def test_target_market_takes_priority_over_auth_region(self) -> None:
        tz = _timezone_from_creator_info({
            "targetMarket": "US",
            "oauthRegion": "GB",
            "registerRegion": "CN",
        })

        self.assertEqual(tz, "America/Los_Angeles")

    def test_unknown_region_defaults_to_us_west(self) -> None:
        self.assertEqual(_timezone_from_creator_info({"oauthRegion": "UNKNOWN"}), "America/Los_Angeles")


class ScheduleStaggerTests(unittest.TestCase):
    def test_schedule_keeps_morning_noon_evening_and_staggers_creators(self) -> None:
        rows = build_schedule_rows(
            dates=["2026-07-05"],
            creators=["alice", "bob"],
            platform="tiktok_shop",
            product_id="pid",
            timezone_by_creator={
                "alice": "America/Los_Angeles",
                "bob": "America/New_York",
            },
            count=3,
        )

        self.assertEqual(
            [row["scheduled_at"] for row in rows],
            [
                "2026-07-05 09:00",
                "2026-07-05 14:00",
                "2026-07-05 19:00",
                "2026-07-05 09:11",
                "2026-07-05 14:11",
                "2026-07-05 19:11",
            ],
        )
        self.assertEqual(rows[0]["timezone"], "America/Los_Angeles")
        self.assertEqual(rows[3]["timezone"], "America/New_York")


class ScheduleFileTests(unittest.TestCase):
    def test_csv_column_mapping_includes_product_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "schedule.csv"
            csv_path.write_text(
                "达人用户名,平台,产品ID,购物车标题,商品来源,视频文案内容,时区,发布时间,视频文件名\n"
                "alice,tiktok_shop,pid,Product,SHOWCASE,caption,America/Los_Angeles,2026-07-05 09:00,video.mp4\n",
                encoding="utf-8",
            )

            rows = parse_excel_or_csv(str(csv_path))

        self.assertEqual(rows[0]["creator_username"], "alice")
        self.assertEqual(rows[0]["product_source"], "SHOWCASE")
        self.assertEqual(rows[0]["scheduled_at"], "2026-07-05 09:00")


class TextLimitTests(unittest.TestCase):
    def test_sanitize_removes_emoji_symbols_and_truncates_lengths(self) -> None:
        self.assertEqual(sanitize_product_title("Great Product!🔥#1" * 3), "Great Product1Great Product1Gr")
        self.assertEqual(sanitize_post_title("Great caption #summer!🔥"), "Great caption #summer")
        self.assertEqual(len(sanitize_product_title("a" * 40)), 30)
        self.assertEqual(len(sanitize_post_title("a" * 4100)), 4000)

    def test_validate_rejects_unsupported_title_and_product_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "video.mp4").write_bytes(b"fake")
            row = {
                "creator_username": "alice",
                "platform": "tiktok_shop",
                "product_id": "pid",
                "product_title": "Good Product!",
                "title": "Nice caption 😊",
                "timezone": "America/Los_Angeles",
                "scheduled_at": "2026-07-05 09:00",
                "video_file": "video.mp4",
            }

            errors = _validate_row(row, 0, folder)

        self.assertTrue(any("title 不能超过 4000 字符" in error for error in errors))
        self.assertTrue(any("购物车标题不能超过 30 字符" in error for error in errors))

    def test_validate_allows_hashtag_in_post_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "video.mp4").write_bytes(b"fake")
            row = {
                "creator_username": "alice",
                "platform": "tiktok",
                "product_id": "",
                "product_title": "",
                "title": "Nice caption #summer",
                "timezone": "America/Los_Angeles",
                "scheduled_at": "2026-07-05 09:00",
                "video_file": "video.mp4",
            }

            errors = _validate_row(row, 0, folder)

        self.assertFalse(any("title 不能超过 4000 字符" in error for error in errors))

    def test_validate_rejects_long_post_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "video.mp4").write_bytes(b"fake")
            row = {
                "creator_username": "alice",
                "platform": "tiktok",
                "product_id": "",
                "product_title": "",
                "title": "a" * 4001,
                "timezone": "America/Los_Angeles",
                "scheduled_at": "2026-07-05 09:00",
                "video_file": "video.mp4",
            }

            errors = _validate_row(row, 0, folder)

        self.assertTrue(any("title 不能超过 4000 字符" in error for error in errors))


class CreatorRegionFlowTests(unittest.TestCase):
    def test_tiktok_shop_region_filters_creator_list(self) -> None:
        args = argparse.Namespace(
            platform="tiktok_shop",
            creators=None,
            date="2026-07-05",
            days=1,
            count=1,
            product_id="pid",
            timezone="",
            region="US",
            output_dir="/tmp/video-publish-test",
            dry_run=False,
            format="json",
        )

        with mock.patch.object(cli_module, "require_api_key"), \
                mock.patch.object(cli_module, "generate_csv_template", return_value="/tmp/video-publish-test/schedule.csv"), \
                mock.patch.object(cli_module, "list_creator_accounts", return_value={
                    "data": {
                        "list": [{
                            "username": "alice",
                            "targetMarket": "US",
                            "oauthRegion": "GB",
                        }]
                    }
                }) as list_creator_accounts, \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            command_gen_csv(args)

        list_creator_accounts.assert_called_once_with(platform="tiktok_shop", selection_region="US")
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["region_filter_applied"])
        self.assertEqual(payload["csv"], "/tmp/video-publish-test/schedule.csv")
        self.assertEqual(payload["timezones_by_creator"]["alice"], "America/Los_Angeles")

    def test_plain_tiktok_region_does_not_filter_creator_list_or_keep_product_id(self) -> None:
        args = argparse.Namespace(
            platform="tiktok",
            creators=None,
            date="2026-07-05",
            days=1,
            count=1,
            product_id="pid",
            timezone="",
            region="US",
            output_dir="/tmp/video-publish-test",
            dry_run=False,
            format="json",
        )

        captured_rows = []

        def fake_generate_csv_template(output_path: str, rows_data: list[dict[str, str]]) -> str:
            captured_rows.extend(rows_data)
            return output_path

        with mock.patch.object(cli_module, "require_api_key"), \
                mock.patch.object(cli_module, "generate_csv_template", side_effect=fake_generate_csv_template), \
                mock.patch.object(cli_module, "list_creator_accounts", return_value={
                    "data": {
                        "list": [{
                            "username": "alice",
                            "oauthRegion": "GB",
                        }]
                    }
                }) as list_creator_accounts, \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            command_gen_csv(args)

        list_creator_accounts.assert_called_once_with(platform="tiktok", selection_region=None)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["region_filter_applied"])
        self.assertEqual(payload["timezones_by_creator"]["alice"], "America/Los_Angeles")
        self.assertEqual(captured_rows[0]["product_id"], "")

    def test_daily_counts_generate_one_schedule_with_mixed_day_counts(self) -> None:
        args = argparse.Namespace(
            platform="tiktok",
            creators="alice,bob",
            date="2026-07-06",
            days=1,
            count=3,
            daily_counts="2026-07-06=2,2026-07-07=3",
            product_id="pid",
            timezone="",
            region="US",
            output_dir="/tmp/video-publish-test",
            dry_run=False,
            format="json",
        )
        captured_rows = []

        def fake_generate_csv_template(output_path: str, rows_data: list[dict[str, str]]) -> str:
            captured_rows.extend(rows_data)
            return output_path

        with mock.patch.object(cli_module, "require_api_key"), \
                mock.patch.object(cli_module, "generate_csv_template", side_effect=fake_generate_csv_template), \
                mock.patch.object(cli_module, "resolve_creator_batch", return_value=({
                    "alice": {"targetRegion": "US"},
                    "bob": {"targetRegion": "US"},
                }, [])), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            command_gen_csv(args)

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["dates"], ["2026-07-06", "2026-07-07"])
        self.assertEqual(payload["days"], 2)
        self.assertEqual(payload["daily_counts"], {"2026-07-06": 2, "2026-07-07": 3})
        self.assertEqual(len(captured_rows), 10)
        self.assertEqual(
            [row["scheduled_at"] for row in captured_rows],
            [
                "2026-07-06 09:00",
                "2026-07-06 14:00",
                "2026-07-06 09:11",
                "2026-07-06 14:11",
                "2026-07-07 09:00",
                "2026-07-07 14:00",
                "2026-07-07 19:00",
                "2026-07-07 09:11",
                "2026-07-07 14:11",
                "2026-07-07 19:11",
            ],
        )


class FillCommandTests(unittest.TestCase):
    def test_fill_row_zero_updates_first_csv_data_row_not_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            schedule_path = folder / "schedule.csv"
            schedule_path.write_text(
                "达人用户名,平台,视频文案内容\n"
                "alice,tiktok_shop,old\n"
                "bob,tiktok_shop,old\n",
                encoding="utf-8-sig",
            )

            args = argparse.Namespace(
                folder=str(folder),
                col="视频文案内容",
                value="new",
                row=0,
                creator=None,
                auto_product_title=False,
                format="text",
            )
            with contextlib.redirect_stdout(io.StringIO()):
                command_fill(args)

            rows = parse_excel_or_csv(str(schedule_path))
            self.assertEqual(rows[0]["title"], "new")
            self.assertEqual(rows[1]["title"], "old")


class UploadFileTests(unittest.TestCase):
    def test_upload_file_skips_confirm_for_existing_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"fake video")

            with mock.patch.object(api_module, "_put_file") as put_file, \
                    mock.patch.object(api_module, "_request_json", return_value={
                        "code": 0,
                        "data": {
                            "fileId": 123,
                            "url": "https://cdn.example/video.mp4",
                            "isNew": False,
                        },
                    }) as request_json:
                result = api_module.upload_file(str(video))

        put_file.assert_not_called()
        request_json.assert_called_once()
        self.assertEqual(result["id"], "123")
        self.assertEqual(result["url"], "https://cdn.example/video.mp4")

    def test_upload_file_confirms_new_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"fake video")

            with mock.patch.object(api_module, "_put_file") as put_file, \
                    mock.patch.object(api_module, "_request_json", side_effect=[
                        {
                            "code": 0,
                            "data": {
                                "fileId": 123,
                                "uploadUrl": "https://upload.example/video.mp4",
                                "url": "https://cdn.example/video.mp4",
                                "isNew": True,
                            },
                        },
                        {"code": 0, "data": {}},
                    ]) as request_json:
                result = api_module.upload_file(str(video))

        put_file.assert_called_once()
        self.assertEqual(request_json.call_count, 2)
        self.assertEqual(result["id"], "123")


class PublishReportTests(unittest.TestCase):
    def test_live_report_includes_completion_summary_and_records_url(self) -> None:
        text = format_publish_results({
            "mode": "live",
            "total": 2,
            "succeeded": 2,
            "failed_count": 0,
            "video_type": "带货",
            "records_url": PUBLISH_RECORDS_URL,
            "rows": [
                {
                    "status": "success",
                    "creator_username": "alice",
                    "platform": "tiktok_shop",
                    "title": "caption",
                    "scheduled_at": "2026-07-05 09:00",
                    "post_id": "p1",
                    "post_status": "SCHEDULED",
                },
                {
                    "status": "success",
                    "creator_username": "bob",
                    "platform": "tiktok_shop",
                    "title": "caption",
                    "scheduled_at": "2026-07-05 09:11",
                    "post_id": "p2",
                    "post_status": "SCHEDULED",
                },
            ],
        })

        self.assertIn("发布完成，发布 2 条 带货 视频。", text)
        self.assertIn("发布基本信息：", text)
        self.assertIn("请前往发布记录确认发布内容：", text)
        self.assertIn(PUBLISH_RECORDS_URL, text)

    def test_validation_rows_are_reported_as_needs_edit_not_failure(self) -> None:
        text = format_publish_results({
            "mode": "needs-edit",
            "total": 2,
            "dry_run_valid": 1,
            "needs_edit_count": 1,
            "failed_count": 0,
            "rows": [
                {
                    "status": "needs-edit",
                    "index": 3,
                    "creator_username": "",
                    "errors": ["title 为空"],
                }
            ],
        })

        self.assertIn("排期表需要修改", text)
        self.assertIn("不算发布失败", text)
        self.assertIn("需修改：", text)
        self.assertNotIn("失败：", text)


if __name__ == "__main__":
    unittest.main()
