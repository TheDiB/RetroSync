"""Read-only synchronization planner for SRAM files.

Plans are proposals, never commands: this module performs no filesystem writes.
A plan must be rebuilt from fresh inventory before any future execution.
"""

from decision import decide


def plan_sram(local_path, remote_path, local_hash, remote_hash, baseline_hash):
    """Build a conservative, serializable plan from observed SHA-256 values.

    An absent baseline never permits a directional copy. Missing files and
    divergent edits always require explicit human review.
    """
    decision = decide(local_hash, remote_hash, baseline_hash)
    plan = {
        "decision": decision,
        "operation": "NONE",
        "source": None,
        "destination": None,
        "expected_source_sha256": None,
        "expected_destination_sha256": None,
        "requires_review": False,
        "reason": None,
        "read_only": True,
    }
    if decision == "IN_SYNC":
        plan["reason"] = "Both observed SRAM hashes match; no copy needed."
    elif decision in ("PULL", "PUSH"):
        if decision == "PULL":
            source, destination = remote_path, local_path
            source_hash, destination_hash = remote_hash, local_hash
        else:
            source, destination = local_path, remote_path
            source_hash, destination_hash = local_hash, remote_hash
        if not source or not destination or str(source) == str(destination):
            raise ValueError("Distinct source and destination paths are required")
        plan.update(operation="COPY_PROPOSED", source=str(source),
                    destination=str(destination),
                    expected_source_sha256=source_hash.lower(),
                    expected_destination_sha256=destination_hash.lower(),
                    reason="One side differs from a trusted last-synced baseline.")
    else:
        plan.update(operation="BLOCKED", requires_review=True,
                    reason={
                        "CONFLICT": "Both sides changed since the baseline.",
                        "INITIAL_CONFLICT": "No trusted common baseline exists.",
                        "MISSING_LOCAL": "Local SRAM is absent; no automatic restoration.",
                        "MISSING_REMOTE": "Remote SRAM is absent; no automatic restoration.",
                        "MISSING_BOTH": "Both SRAM files are absent.",
                    }[decision])
    return plan
