"""Pure SRAM policy proposals. Never grants write permission."""
from configuration import resolve_policy
from decision import decide, _hash
from platform_baseline import platform_baseline_hash
from platform_comparison import compare_platform


def propose_sram(local_hash, remote_hash, baseline_hash=None, policy=None):
    policy = resolve_policy(policy)
    local, remote, baseline = map(_hash, (local_hash, remote_hash, baseline_hash))
    status = decide(local, remote, baseline)
    action = "BLOCKED"
    if status == "IN_SYNC":
        action = "NOOP"
    elif status in ("PUSH", "PULL"):
        action = status + "_PROPOSED"
    elif status in ("CONFLICT", "INITIAL_CONFLICT"):
        action = {"manual": "BLOCKED", "prefer_local": "PUSH_PROPOSED",
                  "prefer_remote": "PULL_PROPOSED"}[policy["sram"]]
    elif status in ("MISSING_LOCAL", "MISSING_REMOTE"):
        side = status.removeprefix("MISSING_")
        if policy["missing"] != "block":
            if baseline is None:
                action = "CREATE_" + side
            elif policy["missing"] == "restore":
                action = "RESTORE_" + side
            else:
                action = "CONFIRM_RESTORE"
    return {"classification": status, "action": action,
            "local_sha256": local, "remote_sha256": remote,
            "baseline_sha256": baseline, "policy": policy,
            "write_authorized": False}


def propose_platform(item, history):
    """Use a complete scan item and previously validated device history."""
    identifier = item["id"]
    inventory = item["inventory"]
    comparison = compare_platform(inventory)
    if comparison["platform"] != identifier or comparison != item["comparison"]:
        raise ValueError("Platform inventory/comparison mismatch")
    policy = resolve_policy(item["policy"])
    files = {f["relative_path"]: f for f in comparison["files"]}
    tracked = history.get(identifier, {}).get("files", {})
    proposals = []
    for name in sorted(set(files) | set(tracked)):
        entry = files.get(name)
        if entry is not None and entry["kind"] == "STATE":
            if name in tracked:
                raise ValueError("Baseline conflicts with save state classification")
            continue
        baseline = platform_baseline_hash(history, identifier, name)
        proposal = propose_sram(entry["local_sha256"] if entry else None,
                                entry["remote_sha256"] if entry else None,
                                baseline, policy)
        proposals.append({"relative_path": name, **proposal})
    return {"id": identifier, "read_only": True, "write_authorized": False,
            "attribution_verified": False, "compatibility_verified": False,
            "policy": policy, "files": proposals,
            "states_excluded": sum(f["kind"] == "STATE" for f in files.values())}
