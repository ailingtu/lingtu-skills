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
from lib.api import creator_can_publish_photo, is_tiktok_shop_auth_source, normalize_permission_list  # noqa: E402
from lib.cli import (  # noqa: E402
    _row_media_type,
    _timezone_from_creator_info,
    _validate_row,
    command_fill,
    command_gen_csv,
)
from lib.config import (  # noqa: E402
    PHOTO_MAX_FILE_BYTES,
    PHOTO_MAX_IMAGES,
    PHOTO_SHOPPABLE_PERMISSION,
    PUBLISH_RECORDS_URL,
)
from lib.excel_utils import parse_excel_or_csv, sanitize_post_title, sanitize_product_title  # noqa: E402
from lib.image_utils import read_image_dimensions, validate_photo_files  # noqa: E402
from lib.report import format_publish_results  # noqa: E402
from lib.scheduler import build_schedule_rows  # noqa: E402


def _write_png(path: Path, width: int, height: int) -> None:
    """写一个最小合法 RGB PNG，用于尺寸/格式校验测试。"""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = b"\x00" + (b"\xff\x00\x00" * width)
    raw = row * height
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


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

    def test_csv_accepts_media_type_column_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "schedule.csv"
            csv_path.write_text(
                "达人用户名,平台,媒体类,产品ID,购物车标题,视频文案内容,时区,发布时间,图片文件名\n"
                "alice,tiktok_shop,图文,pid,Product,caption,America/New_York,2026-07-05 09:00,a.png\n",
                encoding="utf-8-sig",
            )
            rows = parse_excel_or_csv(str(csv_path))
        self.assertEqual(rows[0]["media_type"], "图文")

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "schedule.csv"
            csv_path.write_text(
                "达人用户名,平台,媒体类型,视频文案内容,时区,发布时间,视频文件名\n"
                "bob,tiktok,video,caption,America/New_York,2026-07-05 09:00,v.mp4\n",
                encoding="utf-8-sig",
            )
            rows = parse_excel_or_csv(str(csv_path))
        self.assertEqual(rows[0]["media_type"], "video")


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
            media_type="video",
            creators=None,
            date="2026-07-05",
            days=1,
            count=1,
            daily_counts="",
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

        list_creator_accounts.assert_called_once_with(
            platform="tiktok_shop",
            selection_region="US",
            has_photo_permission=None,
        )
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["region_filter_applied"])
        self.assertEqual(payload["csv"], "/tmp/video-publish-test/schedule.csv")
        self.assertEqual(payload["timezones_by_creator"]["alice"], "America/Los_Angeles")

    def test_plain_tiktok_region_does_not_filter_creator_list_or_keep_product_id(self) -> None:
        args = argparse.Namespace(
            platform="tiktok",
            media_type="video",
            creators=None,
            date="2026-07-05",
            days=1,
            count=1,
            daily_counts="",
            product_id="pid",
            timezone="",
            region="US",
            output_dir="/tmp/video-publish-test",
            dry_run=False,
            format="json",
        )

        captured_rows = []

        def fake_generate_csv_template(output_path: str, rows_data: list[dict[str, str]], **kwargs) -> str:
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

        list_creator_accounts.assert_called_once_with(
            platform="tiktok",
            selection_region=None,
            has_photo_permission=None,
        )
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["region_filter_applied"])
        self.assertEqual(payload["timezones_by_creator"]["alice"], "America/Los_Angeles")
        self.assertEqual(captured_rows[0]["product_id"], "")

    def test_daily_counts_generate_one_schedule_with_mixed_day_counts(self) -> None:
        args = argparse.Namespace(
            platform="tiktok",
            media_type="video",
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

        def fake_generate_csv_template(output_path: str, rows_data: list[dict[str, str]], **kwargs) -> str:
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


class MediaTypeInferenceTests(unittest.TestCase):
    def test_image_suffix_in_video_file_does_not_imply_photo(self) -> None:
        row = {
            "platform": "tiktok_shop",
            "video_file": "cover.jpg",
            "image_files": "",
            "media_type": "",
        }
        self.assertEqual(_row_media_type(row), "video")

    def test_image_files_without_media_type_implies_photo(self) -> None:
        row = {
            "platform": "tiktok_shop",
            "video_file": "",
            "image_files": "a.jpg,b.png",
            "media_type": "",
        }
        self.assertEqual(_row_media_type(row), "photo")

    def test_validate_video_row_with_image_in_video_file_column_is_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "cover.jpg").write_bytes(b"x")
            row = {
                "creator_username": "alice",
                "platform": "tiktok_shop",
                "media_type": "video",
                "product_id": "pid",
                "product_title": "Good Product",
                "title": "caption",
                "timezone": "America/New_York",
                "scheduled_at": "2026-07-05 09:00",
                "video_file": "cover.jpg",
                "image_files": "",
            }
            errors = _validate_row(row, 0, folder)
        self.assertTrue(any("看起来是图片" in e and "图片文件名" in e for e in errors))

    def test_validate_photo_requires_image_files_column_not_video_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            _write_png(folder / "a.png", 100, 100)
            row = {
                "creator_username": "alice",
                "platform": "tiktok_shop",
                "media_type": "photo",
                "product_id": "pid",
                "product_title": "Good Product",
                "title": "caption",
                "timezone": "America/New_York",
                "scheduled_at": "2026-07-05 09:00",
                "video_file": "a.png",
                "image_files": "",
            }
            errors = _validate_row(row, 0, folder)
        self.assertTrue(any("图片文件名" in e and "不要写在「视频文件名」" in e for e in errors))


