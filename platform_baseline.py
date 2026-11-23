"""Read-only v2 SRAM history. Validation does not establish provenance."""
import json
import re
from datetime import datetime
from pathlib import Path, PureWindowsPath

from configuration import validate_config
from decision import _hash


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate baseline key: {key}")
        result[key] = value
    return result


def _filename(name):
    if (not isinstance(name, str) or not name.lower().endswith(".srm")
            or len(name) <= 4 or "/" in name or "\\" in name
            or PureWindowsPath(name).drive or ":" in name
            or any(ord(c) < 32 for c in name)):
        raise ValueError(f"Invalid baseline SRAM filename: {name!r}")


def validate_platform_baseline(data, config):
    validate_config(config)
    if config["schema_version"] != 2:
        raise ValueError("Platform baseline requires config schema v2")
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 2 or "games" in data):
        raise ValueError("Unsupported platform baseline schema")
    if data.get("device_id") != config["device_id"]:
        raise ValueError("Baseline device_id does not match configuration")
    platforms = data.get("platforms")
    if not isinstance(platforms, dict):
        raise ValueError("Baseline platforms must be an object")
    configured = {p["id"] for p in config["platforms"]}
    for identifier, platform in platforms.items():
        if identifier not in configured:
            raise ValueError(f"Unknown baseline platform: {identifier}")
        if not isinstance(platform, dict) or not isinstance(platform.get("files"), dict):
            raise ValueError(f"Invalid baseline platform: {identifier}")
        for name, entry in platform["files"].items():
            _filename(name)
            if not isinstance(entry, dict) or entry.get("last_synced_sha256") is None:
                raise ValueError(f"Missing baseline hash: {name}")
            _hash(entry["last_synced_sha256"])
            stamp = entry.get("last_synced_at")
            if not isinstance(stamp, str) or not re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", stamp):
                raise ValueError(f"Expected UTC baseline timestamp: {name}")
            datetime.fromisoformat(stamp[:-1] + "+00:00")
    return platforms


def load_platform_baseline(path, config):
    """None means no history; an explicitly missing file is an error."""
    if path is None:
        validate_config(config)
        if config["schema_version"] != 2:
            raise ValueError("Platform baseline requires config schema v2")
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=_unique_object)
    return validate_platform_baseline(data, config)


def platform_baseline_hash(platforms, platform_id, filename):
    """Exact filename lookup, never infer identity from matching hashes."""
    _filename(filename)
    entry = platforms.get(platform_id, {}).get("files", {}).get(filename)
    return None if entry is None else _hash(entry["last_synced_sha256"])
