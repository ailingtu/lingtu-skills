#!/usr/bin/env python3
"""Read the live public catalog. Semantic recommendation is left to the agent."""

import argparse
import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

CATALOG_URL = "https://ailingtu.com/api/skills"
COPY_FIELDS = ("title", "description", "highlights", "prompt", "input", "output", "requirement", "categoryLabel")


def fetch_catalog():
    request = Request(CATALOG_URL, headers={"Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        raise ValueError("Invalid catalog response: expected skills array")
    for skill in data["skills"]:
        if not isinstance(skill, dict) or not all(
            isinstance(skill.get(key), str) and skill[key]
            for key in ("slug", "packageName", "version")
        ) or not isinstance(skill.get("locales"), dict):
            raise ValueError("Invalid catalog entry: missing identity or locales")
    return data["skills"]


def project_skill(skill, locale):
    copy = skill["locales"].get(locale)
    actual_locale = locale
    if not isinstance(copy, dict):
        actual_locale = "zh-CN"
        copy = skill["locales"].get(actual_locale)
    if not isinstance(copy, dict):
        raise ValueError(f"Missing locale data for {skill['packageName']}")
    result = {key: skill.get(key) for key in
              ("slug", "packageName", "version", "updatedAt", "auth", "category", "platforms")}
    result["locale"] = actual_locale
    result.update({key: copy.get(key) for key in COPY_FIELDS})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "get"))
    parser.add_argument("skill", nargs="?", help="Exact slug or packageName for get")
    parser.add_argument("--locale", choices=("zh-CN", "en-US"), default="zh-CN")
    args = parser.parse_args(argv)
    if (args.command == "get") != (args.skill is not None):
        parser.error("get requires a skill name; list does not accept one")
    try:
        skills = fetch_catalog()
        if args.command == "get":
            skills = [skill for skill in skills if args.skill in (skill["slug"], skill["packageName"])]
            if not skills:
                print(f"Skill not found in live catalog: {args.skill}", file=sys.stderr)
                return 2
        result = {"source": CATALOG_URL, "skills": [project_skill(skill, args.locale) for skill in skills]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, URLError, ValueError) as exc:
        print(f"Catalog request failed ({CATALOG_URL}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
