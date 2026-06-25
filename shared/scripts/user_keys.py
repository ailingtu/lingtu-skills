#!/usr/bin/env python3
"""Manage Lingtu skill user-key bindings."""

from __future__ import annotations

import argparse
import json
import sys

from lingtu_auth import (
    build_bind_url,
    delete_user_api_key,
    get_auth_mode,
    get_saved_user_api_key,
    list_user_bindings,
    resolve_user_api_key,
    set_auth_mode,
)


def command_mode(args: argparse.Namespace) -> None:
    if args.mode_command == "set":
        mode = set_auth_mode(args.mode)
        response = {"authMode": mode}
        if mode == "multi":
            response["notice"] = (
                "Multi-user mode ignores LINGTU_API_KEY. "
                "The environment variable is not cleared automatically; remove it manually if needed."
            )
        print(json.dumps(response, ensure_ascii=False, indent=2))
    elif args.mode_command == "get":
        print(get_auth_mode())


def command_bind(args: argparse.Namespace) -> None:
    print(build_bind_url(args.channel, args.user_id, remark=args.remark or "", token=args.token))


def command_get(args: argparse.Namespace) -> None:
    api_key = get_saved_user_api_key(args.channel, args.user_id)
    source = "local"
    if not api_key:
        api_key = resolve_user_api_key(args.channel, args.user_id)
        source = "bind_check"
    masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    print(json.dumps({"channel": args.channel, "userId": args.user_id, "source": source, "saved": True, "apiKeyMasked": masked}, ensure_ascii=False, indent=2))


def command_unbind(args: argparse.Namespace) -> None:
    deleted = delete_user_api_key(args.channel, args.user_id)
    print(json.dumps({"channel": args.channel, "userId": args.user_id, "deleted": deleted}, ensure_ascii=False, indent=2))


def command_list(args: argparse.Namespace) -> None:
    print(json.dumps(list_user_bindings(), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bind Lingtu skills to per-user API keys.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mode = subparsers.add_parser("mode", help="Read or write single-user / multi-user auth mode.")
    mode_sub = mode.add_subparsers(dest="mode_command", required=True)
    mode_set = mode_sub.add_parser("set", help="Set auth mode.")
    mode_set.add_argument("mode", choices=("single", "multi"))
    mode_set.set_defaults(func=command_mode)
    mode_get = mode_sub.add_parser("get", help="Print auth mode.")
    mode_get.set_defaults(func=command_mode)

    bind = subparsers.add_parser("bind", help="Generate a /binduser URL for a bot user.")
    bind.add_argument("--channel", choices=("feishu", "wechat"), required=True)
    bind.add_argument("--user-id", required=True)
    bind.add_argument("--remark", default="")
    bind.add_argument("--message", default="", help="Accepted for bot command compatibility; not used.")
    bind.add_argument("--token", help="Use this binding session token instead of auto-generating one.")
    bind.set_defaults(func=command_bind)

    get = subparsers.add_parser("get", help="Get the locally saved key or check the backend binding endpoint.")
    get.add_argument("--channel", choices=("feishu", "wechat"), required=True)
    get.add_argument("--user-id", required=True)
    get.set_defaults(func=command_get)

    unbind = subparsers.add_parser("unbind", help="Delete the local key for a bot user.")
    unbind.add_argument("--channel", choices=("feishu", "wechat"), required=True)
    unbind.add_argument("--user-id", required=True)
    unbind.set_defaults(func=command_unbind)

    list_parser = subparsers.add_parser("list", help="List local user bindings without printing API keys.")
    list_parser.set_defaults(func=command_list)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
