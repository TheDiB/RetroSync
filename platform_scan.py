"""Non-interactive read-only discovery; no sync decisions."""
from pathlib import Path
from configuration import configuration_report, resolve_policy
from platform_discovery import discover_platform
from platform_comparison import compare_platform
from platform_report import render_platform_report


def scan_configured(config, verify_mount, platform_id=None):
    report = configuration_report(config)
    if report["schema_version"] != 2:
        raise ValueError("Scan requires schema v2")
    if report["warnings"]:
        raise ValueError("; ".join(report["warnings"]))
    platforms = config["platforms"]
    if platform_id is not None and not any(p["id"] == platform_id for p in platforms):
        raise ValueError(f"Unknown platform: {platform_id}")
    nas = config["nas"]
    mount = Path(nas["mount"])
    verify_mount(mount, nas["expected_source"])
    root = mount / nas["remote_root"]
    mappings = []
    seen = []
    for platform in platforms:
        mapping = {"id": platform["id"], "local": dict(platform["local"]),
                   "remote": dict(platform["remote"])}
        mapping["remote"]["save_dir"] = str(root / platform["remote"]["save_dir"])
        for side in ("local", "remote"):
            path = Path(mapping[side]["save_dir"])
            if not path.is_absolute():
                raise ValueError(f"Endpoint is not absolute on this host: {path}")
            # Reject symlink components and physical aliases before inventory.
            if any(p.is_symlink() for p in (path, *path.parents)):
                raise ValueError(f"Symlinked endpoint: {path}")
            resolved = path.resolve(strict=True)
            if not resolved.is_dir():
                raise ValueError(f"Endpoint is not a directory: {path}")
            for previous in seen:
                if (resolved == previous or resolved in previous.parents
                        or previous in resolved.parents or resolved.samefile(previous)):
                    raise ValueError(f"Overlapping endpoint directories: {path} and {previous}")
            seen.append(resolved)
        mappings.append((platform, mapping))
    output = {"schema_version": 2, "device_id": config["device_id"],
              "complete": True, "read_only": True, "sync_decisions": False,
              "platforms": []}
    for platform, mapping in mappings:
        if platform_id is not None and platform["id"] != platform_id:
            continue
        verify_mount(mount, nas["expected_source"])
        inventory = discover_platform(mapping)
        comparison = compare_platform(inventory)
        verify_mount(mount, nas["expected_source"])
        output["platforms"].append({
            "id": platform["id"], "attribution_verified": False,
            "policy": resolve_policy(config.get("policy"), platform.get("policy")),
            "inventory": inventory, "comparison": comparison})
    return output


def render_scan(report):
    lines = ["RetroSync v0.10 | PLATFORM SCAN | READ ONLY",
             f"Device: {report['device_id']} | Platforms: {len(report['platforms'])}"]
    for item in report["platforms"]:
        lines.extend(["", render_platform_report(item["inventory"], item["comparison"]),
                      "WARNING: Platform attribution not verified; inventory only."])
    lines.append("No configuration, baseline or save files modified.")
    return "\n".join(lines)
