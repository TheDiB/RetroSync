"""Read-only comparison of two complete platform inventories.

File identity is the exact relative path, not a guessed game identity.
No copy direction, conflict resolution, or state compatibility is inferred.
"""


def compare_platform(report):
    """Return deterministic per-file comparisons, failing closed on bad input."""
    if not isinstance(report, dict) or report.get("complete") is not True:
        raise ValueError("A complete platform inventory is required")
    endpoints = report.get("endpoints")
    if not isinstance(endpoints, dict):
        raise ValueError("Missing platform endpoints")

    indexed = {}
    for side in ("local", "remote"):
        endpoint = endpoints.get(side)
        if not isinstance(endpoint, dict) or not isinstance(endpoint.get("files"), list):
            raise ValueError(f"Invalid {side} inventory")
        files = {}
        for entry in endpoint["files"]:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid {side} file entry")
            path = entry.get("relative_path")
            kind = entry.get("kind")
            digest = entry.get("sha256")
            if (not isinstance(path, str) or not path
                    or "/" in path or "\\" in path or path in (".", "..")
                    or kind not in ("SRAM", "STATE")
                    or not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdefABCDEF" for c in digest)):
                raise ValueError(f"Invalid {side} file identity or digest")
            if path in files:
                raise ValueError(f"Duplicate {side} file: {path}")
            files[path] = entry
        indexed[side] = files

    comparisons = []
    counts = {"IDENTICAL": 0, "DIFFERENT": 0, "LOCAL_ONLY": 0, "REMOTE_ONLY": 0}
    for path in sorted(set(indexed["local"]) | set(indexed["remote"])):
        left = indexed["local"].get(path)
        right = indexed["remote"].get(path)
        if left and right:
            if left["kind"] != right["kind"] or left.get("slot") != right.get("slot"):
                raise ValueError(f"Inconsistent file classification: {path}")
            status = ("IDENTICAL" if left["sha256"].lower() == right["sha256"].lower()
                      else "DIFFERENT")
        else:
            status = "LOCAL_ONLY" if left else "REMOTE_ONLY"
        entry = left or right
        comparisons.append({
            "relative_path": path, "kind": entry["kind"], "slot": entry.get("slot"),
            "status": status,
            "local_sha256": left["sha256"] if left else None,
            "remote_sha256": right["sha256"] if right else None,
        })
        counts[status] += 1

    return {
        "platform": report.get("platform"), "complete": True,
        "matching_rule": "exact_relative_path",
        "read_only": True, "sync_decisions": False,
        "counts": counts, "files": comparisons,
    }
