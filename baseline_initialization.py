"""Baseline initialization drafts; persistence is fixture-only.

No production history is trusted or written by this module.
"""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from configuration import configuration_report
from platform_baseline import validate_platform_baseline, _unique_object
from platform_comparison import compare_platform
from platform_scan import scan_configured


def mapping_fingerprint(config):
    report = configuration_report(config)
    if report["schema_version"] != 2 or report["warnings"]:
        raise ValueError("Unambiguous schema v2 configuration required")
    mapping = {"device_id": config["device_id"],
               "nas": {k: config["nas"][k] for k in ("mount", "expected_source", "remote_root")},
               "platforms": sorted([
                   {"id": p["id"], **{side: {k: p[side][k] for k in
                    ("emulator", "core", "save_dir")} for side in ("local", "remote")}}
                   for p in config["platforms"]], key=lambda p: p["id"])}
    raw = json.dumps(mapping, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_baseline_draft(config, verify_mount):
    """Fresh full scan; equal bytes are candidates, not verified provenance."""
    fingerprint = mapping_fingerprint(config)
    scan = scan_configured(config, verify_mount)
    if scan["complete"] is not True or scan["device_id"] != config["device_id"]:
        raise ValueError("Incomplete or mismatched scan")
    ids = [p["id"] for p in scan["platforms"]]
    if sorted(ids) != sorted(p["id"] for p in config["platforms"]):
        raise ValueError("Full platform coverage required")
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data = {"schema_version": 2, "device_id": config["device_id"],
            "initialization": {"method": "equal_hash_observation",
                               "mapping_sha256": fingerprint,
                               "provenance_verified": False},
            "platforms": {}}
    for item in scan["platforms"]:
        comparison = compare_platform(item["inventory"])
        if comparison != item["comparison"] or comparison["platform"] != item["id"]:
            raise ValueError("Inconsistent inventory")
        files = {}
        for f in comparison["files"]:
            if f["kind"] == "SRAM" and f["status"] == "IDENTICAL":
                files[f["relative_path"]] = {
                    "last_synced_sha256": f["local_sha256"],
                    "last_synced_at": stamp}
        data["platforms"][item["id"]] = {"files": files}
    validate_platform_baseline(data, config)
    return data


def validate_baseline_draft(data, config):
    """Check mapping binding, not authenticity or runtime provenance."""
    validate_platform_baseline(data, config)
    expected = {"method": "equal_hash_observation",
                "mapping_sha256": mapping_fingerprint(config),
                "provenance_verified": False}
    metadata = data.get("initialization")
    if (not isinstance(metadata, dict) or metadata != expected
            or metadata.get("provenance_verified") is not False):
        raise ValueError("Invalid initialization metadata or changed mapping")
    if set(data["platforms"]) != {p["id"] for p in config["platforms"]}:
        raise ValueError("Incomplete baseline draft")
    return data


def persist_baseline_fixture(data, config, directory):
    """Publish a draft in an isolated test directory, never overwrite.

    Requires hard-link support; no fallback to replacement or partial final
    files. Caller must supply an isolated fixture directory. Not crash-durable
    on every filesystem and not a production history store.
    """
    validate_baseline_draft(data, config)
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Existing fixture directory required")
    target = directory / "baseline-initialization.fixture.json"
    payload = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    stage = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".baseline-stage-",
                                         delete=False) as stream:
            stage = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if stage.read_bytes() != payload:
            raise RuntimeError("Baseline staging verification failed")
        validate_baseline_draft(json.loads(stage.read_text(encoding="utf-8"),
                                          object_pairs_hook=_unique_object), config)
        os.link(stage, target)
        return target
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)
