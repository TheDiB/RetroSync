"""Pure, read-only SRAM synchronization decision logic.

A baseline is trustworthy only if it was recorded after a verified synchronization.
This module never writes saves or baselines.
"""

import json
import re
from pathlib import Path

_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")


def _hash(value):
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError("Expected a 64-character SHA-256 hex digest or null")
    return value.lower()


def decide(local_hash, remote_hash, baseline_hash=None):
    """Classify SRAM versions; returned strings are NOT write permissions."""
    local = _hash(local_hash)
    remote = _hash(remote_hash)
    baseline = _hash(baseline_hash)

    if local is None and remote is None:
        return "MISSING_BOTH"
    if local is None:
        return "MISSING_LOCAL"
    if remote is None:
        return "MISSING_REMOTE"
    if local == remote:
        return "IN_SYNC"
    if baseline is None:
        return "INITIAL_CONFLICT"
    if local == baseline:
        return "PULL"
    if remote == baseline:
        return "PUSH"
    return "CONFLICT"


def load_baseline(path, device_id):
    """Read and validate an optional local baseline file; never create one."""
    if path is None:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported baseline schema")
    if data.get("device_id") != device_id:
        raise ValueError("Baseline device_id does not match configuration")
    games = data.get("games")
    if not isinstance(games, dict):
        raise ValueError("Baseline games must be an object")
    for game_id, game in games.items():
        if not isinstance(game, dict) or not isinstance(game.get("sram"), dict):
            raise ValueError(f"Invalid baseline entry for {game_id}")
        if "last_synced_sha256" not in game["sram"]:
            raise ValueError(f"Missing last_synced_sha256 for {game_id}")
        _hash(game["sram"]["last_synced_sha256"])
    return games


def baseline_hash(games, game_id):
    """Return known last-synced SRAM hash, or None for an untracked game."""
    entry = games.get(game_id)
    return None if entry is None else _hash(entry["sram"]["last_synced_sha256"])
