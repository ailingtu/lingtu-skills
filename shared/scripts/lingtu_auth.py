#!/usr/bin/env python3
"""Shared auth helper for Lingtu skills.

Reads LINGTU_API_KEY from the environment. OpenClaw injects this
automatically; standalone CLI users export it themselves.
"""

from __future__ import annotations

import os
import secrets
import urllib.parse

DEFAULT_SITE_URL = "https://app.ailingtu.com"


def require_api_key() -> str:
    key = os.environ.get("LINGTU_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "LINGTU_API_KEY environment variable is not set. "
            "Run `python3 shared/scripts/user_keys.py single bind` "
            "to generate a bind URL, or export LINGTU_API_KEY=xxx."
        )
    return key


def build_single_user_bind_url(
    channel: str = "local",
    user_id: str = "",
    remark: str = "",
) -> str:
    platform = (channel or "local").strip().lower()
    uid = (user_id or "").strip()
    if not uid:
        uid = f"local_{secrets.token_urlsafe(18).replace('-', '_')}"
    token = secrets.token_urlsafe(16)
    params: dict[str, str] = {
        "token": token,
        "platform": platform,
        "userid": uid,
    }
    if remark:
        params["remark"] = remark
    return f"{DEFAULT_SITE_URL}/binduser?{urllib.parse.urlencode(params)}"
