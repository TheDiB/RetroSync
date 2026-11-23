"""Human-readable, strictly read-only platform comparison diagnostics."""

from collections import defaultdict


def render_platform_report(inventory, comparison):
    """Render an inventory/comparison pair without choosing a sync direction."""
    if not isinstance(inventory, dict) or not isinstance(comparison, dict):
        raise ValueError("Expected inventory and comparison dictionaries")
    if inventory.get("complete") is not True or comparison.get("complete") is not True:
        raise ValueError("Incomplete inventory or comparison")
    if inventory.get("platform") != comparison.get("platform"):
        raise ValueError("Platform mismatch")
    endpoints = inventory.get("endpoints")
    if not isinstance(endpoints, dict) or any(
        not isinstance(endpoints.get(side), dict) for side in ("local", "remote")
    ):
        raise ValueError("Missing endpoints")
    files = comparison.get("files")
    if not isinstance(files, list):
        raise ValueError("Missing comparison files")
    statuses = ("IDENTICAL", "DIFFERENT", "LOCAL_ONLY", "REMOTE_ONLY")
    kinds = ("SRAM", "STATE")
    matrix = {kind: {status: 0 for status in statuses} for kind in kinds}
    divergent_sram = []
    only_sram = []
    hashes = defaultdict(list)
    for side in ("local", "remote"):
        entries = endpoints[side].get("files")
        if not isinstance(entries, list):
            raise ValueError("Missing endpoint files")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Invalid endpoint file")
            if entry.get("kind") == "SRAM":
                digest = entry.get("sha256")
                name = entry.get("relative_path")
                if isinstance(digest, str) and len(digest) == 64 and isinstance(name, str):
                    hashes[(side, digest.lower())].append(name)

    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("Invalid comparison entry")
        kind, status = entry.get("kind"), entry.get("status")
        if kind not in kinds or status not in statuses:
            raise ValueError("Unexpected file kind or comparison status")
        name = entry.get("relative_path")
        if not isinstance(name, str) or not name:
            raise ValueError("Missing relative path")
        matrix[kind][status] += 1
        if kind == "SRAM" and status == "DIFFERENT":
            divergent_sram.append(name)
        elif kind == "SRAM" and status in ("LOCAL_ONLY", "REMOTE_ONLY"):
            only_sram.append((name, status))
    expected = comparison.get("counts")
    if not isinstance(expected, dict) or any(
        sum(matrix[kind][status] for kind in kinds) != expected.get(status)
        for status in statuses
    ):
        raise ValueError("Comparison totals do not match file entries")

    local_core = str(endpoints["local"].get("core", "unknown"))
    remote_core = str(endpoints["remote"].get("core", "unknown"))
    lines = [
        f"RetroSync platform report | {inventory['platform']} | READ ONLY",
        "Matching: exact relative filenames; equality: SHA-256",
        "",
        "STATUS          SRAM  STATE  TOTAL",
    ]
    for status in statuses:
        lines.append(f"{status:<15} {matrix['SRAM'][status]:>4}  {matrix['STATE'][status]:>5}  {expected[status]:>5}")
    lines.append(f"{'TOTAL':<15} {sum(matrix['SRAM'].values()):>4}  {sum(matrix['STATE'].values()):>5}  {len(files):>5}")
    lines.extend(["", "Divergent SRAM (no winner selected):"])
    lines.extend(f"  - {name}" for name in sorted(divergent_sram))
    if not divergent_sram:
        lines.append("  (none)")
    lines.append("SRAM present on one side only (not a deletion instruction):")
    lines.extend(f"  - {status}: {name}" for name, status in sorted(only_sram))
    if not only_sram:
        lines.append("  (none)")

    lines.append("Identical SRAM content under different names (advisory):")
    duplicates = []
    for (side, digest), names in sorted(hashes.items()):
        unique = sorted(set(names))
        if len(unique) > 1:
            duplicates.append(f"  - {side}: " + " | ".join(unique))
    lines.extend(duplicates or ["  (none)"])

    lines.extend(["", "Compatibility and safety:"])
    lines.append(f"  - Declared cores: local={local_core}, remote={remote_core}")
    if local_core.strip().lower() == "unknown" or remote_core.strip().lower() == "unknown":
        lines.append("  - WARNING: at least one core is unknown; compatibility not established.")
    elif local_core.casefold() != remote_core.casefold():
        lines.append("  - WARNING: cores differ; compatibility not established.")
    else:
        lines.append("  - Same declared core does not prove save compatibility.")
    lines.append("  - Save states: inventory only, never automatic sync candidates.")
    lines.append("  - No master/slave policy applied; no copy, delete, or config changes.")
    return "\n".join(lines)
