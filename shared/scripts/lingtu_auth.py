#!/usr/bin/env python3
"""Shared auth helper for Lingtu skills.

Reads LINGTU_API_KEY from the environment. Users must configure the key
manually before running a skill.
"""

from __future__ import annotations

import os
import platform


def api_key_setup_instructions() -> str:
    if platform.system() == "Windows":
        return (
            'Set it in PowerShell with `$env:LINGTU_API_KEY = "your-api-key"` for the current session, '
            'or `[Environment]::SetEnvironmentVariable("LINGTU_API_KEY", "your-api-key", "User")` '
            "and then open a new terminal."
        )
    return (
        "Set it in Terminal with `export LINGTU_API_KEY='your-api-key'`. "
        "To keep it across sessions on macOS, add that line to `~/.zshrc` and run `source ~/.zshrc`."
    )


def require_api_key() -> str:
    key = os.environ.get("LINGTU_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "LINGTU_API_KEY environment variable is not set. "
            f"{api_key_setup_instructions()}"
        )
    return key
