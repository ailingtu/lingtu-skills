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
    get_bind_token,
    get_saved_user_api_key,
    list_user_bindings,
    resolve_user_api_key,
    set_auth_mode,
    set_bind_token,
)


def command_mode(args: argparse.Namespace) -> None:
    if args.mode_command == "set":
        print(set_auth_mode(args.mode))
    elif args.mode_command == "get":
        print(get_auth_mode())


def command_token(args: argparse.Namespace) -> None:
    if args.token_command == "set":
        set_bind_token(args.token)
        print(json.dumps({"saved": True}, ensure_ascii=False, indent=2))
    elif args.token_command == "clear":
        set_bind_token(None)
        print(json.dumps({"saved": False}, ensure_ascii=False, indent=2))
    elif args.token_command == "status":
        print(json.dumps({"saved": bool(get_bind_token())}, ensure_ascii=False, indent=2))


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

    token = subparsers.add_parser("token", help="Manage optional backend binding-check token.")
    token_sub = token.add_subparsers(dest="token_command", required=True)
    token_set = token_sub.add_parser("set", help="Save the optional binding-check token.")
    token_set.add_argument("--token", required=True)
    token_set.set_defaults(func=command_token)
    token_clear = token_sub.add_parser("clear", help="Delete the saved binding-check token.")
    token_clear.set_defaults(func=command_token)
    token_status = token_sub.add_parser("status", help="Show whether a binding-check token is configured.")
    token_status.set_defaults(func=command_token)

    bind = subparsers.add_parser("bind", help="Generate a /binduser URL for a bot user.")
    bind.add_argument("--channel", choices=("feishu", "wechat"), required=True)
    bind.add_argument("--user-id", required=True)
    bind.add_argument("--remark", default="")
    bind.add_argument("--message", default="", help="Accepted for bot command compatibility; not used.")
    bind.add_argument("--token", help="Override the configured binding token for this generated URL.")
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
