#!/usr/bin/env python3
"""Shared auth helpers for Lingtu skills.

Single-user mode uses the configured administrator binding. Multi-user bot
mode passes --channel and --user-id. Both modes resolve keys from
~/.lingtu-skills/config.json or the backend binding check endpoint.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback for local installs.
    fcntl = None


DEFAULT_SITE_URL = "https://app.ailingtu.com"
DEFAULT_BIND_API_URL = "https://api.ailingtu.com"
DEFAULT_AUTH_MODE = "single"
LOCAL_CHANNEL = "local"
CONFIG_ENV = "LINGTU_SKILLS_CONFIG"
AUTH_MODE_ENV = "LINGTU_SKILLS_AUTH_MODE"
CHANNEL_ENV = "LINGTU_SKILL_CHANNEL"
USER_ID_ENV = "LINGTU_SKILL_USER_ID"


def config_path() -> Path:
    return Path(os.environ.get(CONFIG_ENV, "~/.lingtu-skills/config.json")).expanduser()


def config_lock_path() -> Path:
    return config_path().with_suffix(config_path().suffix + ".lock")


@contextmanager
def config_lock():
    path = config_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def normalize_channel(channel: str) -> str:
    value = (channel or "").strip().lower()
    aliases = {
        "codex": LOCAL_CHANNEL,
        "desktop": LOCAL_CHANNEL,
        "lark": "feishu",
        "local": LOCAL_CHANNEL,
        "飞书": "feishu",
        "wx": "wechat",
        "weixin": "wechat",
        "微信": "wechat",
    }
    value = aliases.get(value, value)
    if value not in {"feishu", "wechat", LOCAL_CHANNEL}:
        return LOCAL_CHANNEL
    return value


def normalize_bot_channel(channel: str) -> str:
    value = normalize_channel(channel)
    if value == LOCAL_CHANNEL:
        raise SystemExit("Unsupported bot channel. Use feishu or wechat.")
    return value


def user_key_id(channel: str, user_id: str) -> str:
    user_id = (user_id or "").strip()
    if not user_id:
        raise SystemExit("Missing user id.")
    return f"{normalize_channel(channel)}:{user_id}"


def redact_url_token(url: str) -> str:
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted = [
        (key, "***" if key.lower() == "token" else value)
        for key, value in pairs
    ]
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(redacted)))


def redact_sensitive_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if "token" in key_text or "apikey" in key_text or key_text in {"api_key", "key"}:
                redacted[key] = "***"
            else:
                redacted[key] = redact_sensitive_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive_payload(item) for item in value]
    return value


def default_config() -> dict[str, Any]:
    return {
        "authMode": DEFAULT_AUTH_MODE,
        "singleUser": {},
        "users": {},
    }


def normalize_config(data: dict[str, Any]) -> dict[str, Any]:
    single_user = data.get("singleUser")
    if not isinstance(single_user, dict):
        data["singleUser"] = {}
    users = data.get("users")
    if not isinstance(users, dict):
        data["users"] = {}
    if data.get("authMode") not in {"single", "multi"}:
        data["authMode"] = DEFAULT_AUTH_MODE
    return data


def _read_config_unlocked() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return default_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid Lingtu skills config JSON: {path}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid Lingtu skills config shape: {path}")
    return normalize_config(data)


def load_config() -> dict[str, Any]:
    return _read_config_unlocked()


def _write_config_unlocked(config: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp_path.write_text(json.dumps(normalize_config(config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp_path, path)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def save_config(config: dict[str, Any]) -> None:
    with config_lock():
        _write_config_unlocked(config)


def update_config(mutator: Any) -> dict[str, Any]:
    with config_lock():
        config = _read_config_unlocked()
        mutator(config)
        _write_config_unlocked(config)
        return config


def generate_bind_token() -> str:
    return secrets.token_urlsafe(16)


def generate_local_user_id() -> str:
    return f"local_{secrets.token_urlsafe(18).replace('-', '_')}"


def generate_unique_bind_token(config: dict[str, Any]) -> str:
    users = config.get("users", {})
    existing: set[str] = set()
    for value in users.values():
        if not isinstance(value, dict):
            continue
        if isinstance(value.get("bindToken"), str):
            existing.add(value["bindToken"])
    while True:
        token = generate_bind_token()
        if token not in existing:
            return token


def get_saved_user_record(channel: str, user_id: str) -> dict[str, Any] | None:
    users = load_config().get("users", {})
    record = users.get(user_key_id(channel, user_id))
    return record if isinstance(record, dict) else None


def get_saved_user_bind_token(channel: str, user_id: str) -> str | None:
    record = get_saved_user_record(channel, user_id)
    if record and isinstance(record.get("bindToken"), str) and record["bindToken"]:
        return record["bindToken"]
    return None


def save_user_bind_token(channel: str, user_id: str, bind_token: str) -> str:
    if not bind_token:
        raise SystemExit("Cannot save an empty binding token.")
    key = user_key_id(channel, user_id)

    def mutate(config: dict[str, Any]) -> None:
        users = config.setdefault("users", {})
        record = users.setdefault(key, {})
        if not isinstance(record, dict):
            record = {}
            users[key] = record
        created_at = datetime.now(timezone.utc).isoformat()
        record["bindToken"] = bind_token
        record["tokenCreatedAt"] = created_at

    update_config(mutate)
    return bind_token


def create_user_bind_token(channel: str, user_id: str, token: str | None = None) -> str:
    if token:
        return save_user_bind_token(channel, user_id, token)
    key = user_key_id(channel, user_id)
    generated = ""

    def mutate(config: dict[str, Any]) -> None:
        nonlocal generated
        generated = generate_unique_bind_token(config)
        users = config.setdefault("users", {})
        record = users.setdefault(key, {})
        if not isinstance(record, dict):
            record = {}
            users[key] = record
        created_at = datetime.now(timezone.utc).isoformat()
        record["bindToken"] = generated
        record["tokenCreatedAt"] = created_at

    update_config(mutate)
    return generated


def require_user_bind_token(channel: str, user_id: str) -> str:
    saved = get_saved_user_bind_token(channel, user_id)
    if not saved:
        raise SystemExit(
            "Missing binding session token for this user. Generate a bind URL first with "
            "`python3 shared/scripts/user_keys.py bind --channel <channel> --user-id <user_id>`."
        )
    return saved


def clear_user_bind_token(channel: str, user_id: str) -> None:
    key = user_key_id(channel, user_id)

    def mutate(config: dict[str, Any]) -> None:
        users = config.setdefault("users", {})
        record = users.get(key)
        if isinstance(record, dict):
            record.pop("bindToken", None)
            record.pop("tokenCreatedAt", None)
            record["tokenUsedAt"] = datetime.now(timezone.utc).isoformat()

    update_config(mutate)


def normalize_auth_mode(mode: str | None) -> str:
    value = (mode or DEFAULT_AUTH_MODE).strip().lower()
    aliases = {
        "user": "single",
        "single-user": "single",
        "single_user": "single",
        "bot": "multi",
        "multi-user": "multi",
        "multi_user": "multi",
    }
    value = aliases.get(value, value)
    if value not in {"single", "multi"}:
        raise SystemExit("Unsupported auth mode. Use single or multi.")
    return value


def get_auth_mode() -> str:
    env_mode = os.environ.get(AUTH_MODE_ENV)
    if env_mode:
        return normalize_auth_mode(env_mode)
    return normalize_auth_mode(load_config().get("authMode"))


def set_auth_mode(mode: str) -> str:
    normalized = normalize_auth_mode(mode)
    update_config(lambda config: config.update({"authMode": normalized}))
    return normalized


def get_single_user_identity() -> dict[str, str] | None:
    single_user = load_config().get("singleUser", {})
    if not isinstance(single_user, dict):
        return None
    channel = single_user.get("channel")
    user_id = single_user.get("userId")
    if not isinstance(channel, str) or not isinstance(user_id, str):
        return None
    if not channel or not user_id:
        return None
    return {
        "channel": normalize_channel(channel),
        "userId": user_id,
    }


def set_single_user_identity(channel: str, user_id: str) -> dict[str, str]:
    platform = normalize_channel(channel)
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id:
        raise SystemExit("Missing user id.")
    updated_at = datetime.now(timezone.utc).isoformat()

    def mutate(config: dict[str, Any]) -> None:
        config["singleUser"] = {
            "channel": platform,
            "userId": normalized_user_id,
            "updatedAt": updated_at,
        }

    update_config(mutate)
    return {"channel": platform, "userId": normalized_user_id}


def ensure_single_user_identity(
    channel: str | None = None,
    user_id: str | None = None,
) -> dict[str, str]:
    platform = normalize_channel(channel or LOCAL_CHANNEL)
    normalized_user_id = (user_id or "").strip()
    if normalized_user_id:
        return set_single_user_identity(platform, normalized_user_id)

    existing = get_single_user_identity()
    if existing and existing["channel"] == platform:
        return existing

    generated = ""

    def mutate(config: dict[str, Any]) -> None:
        nonlocal generated
        generated = generate_local_user_id()
        config["singleUser"] = {
            "channel": platform,
            "userId": generated,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

    update_config(mutate)
    return {"channel": platform, "userId": generated}


def clear_single_user_identity() -> dict[str, Any]:
    result: dict[str, Any] = {"singleUser": False, "apiKey": False}

    def mutate(config: dict[str, Any]) -> None:
        single_user = config.get("singleUser", {})
        if isinstance(single_user, dict) and single_user.get("channel") and single_user.get("userId"):
            result["singleUser"] = True
            users = config.setdefault("users", {})
            record = users.get(user_key_id(single_user["channel"], single_user["userId"]))
            if isinstance(record, dict):
                result["apiKey"] = "apiKey" in record
                record.pop("apiKey", None)
                record.pop("boundAt", None)
        config["singleUser"] = {}

    update_config(mutate)
    return result


def clear_single_user_identity_key(config: dict[str, Any]) -> bool:
    single_user = config.get("singleUser", {})
    if not isinstance(single_user, dict):
        return False
    channel = single_user.get("channel")
    user_id = single_user.get("userId")
    if not isinstance(channel, str) or not isinstance(user_id, str):
        return False
    users = config.setdefault("users", {})
    record = users.get(user_key_id(channel, user_id))
    if isinstance(record, dict):
        deleted = "apiKey" in record
        record.pop("apiKey", None)
        record.pop("boundAt", None)
        return deleted
    return False


def clear_single_user_api_key() -> dict[str, Any]:
    """Best-effort cleanup for local single-user API key state."""
    result: dict[str, Any] = {
        "processEnv": bool(os.environ.pop("LINGTU_API_KEY", None)),
        "singleUserApiKey": False,
        "configFields": [],
    }
    single_key_fields = ("apiKey", "api_key", "lingtuApiKey", "singleUserApiKey")

    def mutate(config: dict[str, Any]) -> None:
        result["singleUserApiKey"] = clear_single_user_identity_key(config)
        for field in single_key_fields:
            if field in config:
                config.pop(field, None)
                result["configFields"].append(field)

    update_config(mutate)

    if sys.platform == "darwin":
        try:
            completed = subprocess.run(
                ["launchctl", "unsetenv", "LINGTU_API_KEY"],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            result["macosLaunchctl"] = {
                "attempted": True,
                "cleared": False,
                "error": str(exc),
            }
        else:
            result["macosLaunchctl"] = {
                "attempted": True,
                "cleared": completed.returncode == 0,
            }
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "").strip()
                result["macosLaunchctl"]["error"] = detail or f"exit {completed.returncode}"
    else:
        result["macosLaunchctl"] = {"attempted": False, "cleared": False}

    result["currentShell"] = "not_clearable_from_child_process"
    return result


def build_bind_url(
    channel: str,
    user_id: str,
    remark: str = "",
    token: str | None = None,
) -> str:
    import urllib.parse

    platform = normalize_channel(channel)
    user_id = (user_id or "").strip()
    if not user_id:
        raise SystemExit("Missing user id.")
    query: dict[str, str] = {}
    query["token"] = create_user_bind_token(platform, user_id, token)
    query["platform"] = platform
    query["userid"] = user_id
    if remark:
        query["remark"] = remark
    return f"{DEFAULT_SITE_URL}/binduser?{urllib.parse.urlencode(query)}"


def build_single_user_bind_url(
    channel: str | None = None,
    user_id: str | None = None,
    remark: str = "",
    token: str | None = None,
) -> str:
    identity = ensure_single_user_identity(channel, user_id)
    return build_bind_url(identity["channel"], identity["userId"], remark=remark, token=token)


def get_saved_user_api_key(channel: str, user_id: str) -> str | None:
    record = get_saved_user_record(channel, user_id)
    if isinstance(record, dict) and isinstance(record.get("apiKey"), str) and record["apiKey"]:
        return record["apiKey"]
    return None


def save_user_api_key(channel: str, user_id: str, api_key: str) -> None:
    if not api_key:
        raise SystemExit("Cannot save an empty API key.")
    key = user_key_id(channel, user_id)

    def mutate(config: dict[str, Any]) -> None:
        users = config.setdefault("users", {})
        record = users.setdefault(key, {})
        if not isinstance(record, dict):
            record = {}
            users[key] = record
        record["apiKey"] = api_key
        record["boundAt"] = datetime.now(timezone.utc).isoformat()

    update_config(mutate)


def delete_user_api_key(channel: str, user_id: str) -> bool:
    key = user_key_id(channel, user_id)
    deleted = False

    def mutate(config: dict[str, Any]) -> None:
        nonlocal deleted
        users = config.setdefault("users", {})
        deleted = key in users
        users.pop(key, None)

    update_config(mutate)
    return deleted


def list_user_bindings() -> dict[str, Any]:
    config = load_config()
    users = config.get("users", {})
    single_user = config.get("singleUser", {})
    return {
        "authMode": normalize_auth_mode(config.get("authMode")),
        "singleUser": {
            "channel": single_user.get("channel"),
            "userId": single_user.get("userId"),
            "updatedAt": single_user.get("updatedAt"),
        } if isinstance(single_user, dict) and single_user.get("channel") and single_user.get("userId") else None,
        "users": {
            key: {
                "boundAt": value.get("boundAt"),
                "hasBindToken": bool(value.get("bindToken")),
                "tokenCreatedAt": value.get("tokenCreatedAt"),
            }
            for key, value in users.items()
            if isinstance(value, dict)
        },
    }


def _extract_bind_check_api_key(payload: dict[str, Any]) -> str | None:
    candidates: list[Any] = [
        payload.get("apiKey"),
        payload.get("api_key"),
    ]
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend([data.get("key"), data.get("apiKey"), data.get("api_key")])
    for item in candidates:
        if isinstance(item, str) and item:
            return item
    return None


def bind_check_platform(channel: str) -> str:
    platform = normalize_channel(channel)
    if platform == "feishu":
        return "FEISHU"
    if platform == "wechat":
        return "WEIXIN"
    if platform == LOCAL_CHANNEL:
        return "LOCAL"
    raise SystemExit(f"Unsupported channel for bind check: {channel}")


def fetch_bound_api_key(channel: str, user_id: str) -> str:
    import urllib.parse

    platform = normalize_channel(channel)
    query_params = {
        "externUid": user_id,
        "platform": bind_check_platform(platform),
    }
    query_params["token"] = require_user_bind_token(platform, user_id)
    query = urllib.parse.urlencode(query_params)
    url = f"{DEFAULT_BIND_API_URL}/v1/apiKeyBind/check?{query}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Failed to check Lingtu API key binding: HTTP {exc.code} from {redact_url_token(url)}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to check Lingtu API key binding from {redact_url_token(url)}: {exc.reason}") from exc

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON from Lingtu API key binding endpoint: {body}") from exc

    if isinstance(payload, dict):
        api_key = _extract_bind_check_api_key(payload)
        if api_key:
            save_user_api_key(platform, user_id, api_key)
            clear_user_bind_token(platform, user_id)
            return api_key
        code = payload.get("code") or payload.get("error") or payload.get("message")
        if code:
            raise SystemExit(f"Lingtu API key binding is not ready: {code}")
    redacted = redact_sensitive_payload(payload)
    raise SystemExit(f"Lingtu API key binding response did not include data.key: {json.dumps(redacted, ensure_ascii=False)}")


def resolve_user_api_key(channel: str, user_id: str) -> str:
    saved = get_saved_user_api_key(channel, user_id)
    if saved:
        return saved
    return fetch_bound_api_key(channel, user_id)


def configure_identity(channel: str | None, user_id: str | None) -> None:
    if bool(channel) != bool(user_id):
        raise SystemExit("--channel and --user-id must be passed together.")
    if not channel:
        return
    os.environ[CHANNEL_ENV] = normalize_bot_channel(channel)
    os.environ[USER_ID_ENV] = (user_id or "").strip()


def require_api_key(channel: str | None = None, user_id: str | None = None) -> str:
    channel = channel or os.environ.get(CHANNEL_ENV)
    user_id = user_id or os.environ.get(USER_ID_ENV)
    if get_auth_mode() == "multi":
        if not channel or not user_id:
            raise SystemExit("Both channel and user id are required for multi-user mode.")
        return resolve_user_api_key(channel, user_id)

    if channel or user_id:
        raise SystemExit(
            "Current auth mode is single, so --channel/--user-id will not be used. "
            "Ask an administrator to deploy multi-user mode for bot users, "
            "or omit --channel/--user-id and use the configured single-user administrator."
        )

    single_user = get_single_user_identity()
    if single_user:
        return resolve_user_api_key(single_user["channel"], single_user["userId"])

    raise SystemExit(
        "Missing single-user administrator binding. Run "
        "`python3 shared/scripts/user_keys.py single bind` "
        "and open the returned /binduser URL before using single-user mode."
    )


def add_identity_arguments(parser: Any) -> None:
    parser.add_argument("--channel", choices=("feishu", "wechat"), help="Bot channel for multi-user mode.")
    parser.add_argument("--user-id", help="External user id for multi-user mode.")
