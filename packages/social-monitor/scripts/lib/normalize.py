"""把 TikTok / Instagram 原始响应规范化为统一形状。"""

from __future__ import annotations

from typing import Any

from .config import DEFAULT_PLATFORM
from .utils import (
    extract_hashtags,
    iso_utc_from_epoch_seconds,
    normalize_platform,
    seconds_from_duration,
    to_int,
)


def normalize_response(data: dict[str, Any], platform: str = DEFAULT_PLATFORM) -> dict[str, Any]:
    platform = normalize_platform(platform)
    if platform == "instagram":
        return normalize_instagram_response(data)
    author = data.get("authorInfo") or {}
    unique_id = author.get("uniqueId") or ""
    creator = {
        "platform": platform,
        "creator_id": str(author.get("id") or ""),
        "username": unique_id,
        "nickname": author.get("nickname") or unique_id,
        "profile_url": f"https://www.tiktok.com/@{unique_id}" if unique_id else "",
        "signature": author.get("signature") or "",
        "follower_count": author.get("followerCount"),
        "following_count": author.get("followingCount"),
        "aweme_count": author.get("awemeCount"),
        "total_favorited": author.get("totalFavorited"),
    }

    videos = []
    for post in data.get("posts") or []:
        stats = post.get("stats") or {}
        video_id = str(post.get("videoId") or "")
        caption = post.get("desc") or ""
        videos.append({
            "video_id": video_id,
            "video_url": f"https://www.tiktok.com/@{unique_id}/video/{video_id}" if unique_id and video_id else "",
            "caption": caption,
            "publish_time": iso_utc_from_epoch_seconds(post.get("createTime")),
            "duration": round((post.get("duration") or 0) / 1000, 2),
            "is_ad": bool(post.get("isAd")),
            "views": int(stats.get("playCount") or 0),
            "likes": int(stats.get("diggCount") or 0),
            "comments": int(stats.get("commentCount") or 0),
            "shares": int(stats.get("shareCount") or 0),
            "saves": int(stats.get("collectCount") or 0),
            "reposts": int(stats.get("repostCount") or 0),
            "cover_url": post.get("cover") or "",
            "play_url": post.get("playAddr") or "",
            "hashtags": extract_hashtags(caption),
        })

    return {
        "creator": creator,
        "videos": videos,
        "cursor": data.get("cursor"),
        "has_more": bool(data.get("hasMore")),
    }


def instagram_post_url(short_code: str) -> str:
    if not short_code:
        return ""
    return f"https://www.instagram.com/p/{short_code}/"


def instagram_edge_count(value: Any) -> int | None:
    if isinstance(value, dict):
        for key in ("count", "total_count", "totalCount"):
            if key in value and value[key] is not None:
                return to_int(value[key])
    if isinstance(value, (int, float, str)):
        return to_int(value)
    return None


