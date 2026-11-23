"""Read-only global SRAM proposals, never executable operations."""
from collections import Counter
from platform_baseline import load_platform_baseline
from platform_scan import scan_configured
from platform_policy import propose_platform


def build_plan(config, verify_mount, platform_id=None, baseline_path=None):
    history = load_platform_baseline(baseline_path, config)
    scan = scan_configured(config, verify_mount, platform_id)
    platforms = []
    totals = Counter()
    for item in scan["platforms"]:
        plan = propose_platform(item, history)
        plan["paths"] = item["paths"]
        plan["counts"] = dict(sorted(Counter(f["action"] for f in plan["files"]).items()))
        totals.update(plan["counts"])
        platforms.append(plan)
    return {"schema_version": 2, "device_id": scan["device_id"],
            "complete": True, "read_only": True, "write_authorized": False,
            "baseline": str(baseline_path) if baseline_path is not None else None,
            "baseline_provenance_verified": False,
            "platforms": platforms, "counts": dict(sorted(totals.items())),
            "sram_total": sum(totals.values()),
            "states_excluded": sum(p["states_excluded"] for p in platforms)}


def render_plan(report):
    lines = ["RetroSync v0.10 | GLOBAL PLAN | READ ONLY",
             f"Device: {report['device_id']} | Platforms: {len(report['platforms'])}",
             f"Baseline: {report['baseline'] or 'NONE'}",
             "Baseline provenance not verified."]
    for p in report["platforms"]:
        lines.extend(["", f"Platform: {p['id']}",
                      f"SRAM policy: {p['policy']['sram']} | Missing policy: {p['policy']['missing']}",
                      "WARNING: Platform attribution and core compatibility not verified. Proposals only."])
        for side, paths in p["paths"].items():
            lines.append(f"  {side}: {paths['resolved_path']}")
            if paths["symlink_resolved"]:
                lines.append(f"  {side} alias: {paths['configured_path']} -> {paths['resolved_path']}")
        for f in p["files"]:
            lines.append(f"  {f['action']:<18} {f['classification']:<17} {f['relative_path']}")
        lines.append("  Counts: " + (", ".join(f"{k}={v}" for k,v in p["counts"].items()) or "NONE"))
        lines.append(f"  Save states excluded: {p['states_excluded']}")
    lines.extend(["", "Global counts: " + (", ".join(f"{k}={v}" for k,v in report["counts"].items()) or "NONE"),
                  f"Total SRAM: {report['sram_total']}",
                  f"Save states excluded: {report['states_excluded']}",
                  "Authorized writes: 0",
                  "No configuration, baseline or save files modified."])
    return "\n".join(lines)
