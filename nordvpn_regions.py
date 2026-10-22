"""Country names and explicitly curated country groups."""

from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def country_code(hostname: str) -> str | None:
    match = re.fullmatch(r"([a-z]{2})[0-9]+\.nordvpn\.com", hostname, re.I)
    return match.group(1).lower() if match else None


def country_name(hostname: str) -> str:
    code = country_code(hostname)
    if code is None:
        return "Unknown"
    names = json.loads((ROOT / "country_names.json").read_text(encoding="utf-8"))
    return names.get(code, "Unknown")


def load_region_lists(custom_file: Path | None = None) -> dict:
    """Custom definitions replace built-ins by name, never silently merge."""
    names = json.loads((ROOT / "country_names.json").read_text(encoding="utf-8"))
    groups = json.loads((ROOT / "region-lists.json").read_text(encoding="utf-8"))
    if custom_file is not None:
        custom = json.loads(custom_file.expanduser().read_text(encoding="utf-8"))
        if not isinstance(custom, dict):
            raise ValueError("region lists must be a JSON object")
        groups.update(custom)
    for name, item in groups.items():
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", name):
            raise ValueError(f"invalid region list name: {name!r}")
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("description"), str)
            or not isinstance(item.get("countries"), list)
        ):
            raise ValueError(f"invalid region list definition: {name!r}")
        codes = item["countries"]
        if any(not isinstance(code, str) or code.lower() not in names or code != code.lower() for code in codes):
            raise ValueError(f"invalid country code in region list: {name!r}")
        if len(codes) != len(set(codes)):
            raise ValueError(f"duplicate country code in region list: {name!r}")
    return groups