def instagram_author_count(author: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in author and author[key] is not None:
            count = instagram_edge_count(author[key])
            if count is not None:
                return count
    return None


def normalize_instagram_post(item: dict[str, Any]) -> dict[str, Any]:
    short_code = str(item.get("shortCode") or "")
    video_id = str(item.get("postId") or short_code or "")
    caption = str(item.get("caption") or "")
    # IG 列表 (fetchPosts) 仅在视频帖子上返回播放/点赞计数；图片或图集多为 null。
    views = item.get("videoPlayCount")
    if views is None:
        views = item.get("videoViewCount")
    return {
        "video_id": video_id,
        "video_url": instagram_post_url(short_code),
        "caption": caption,
        "publish_time": iso_utc_from_epoch_seconds(item.get("takenAtTimestamp")),
        "duration": seconds_from_duration(item.get("videoDuration")),
        "is_ad": False,
        "is_video": bool(item.get("isVideo")),
        "views": to_int(views),
        "likes": to_int(item.get("likeCount")),
        "comments": to_int(item.get("commentCount")),
        "shares": 0,
        "saves": 0,
        "reposts": 0,
        "cover_url": str(item.get("displayUrl") or item.get("thumbnailSrc") or ""),
        "play_url": str(item.get("videoUrl") or ""),
        "hashtags": extract_hashtags(caption),
    }


def normalize_instagram_response(data: dict[str, Any]) -> dict[str, Any]:
    author = data.get("author") or {}
    posts = data.get("posts") or []
    if not isinstance(posts, list):
        posts = []

    unique_id = str(author.get("username") or "")
    creator_id = str(author.get("id") or "")
    nickname = str(author.get("fullName") or unique_id)
    creator = {
        "platform": "instagram",
        "creator_id": creator_id,
        "username": unique_id,
        "nickname": nickname,
        "profile_url": f"https://www.instagram.com/{unique_id}/" if unique_id else "",
        "signature": str(author.get("biography") or ""),
        "follower_count": instagram_author_count(
            author,
            "edgeFollowedBy",
            "followerCount",
            "followersCount",
            "followers",
            "follower_count",
        ),
        "following_count": instagram_author_count(
            author,
            "edgeFollow",
            "followingCount",
            "followCount",
            "following",
            "following_count",
        ),
        "aweme_count": instagram_author_count(
            author,
            "edgeOwnerToTimelineMedia",
            "postCount",
            "postsCount",
            "mediaCount",
            "awemeCount",
            "aweme_count",
        ),
        "total_favorited": None,
    }
    videos = [normalize_instagram_post(item) for item in posts if isinstance(item, dict)]
    return {
        "creator": creator,
        "videos": videos,
        "cursor": data.get("endCursor"),
        "has_more": bool(data.get("hasMore")),
    }


def normalize_material_response(payload: dict[str, Any], platform: str = DEFAULT_PLATFORM) -> dict[str, Any]:
    platform = normalize_platform(platform)
    if platform == "instagram":
        return normalize_instagram_material_response(payload)
    data = payload.get("data") or payload
    video_id = str(data.get("videoId") or "")
    unique_id = data.get("uniqueId") or ""
    desc = data.get("videoDesc") or ""
    return {
        "video": {
            "platform": platform,
            "video_id": video_id,
            "video_url": f"https://www.tiktok.com/@{unique_id}/video/{video_id}" if unique_id and video_id else "",
            "username": unique_id,
            "sec_uid": data.get("secUid") or "",
            "caption": desc,
            "description_language": data.get("descLanguage"),
            "publish_time": iso_utc_from_epoch_seconds(data.get("releaseAt")),
            "duration": round((data.get("duration") or 0) / 1000, 2),
            "is_ec_video": data.get("isEcVideo"),
            "is_ad": data.get("isAds"),
            "region": data.get("region"),
            "music_id": data.get("musicId"),
            "music_title": data.get("musicTitle"),
            "views": int(data.get("playCount") or 0),
            "likes": int(data.get("diggCount") or 0),
            "comments": int(data.get("commentCount") or 0),
            "shares": int(data.get("shareCount") or 0),
            "saves": int(data.get("collectCount") or 0),
            "downloads": int(data.get("downloadCount") or 0),
            "forwards": int(data.get("forwardCount") or 0),
            "cover_url": data.get("coverUrl") or "",
            "play_url": data.get("playAddr") or "",
            "download_url": data.get("downloadAddr") or "",
            "hashtags": extract_hashtags(desc),
        },
        "timestamp": payload.get("timestamp"),
    }


def normalize_instagram_material_response(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    owner = data.get("owner") or {}
    music = data.get("musicInfo") or {}
    short_code = str(data.get("shortCode") or "")
    video_id = str(data.get("postId") or short_code or "")
    username = str(owner.get("username") or "")
    caption = str(data.get("caption") or "")
    views = data.get("videoPlayCount")
    if views is None:
        views = data.get("videoViewCount")
    return {
        "video": {
            "platform": "instagram",
            "video_id": video_id,
            "video_url": instagram_post_url(short_code),
            "username": username,
            "sec_uid": "",
            "caption": caption,
            "description_language": None,
            "publish_time": iso_utc_from_epoch_seconds(data.get("takenAtTimestamp")),
            "duration": seconds_from_duration(data.get("videoDuration")),
            "is_ec_video": None,
            "is_ad": False,
            "is_video": bool(data.get("isVideo")),
            "region": None,
            "music_id": music.get("audioId"),
            "music_title": music.get("songName"),
            "views": to_int(views),
            "likes": to_int(data.get("likeCount")),
            "comments": to_int(data.get("commentCount")),
            "shares": 0,
            "saves": 0,
            "downloads": 0,
            "forwards": 0,
            "cover_url": str(data.get("displayUrl") or data.get("thumbnailSrc") or ""),
            "play_url": str(data.get("videoUrl") or ""),
            "download_url": "",
            "hashtags": extract_hashtags(caption),
        },
        "timestamp": payload.get("timestamp"),
    }


def coerce_normalized(data: dict[str, Any], platform: str = DEFAULT_PLATFORM) -> dict[str, Any]:
    platform = normalize_platform(platform)
    if "videos" in data and "creator" in data:
        return data
    if "posts" in data and "authorInfo" in data:
        return normalize_response(data, platform=platform)
    if platform == "instagram" and any(key in data for key in ("posts", "items", "videos", "medias")):
        return normalize_response(data, platform=platform)
    if isinstance(data.get("data"), dict) and any(key in data["data"] for key in ("posts", "items", "videos", "medias")):
        return normalize_response(data["data"], platform=platform)
    raise SystemExit("无法识别的输入 JSON：需要 fetchPosts 响应或 normalize 后的结构。")