class PhotoPermissionTests(unittest.TestCase):
    def test_list_creator_accounts_sends_has_photo_permission(self) -> None:
        captured: dict = {}

        def fake_request(method, path, query_params=None, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["query"] = query_params or {}
            return {"code": 0, "data": {"list": []}}

        with mock.patch.object(api_module, "_request_json", side_effect=fake_request):
            api_module.list_creator_accounts(platform="tiktok_shop", has_photo_permission=True)
            api_module.list_creator_accounts(platform="tiktok_shop")

        # 最后一次调用未传 hasPhotoPermission
        self.assertNotIn("hasPhotoPermission", captured["query"])

        with mock.patch.object(api_module, "_request_json", side_effect=fake_request):
            api_module.list_creator_accounts(has_photo_permission=True)
        self.assertEqual(captured["query"].get("hasPhotoPermission"), "true")
        self.assertEqual(captured["method"], "GET")

    def test_is_tiktok_shop_auth_source(self) -> None:
        self.assertTrue(is_tiktok_shop_auth_source("TIKTOK_SHOP"))
        self.assertTrue(is_tiktok_shop_auth_source("TIKTOK_SHOP_CREATOR"))
        self.assertFalse(is_tiktok_shop_auth_source("TIKTOK_LOGIN_KIT"))
        self.assertFalse(is_tiktok_shop_auth_source(""))

    def test_normalize_permission_list_variants(self) -> None:
        self.assertEqual(
            normalize_permission_list("A,B;C"),
            ["A", "B", "C"],
        )
        self.assertEqual(
            normalize_permission_list([{"permissionCode": "PHOTO_SHOPPABLE_PERMISSION_PRODUCT"}]),
            [PHOTO_SHOPPABLE_PERMISSION],
        )

    def test_creator_can_publish_photo_requires_shop_and_permission(self) -> None:
        ok, _ = creator_can_publish_photo({
            "username": "alice",
            "authSource": "TIKTOK_SHOP",
            "permissions": [PHOTO_SHOPPABLE_PERMISSION],
        })
        self.assertTrue(ok)

        ok, reason = creator_can_publish_photo({
            "username": "bob",
            "authSource": "TIKTOK_LOGIN_KIT",
            "permissions": [PHOTO_SHOPPABLE_PERMISSION],
        })
        self.assertFalse(ok)
        self.assertIn("不是 TikTok Shop", reason)

        ok, reason = creator_can_publish_photo({
            "username": "carol",
            "authSource": "TIKTOK_SHOP_CREATOR",
            "permissions": ["OTHER"],
        })
        self.assertFalse(ok)
        self.assertIn(PHOTO_SHOPPABLE_PERMISSION, reason)


class PhotoPostApiTests(unittest.TestCase):
    def test_create_post_video_sends_media_type_video(self) -> None:
        captured: dict = {}

        def fake_request(method, path, body=None, **kwargs):
            captured["body"] = body
            return {"code": 0, "data": {"postId": "p-video", "status": "SCHEDULED"}}

        with mock.patch.object(api_module, "_request_json", side_effect=fake_request):
            api_module.create_post(
                creator_id="c1",
                title="caption",
                business_id="file1",
                platform="tiktok_shop",
                product_id="pid",
                product_title="Product",
                product_source="SHOP",
            )

        self.assertEqual(captured["body"]["mediaType"], "VIDEO")
        self.assertIn("tiktokShop", captured["body"])
        self.assertNotIn("tiktokShopPhoto", captured["body"])

    def test_create_post_photo_builds_tiktok_shop_photo_body(self) -> None:
        captured: dict = {}

        def fake_request(method, path, body=None, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["body"] = body
            return {"code": 0, "data": {"postId": "p1", "status": "SCHEDULED"}}

        with mock.patch.object(api_module, "_request_json", side_effect=fake_request):
            result = api_module.create_post(
                creator_id="2077242233106595840",
                title="test #12341234",
                business_id="591",
                platform="tiktok_shop",
                scheduled_at=1784896665989,
                scheduled_tz="America/New_York",
                product_id="1732280564607717841",
                product_title="Summer Vibes 2026 Vacease Cord",
                product_source="SHOP",
                media_type="PHOTO",
                business_ids=["591", "592"],
                music_info={
                    "id": "7567668059796720391",
                    "title": "original sound - ivaaan_beltran",
                    "author": "Ivan",
                    "duration": "15",
                },
            )

        self.assertEqual(result["postId"], "p1")
        self.assertEqual(captured["method"], "POST")
        body = captured["body"]
        self.assertEqual(body["mediaType"], "PHOTO")
        self.assertEqual(body["businessId"], "591")
        self.assertEqual(body["platform"], "TIKTOK_SHOP")
        self.assertNotIn("tiktokShop", body)
        photo = body["tiktokShopPhoto"]
        self.assertEqual(photo["postType"], "MULTI_PHOTO_ONE_ANCHOR")
        self.assertEqual(photo["businessIds"], ["591", "592"])
        self.assertEqual(len(photo["productLinks"]), 1)
        self.assertEqual(photo["productLinks"][0]["productId"], "1732280564607717841")
        self.assertEqual(photo["musicInfo"]["id"], "7567668059796720391")
        # businessId 默认首图；businessIds 保持上传顺序
        self.assertEqual(body["businessId"], photo["businessIds"][0])

    def test_create_post_photo_rejects_multiple_product_links(self) -> None:
        with mock.patch.object(api_module, "_request_json") as request_json:
            with self.assertRaises(SystemExit) as ctx:
                api_module.create_post(
                    creator_id="c1",
                    title="caption",
                    business_id="1",
                    platform="tiktok_shop",
                    media_type="PHOTO",
                    business_ids=["1", "2"],
                    product_links=[
                        {"productId": "p1", "title": "A", "source": "SHOP"},
                        {"productId": "p2", "title": "B", "source": "SHOP"},
                    ],
                )
        request_json.assert_not_called()
        self.assertIn("只能有 1 个产品", str(ctx.exception))

    def test_validate_photo_row_accepts_multi_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            _write_png(folder / "a.png", 1080, 1920)  # 9:16
            _write_png(folder / "b.png", 1920, 1080)  # 16:9
            row = {
                "creator_username": "alice",
                "platform": "tiktok_shop",
                "media_type": "photo",
                "product_id": "pid",
                "product_title": "Good Product",
                "title": "Nice caption #summer",
                "timezone": "America/New_York",
                "scheduled_at": "2026-07-05 09:00",
                "image_files": "a.png,b.png",
                "music_id": "7567668059796720391",
                "music_title": "original sound",
                "music_author": "Ivan",
                "music_duration": "15",
            }
            errors = _validate_row(row, 0, folder)
        self.assertEqual(errors, [])

    def test_validate_photo_requires_tiktok_shop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            _write_png(folder / "a.png", 1000, 1000)
            row = {
                "creator_username": "alice",
                "platform": "tiktok",
                "media_type": "photo",
                "title": "caption",
                "timezone": "America/New_York",
                "scheduled_at": "2026-07-05 09:00",
                "image_files": "a.png",
            }
            errors = _validate_row(row, 0, folder)
        self.assertTrue(any("仅支持 platform=tiktok_shop" in e for e in errors))

    def test_validate_photo_rejects_too_many_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            names = []
            for i in range(PHOTO_MAX_IMAGES + 1):
                name = f"p{i}.png"
                _write_png(folder / name, 100, 100)
                names.append(name)
            row = {
                "creator_username": "alice",
                "platform": "tiktok_shop",
                "media_type": "photo",
                "product_id": "pid",
                "product_title": "Good Product",
                "title": "caption",
                "timezone": "America/New_York",
                "scheduled_at": "2026-07-05 09:00",
                "image_files": ",".join(names),
            }
            errors = _validate_row(row, 0, folder)
        self.assertTrue(any("最多 15 张" in e for e in errors))

    def test_validate_photo_rejects_bad_aspect_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            # 超竖：1:10 < 9:16
            _write_png(folder / "tall.png", 100, 1000)
            errors = validate_photo_files([folder / "tall.png"])
        self.assertTrue(any("宽高比" in e for e in errors))

    def test_validate_photo_rejects_oversize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            path = folder / "big.png"
            _write_png(path, 100, 100)
            # 在合法 PNG 后追加填充，超过 10MB，仍可被识别为 PNG 尺寸
            path.write_bytes(path.read_bytes() + b"\x00" * (PHOTO_MAX_FILE_BYTES + 1))
            errors = validate_photo_files([path])
        self.assertTrue(any("10MB" in e for e in errors))

    def test_validate_photo_rejects_unsupported_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            path = folder / "x.gif"
            path.write_bytes(b"GIF89a")
            errors = validate_photo_files([path])
        self.assertTrue(any("格式不支持" in e for e in errors))

    def test_read_png_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.png"
            _write_png(path, 640, 360)
            self.assertEqual(read_image_dimensions(path), (640, 360))


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

    def test_photo_report_uses_photo_wording(self) -> None:
        text = format_publish_results({
            "mode": "live",
            "total": 1,
            "succeeded": 1,
            "failed_count": 0,
            "video_type": "带货图文",
            "records_url": PUBLISH_RECORDS_URL,
            "rows": [{
                "status": "success",
                "creator_username": "alice",
                "platform": "tiktok_shop",
                "media_type": "photo",
                "title": "caption",
                "scheduled_at": "2026-07-05 09:00",
                "post_id": "p1",
                "post_status": "SCHEDULED",
            }],
        })
        self.assertIn("发布完成，发布 1 条带货图文。", text)

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
