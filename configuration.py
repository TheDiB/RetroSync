"""Read-only configuration validation for platform-based RetroSync."""
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

DEFAULT_POLICY = {"sram": "manual", "missing": "create_new"}
POLICIES = {"sram": {"manual", "prefer_local", "prefer_remote"},
            "missing": {"block", "create_new", "restore"}}


def _object(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _string(value, label):
    if not isinstance(value, str) or not value.strip() or value != value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError(f"Invalid {label}")
    return value


def _relative(value, label):
    value = _string(value, label)
    if "\\" in value or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError(f"{label} must be a traversal-free relative POSIX path")
    return value


def _absolute(value, label):
    value = _string(value, label)
    if not PurePosixPath(value).is_absolute() or "\\" in value or any(p in (".", "..") for p in value.split("/")):
        raise ValueError(f"{label} must be an absolute POSIX path")
    return value


def resolve_policy(global_policy=None, platform_policy=None):
    result = DEFAULT_POLICY.copy()
    for policy in (global_policy, platform_policy):
        if policy is None:
            continue
        for key, value in _object(policy, "policy").items():
            if key not in POLICIES or not isinstance(value, str) or value not in POLICIES[key]:
                raise ValueError(f"Invalid policy: {key}={value!r}")
            result[key] = value
    return result


def validate_config(config):
    """Validate v2 without mutation; preserve legacy v1 dispatch unchanged."""
    config = _object(config, "configuration")
    version = config.get("schema_version")
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Unsupported config schema")
    if version == 1:
        return config
    _string(config.get("device_id"), "device_id")
    nas = _object(config.get("nas"), "nas")
    _absolute(nas.get("mount"), "nas.mount")
    source = _string(nas.get("expected_source"), "nas.expected_source")
    if not re.fullmatch(r"//[^/\\]+/[^/\\]+", source):
        raise ValueError("Expected CIFS source //server/share")
    _relative(nas.get("remote_root"), "nas.remote_root")
    if "games" in config:
        raise ValueError("Schema v2 must not contain legacy games")
    global_policy = config.get("policy", {})
    _object(global_policy, "global policy")
    resolve_policy(global_policy)
    platforms = config.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        raise ValueError("platforms must be a nonempty array")
    ids = set()
    for platform in platforms:
        platform = _object(platform, "platform")
        identifier = _string(platform.get("id"), "platform.id")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", identifier) or identifier in ids:
            raise ValueError(f"Invalid or duplicate platform id: {identifier}")
        ids.add(identifier)
        for side in ("local", "remote"):
            endpoint = _object(platform.get(side), side)
            for key in ("emulator", "core"):
                _string(endpoint.get(key), f"{side}.{key}")
            validator = _absolute if side == "local" else _relative
            validator(endpoint.get("save_dir"), f"{side}.save_dir")
        policy = platform.get("policy", {})
        _object(policy, "platform policy")
        resolve_policy(global_policy, policy)
    return config


def load_config(path):
    """Read configuration without writing or contacting endpoints."""
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8")))
