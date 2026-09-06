#!/usr/bin/env python3
"""Shared auth helper for Lingtu skills.

Reads LINGTU_API_KEY from the environment. Users must configure the key
manually before running a skill.
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
            "Run `python3 shared/scripts/user_keys.py single bind` from the Skill root "
            "and open the generated authorization URL."
        )
    return key


def build_single_user_bind_url(
    channel: str = "local",
    user_id: str = "",
    remark: str = "",
) -> str:
    """Build the browser URL used to bind a local user to Lingtu AI."""
    source = (channel or "local").strip().lower()
    local_user_id = (user_id or "").strip()
    if not local_user_id:
        local_user_id = f"local_{secrets.token_urlsafe(18).replace('-', '_')}"
    params = {
        "token": secrets.token_urlsafe(16),
        "platform": source,
        "userid": local_user_id,
    }
    if remark:
        params["remark"] = remark
    return f"{DEFAULT_SITE_URL}/binduser?{urllib.parse.urlencode(params)}"
