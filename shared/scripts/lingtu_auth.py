#!/usr/bin/env python3
"""Read only LINGTU_API_KEY from the environment for authenticated Lingtu requests."""

from __future__ import annotations

import os
from pathlib import Path


def require_api_key() -> str:
    key = os.environ.get("LINGTU_API_KEY", "").strip()
    if not key:
        guide = Path(__file__).resolve().parents[1] / "references" / "api-key-setup.md"
        raise SystemExit(guide.read_text(encoding="utf-8"))
    return key
