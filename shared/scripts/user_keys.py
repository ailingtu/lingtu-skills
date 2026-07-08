#!/usr/bin/env python3
"""Generate a Lingtu /binduser URL."""

from __future__ import annotations

import argparse
import sys

from lingtu_auth import build_single_user_bind_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Lingtu /binduser URL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bind_parser = subparsers.add_parser("single", help="Generate a /binduser URL.")
    bind_sub = bind_parser.add_subparsers(dest="single_command", required=True)
    bind_cmd = bind_sub.add_parser("bind", help="Generate a /binduser URL and open it in a browser to bind your API key.")
    bind_cmd.add_argument("--channel", default="local", help="Source channel.")
    bind_cmd.add_argument("--user-id", default="", help="User id. If omitted a stable local id is generated.")
    bind_cmd.add_argument("--remark", default="")

    args = parser.parse_args()
    if args.command == "single" and args.single_command == "bind":
        print(build_single_user_bind_url(args.channel, args.user_id, args.remark))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
