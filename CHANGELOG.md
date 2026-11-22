## v0.9 (in development)

- First interactive `--setup` configuration wizard and `--dry-run` preview.
- Explicit confirmation, exclusive new-file creation, and refusal to overwrite existing configs.
- No automatic SSH enrollment, NAS mounting, or save writes.

# Changelog

RetroSync uses incremental development milestones. These are project milestones, not necessarily packaged releases.

## v0.8 — in development (PR #8)
- Optional `batocera.host` / `batocera.user` configuration for read-only SSH preflight.
- Map remote RetroArch RUNNING to FAIL, STOPPED to PASS and unreachable/unrecognized to advisory UNKNOWN.
- Refresh README and document SSH onboarding. No synchronization writes.

## v0.7 — merged (PR #7)
- Standalone `remote_activity.py` SSH detector; strict host-key checking, batch authentication, process-list validation.
- Recognize Batocera `<defunct>` process listings; do not count zombie RetroArch as running.
- Validated RUNNING and STOPPED against Batocera 44 from Steam Deck; 81 unit tests passed at v0.7.

## v0.6 — merged (PR #6)
- Fixture-only read-only backup inspection and verified candidate export in `recovery.py`; no automatic restore.

## v0.5 — merged (PR #5)
- Fixture-only hash-verified staged copy and retained backup in `safe_copy.py`, disconnected from CLI.

## v0.4 — merged (PR #4)
- Local RetroArch process checks, CIFS mount preflight and colored terminal statuses.

## v0.3 — merged (PR #3)
- Read-only SRAM synchronization planner with explicit blocked conflicts and proposed copies.

## v0.2 — merged (PR #2)
- SHA-256 SRAM decision engine using an optional trusted historical baseline.

## v0.1 — merged (PR #1)
- Read-only local/NAS inventory and mounted-share validation.

## Limitations

No production write mode, lock protocol, cross-client coordination, or save-state reconciliation is implemented.
