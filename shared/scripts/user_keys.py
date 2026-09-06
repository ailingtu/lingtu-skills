#!/usr/bin/env python3
"""Generate a Lingtu account-binding URL without handling API keys."""

from __future__ import annotations

import argparse
import sys

from lingtu_auth import build_single_user_bind_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Lingtu account-binding URL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    single_parser = subparsers.add_parser("single", help="Single-user operations.")
    single_commands = single_parser.add_subparsers(dest="single_command", required=True)
    bind_command = single_commands.add_parser("bind", help="Generate a /binduser URL.")
    bind_command.add_argument("--channel", default="local", help="Source channel.")
    bind_command.add_argument("--user-id", default="", help="Optional stable user id.")
    bind_command.add_argument("--remark", default="")

    args = parser.parse_args()
    if args.command == "single" and args.single_command == "bind":
        print(build_single_user_bind_url(args.channel, args.user_id, args.remark))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
