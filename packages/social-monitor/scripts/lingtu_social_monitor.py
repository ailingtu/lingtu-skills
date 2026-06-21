#!/usr/bin/env python3
"""跨平台达人监控、素材数据与每日内容情报报告（TikTok / Instagram）。

实现拆分到同目录的 `lib/` 包；本文件仅作为 CLI 入口。
"""

from __future__ import annotations

import os
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.cli import run


if __name__ == "__main__":
    run()
