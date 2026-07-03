#!/usr/bin/env python3
"""灵途批量视频发布 — TikTok Shop 带货 / TikTok 养号视频批量排期发布。

CLI 驱动：gen-csv → 用户编辑 CSV → publish --confirm
"""

from __future__ import annotations
import os, sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.cli import run

if __name__ == "__main__":
    run()
