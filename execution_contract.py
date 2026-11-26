"""Pure execution contract; no I/O, authorization capability or executor."""
from platform_policy import propose_sram
from platform_baseline import _filename

_DIRECTIONS = {
    "CREATE_LOCAL": ("remote", "local", "CREATE"),
    "CREATE_REMOTE": ("local", "remote", "CREATE"),
    "RESTORE_LOCAL": ("remote", "local", "RESTORE"),
    "RESTORE_REMOTE": ("local", "remote", "RESTORE"),
    "PUSH_PROPOSED": ("local", "remote", "REPLACE"),
    "PULL_PROPOSED": ("remote", "local", "REPLACE"),
}


def assess_candidate(proposal):
    """Validate a v2 file proposal and describe a non-executable candidate.

    Never trusts a serialized authorization flag or grants permission.
    Endpoint identity, caller intent and runtime evidence belong to later
    stages; this result is not a transferable authorization token.
    """
    if not isinstance(proposal, dict):
        raise ValueError("Expected file proposal")
    _filename(proposal.get("relative_path"))
    required = ("local_sha256", "remote_sha256", "baseline_sha256", "policy",
                "classification", "action", "write_authorized")
    if any(key not in proposal for key in required):
        raise ValueError("Incomplete file proposal")
    if proposal["write_authorized"] is not False:
        raise ValueError("Proposal must not authorize writes")
    expected = propose_sram(proposal["local_sha256"], proposal["remote_sha256"],
                            proposal["baseline_sha256"], proposal["policy"])
    if any(proposal[key] != value for key, value in expected.items()):
        raise ValueError("Inconsistent file proposal")
    action = expected["action"]
    result = {"relative_path": proposal["relative_path"], "action": action,
              "status": "BLOCKED", "reason": "POLICY_BLOCKED",
              "candidate": None, "write_authorized": False}
    if action == "NOOP":
        result.update(status="NOOP", reason="ALREADY_IN_SYNC")
    elif action == "CONFIRM_RESTORE":
        result["reason"] = "RESTORE_CONFIRMATION_REQUIRED"
    elif action in _DIRECTIONS:
        source, destination, operation = _DIRECTIONS[action]
        result["candidate"] = {
            "operation": operation, "source_side": source,
            "destination_side": destination,
            "expected_source_sha256": expected[source + "_sha256"],
            "expected_destination_sha256": expected[destination + "_sha256"],
            "baseline_sha256": expected["baseline_sha256"],
            "policy": expected["policy"],
        }
        result["reason"] = "RUNTIME_AUTHORIZATION_NOT_IMPLEMENTED"
    return result
