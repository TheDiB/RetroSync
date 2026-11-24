# Execution contract (v0.11.1)

The v0.10 planner remains read-only. This milestone defines requirements, not a production write capability.

## Boundaries

Classification describes observed hashes; policy proposes an action; authorization evaluates current evidence; execution performs a transaction. A report, configuration preference, CLI confirmation or serialized boolean is never a write capability. The core must not prompt, exit the process, or depend on a terminal. CLI, future service and hooks share the same core.

## Operation contract

Each candidate binds device, platform, exact flat SRAM filename, resolved endpoint identities, direction, expected source and destination SHA-256 (null destination means absent), baseline identity and policy. Recompute the proposal from fresh observations under coordination; never execute a saved report. Reject ambiguous names, aliases, unsupported types, overlapping endpoints and unknown actions. No deletion or save-state transfer.

| Proposal | Candidate |
| --- | --- |
| NOOP | None |
| BLOCKED / CONFIRM_RESTORE | None; intervention or policy change |
| CREATE_LOCAL / CREATE_REMOTE | Exclusive creation only, destination absent |
| RESTORE_LOCAL / RESTORE_REMOTE | Exclusive creation only, destination absent, trusted history |
| PUSH_PROPOSED / PULL_PROPOSED | Replacement only, both hashes present and different |

## Required evidence

All applicable requirements must be established by trusted runtime adapters, not user-supplied report flags. Missing, failed or unknown evidence blocks execution.

- Explicit caller intent scoped to device/platform/file and permitted operation; future enrolled policy may supply intent without interaction.
- Verified current mount and endpoint identities, platform/game attribution and SRAM compatibility.
- Verified history provenance whenever history informs a decision; no-history creation is not proof of a new game.
- Coordination covering all relevant writers, including emulator launch prevention for the duration of the operation. Process snapshots alone are insufficient; unreachable clients are not assumed stopped. A RetroSync-only lock cannot exclude uncooperative NAS writers.
- Fresh source/destination observations under coordination, rechecked before commit; no overwrite on creation.
- Verified backup before replacement, durable staging, journal and recovery strategy appropriate to the filesystem and SMB semantics.
- Verify destination and source stability after commit before advancing device-specific history. Preserve recovery evidence on uncertainty; do not blindly retry.

## Result contract

Return structured results with stable reason codes, not prompts. Distinguish NOOP, BLOCKED (policy or invalid evidence), DEFERRED (temporary unavailability or contention), and later execution outcomes including success and recovery required. A deferred operation is replanned from fresh observations; never replay a stale transfer. An interrupted or uncertain commit requires reconciliation before retry.

## Current limitations

Existing safe_copy and recovery modules are fixture-only. Existing preflight is schema v1 and its remote UNKNOWN can be advisory; its exit code is not a write gate. STOPPED is only a process snapshot. The v2 planner explicitly reports unverified attribution, compatibility and baseline provenance. No production authorization or execution is enabled in v0.11.1. No CLI changes, filesystem writes or baseline updates are introduced by the contract module.

Future milestones must establish real evidence providers and coordination, test filesystem semantics and recovery, and preserve the fail-closed boundary before connecting production execution.
