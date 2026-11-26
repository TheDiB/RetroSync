"""Preliminary v2 checks, never an authorization or coordination token."""
import re
from pathlib import Path
from configuration import configuration_report
from platform_scan import _resolve_endpoint, _verify_endpoints
from preflight import detect_retroarch
from remote_activity import detect_batocera_retroarch


def preflight_v2(config, verify_mount, *, local_detector=None, remote_detector=None):
    checks = []
    result = {"schema_version": 2, "device_id": None, "read_only": True,
              "write_authorized": False, "coordination_verified": False,
              "attribution_verified": False, "compatibility_verified": False,
              "baseline_provenance_verified": False, "checks": checks}

    def add(name, status, reason, detail=""):
        checks.append({"name": name, "status": status, "reason": reason, "detail": detail})

    def finish():
        statuses = {c["status"] for c in checks}
        result["status"] = ("BLOCKED" if "BLOCKED" in statuses else
                            "DEFERRED" if "DEFERRED" in statuses else "READY")
        return result

    try:
        report = configuration_report(config)
        if report["schema_version"] != 2 or report["warnings"]:
            raise ValueError("Unambiguous schema v2 configuration required")
        result["device_id"] = config["device_id"]
        remote = config.get("batocera")
        if remote is not None:
            if (not isinstance(remote, dict)
                    or not isinstance(remote.get("host"), str)
                    or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", remote["host"])
                    or not isinstance(remote.get("user", "root"), str)
                    or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,31}", remote.get("user", "root"))):
                raise ValueError("Invalid Batocera SSH configuration")
    except (ValueError, TypeError, KeyError) as exc:
        add("config", "BLOCKED", "INVALID_CONFIGURATION", str(exc))
        return finish()
    add("config", "PASS", "CONFIGURATION_VALID")
    for p in config["platforms"]:
        for side in ("local", "remote"):
            if p[side]["emulator"].lower() != "retroarch":
                add(f"{side}:{p['id']}", "BLOCKED", "UNSUPPORTED_EMULATOR")
    if any(c["status"] == "BLOCKED" for c in checks):
        return finish()

    nas = config["nas"]
    mount = Path(nas["mount"])

    def mounted():
        try:
            verify_mount(mount, nas["expected_source"])
            return True
        except Exception as exc:
            add("nas_mount", "DEFERRED", "MOUNT_NOT_VERIFIED", str(exc))
            return False

    if not mounted():
        return finish()
    add("nas_mount", "PASS", "MOUNT_VERIFIED")
    snapshots = []
    for p in config["platforms"]:
        for side in ("local", "remote"):
            name = f"{side}:{p['id']}"
            path = Path(p[side]["save_dir"]) if side == "local" else mount / nas["remote_root"] / p[side]["save_dir"]
            try:
                resolved, identity = _resolve_endpoint(path, side)
                for _, _, previous, _ in snapshots:
                    if (resolved == previous or resolved in previous.parents
                            or previous in resolved.parents or resolved.samefile(previous)):
                        raise ValueError("Overlapping endpoint directories")
                snapshots.append((side, path, resolved, identity))
                add(name, "PASS", "ENDPOINT_OBSERVED", str(resolved))
            except ValueError as exc:
                add(name, "BLOCKED", "UNSAFE_ENDPOINT", str(exc))
            except OSError as exc:
                add(name, "DEFERRED", "ENDPOINT_UNAVAILABLE", str(exc))
    if any(c["status"] != "PASS" for c in checks):
        return finish()

    def activity(name, detector, *args, **kwargs):
        try:
            status, detail = detector(*args, **kwargs)
            if status not in ("RUNNING", "STOPPED", "UNKNOWN") or not isinstance(detail, str):
                raise ValueError("Invalid detector result")
        except Exception as exc:
            status, detail = "UNKNOWN", type(exc).__name__
        add(name, "PASS" if status == "STOPPED" else "DEFERRED",
            {"STOPPED": "NO_RETROARCH_OBSERVED", "RUNNING": "EMULATOR_RUNNING",
             "UNKNOWN": "EMULATOR_STATE_UNKNOWN"}[status], detail)

    activity("retroarch_local", local_detector or detect_retroarch)
    if remote is None:
        add("retroarch_remote", "DEFERRED", "REMOTE_INSPECTION_NOT_CONFIGURED")
    else:
        activity("retroarch_remote", remote_detector or detect_batocera_retroarch,
                 remote["host"], user=remote.get("user", "root"))
    if mounted():
        try:
            _verify_endpoints(snapshots)
            add("endpoint_recheck", "PASS", "ENDPOINTS_REOBSERVED")
        except (OSError, RuntimeError, ValueError) as exc:
            add("endpoint_recheck", "DEFERRED", "ENDPOINT_CHANGED_OR_UNAVAILABLE", str(exc))
    return finish()
