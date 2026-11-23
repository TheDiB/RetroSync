# Changelog

RetroSync uses incremental development milestones; these are **not necessarily packaged releases**. A milestone listed as a release candidate is not yet merged.

## v0.10 — merged (PR #10, 2026-11-23)

- Add schema-v2 platform mappings and inherited conflict/missing-file policies, preserving schema-v1 workflows.
- Add offline configuration validation, bounded non-interactive scan and global read-only SRAM plan, with optional platform selection and JSON output.
- Validate per-device, per-platform historical hashes and UTC timestamps; reject invalid or explicitly missing history.
- Resolve local parent aliases, reject overlapping endpoints and remote symlinks, recheck mount and endpoint identity.
- Separate classification from conflict and missing-file proposals; never propagate deletion or authorize writes.
- Add standalone HTML simulator and 576 shared reference cases.
- Validation at `567cf41`: SteamOS 186 passed; Windows 178 passed, 8 symlink privilege skips; browser 576/576 offline and HTTP. Live GBC plans with and without synthetic history covered 9 SRAM and excluded 40 states.

## v0.9 — merged (PR #9, 2026-11-23)

- Add `--setup` guided configuration with `--dry-run`, explicit `y`/`yes` confirmation, restrictive permissions and exclusive creation of a **new** schema-v1 config file.
- Preserve existing configuration files; do not mount shares, enroll SSH keys, or modify save files.
- Add interactive `--platform-preview` for read-only flat-directory discovery of SRAM and RetroArch `.state`/`.stateN` files on the local device and verified NAS mount.
- Include declared emulator/core identity, file sizes, timestamps and SHA-256 in the inventory JSON.
- Add read-only exact-filename comparison JSON: `IDENTICAL`, `DIFFERENT`, `LOCAL_ONLY`, `REMOTE_ONLY`. No winner is inferred from timestamps.
- Add human-readable SRAM/state totals, divergent and one-sided SRAM, same-side duplicate-content advisories, and compatibility warnings.
- Keep save states inventory-only; no production copy, overwrite, deletion, conflict resolution or SSH enrollment.
- **Validation:** 112 tests passed on Steam Deck before the final report additions. The live GBC platform preview and human report succeeded (49 files). The final **118-test** suite passed on Steam Deck on 2026-11-23 (commit `0e0ea54`, 0.053 s).

## v0.8 — merged (PR #8)

- Add optional `batocera.host` / `batocera.user` configuration for read-only SSH preflight.
- Map remote RetroArch `RUNNING` to `FAIL`, `STOPPED` to `PASS`, and unreachable/unrecognized to advisory `UNKNOWN`.
- Refresh README and manual SSH onboarding documentation. No synchronization writes.

## v0.7 — merged (PR #7)

- Add standalone `remote_activity.py` SSH detector with strict host-key checking, batch authentication and process-list validation.
- Recognize Batocera `<defunct>` processes without counting zombie RetroArch as running.
- Validate `RUNNING` and `STOPPED` against Batocera 44 from Steam Deck; 81 tests passed at v0.7.

## v0.6 — merged (PR #6)

- Add fixture-only backup inspection and verified candidate export in `recovery.py`; no automatic restore.

## v0.5 — merged (PR #5)

- Add fixture-only hash-verified staged copy and retained backup in `safe_copy.py`, disconnected from CLI.

## v0.4 — merged (PR #4)

- Add local RetroArch process checks, CIFS mount preflight and terminal status colors.

## v0.3 — merged (PR #3)

- Add read-only SRAM planner with blocked conflicts and proposed copies.

## v0.2 — merged (PR #2)

- Add SHA-256 SRAM decision engine with optional trusted historical baseline.

## v0.1 — merged (PR #1)

- Add read-only local/NAS inventory and mounted-share validation.

## Limitations

No production write mode, multi-writer lock protocol, automatic execution of SRAM priority policies, cross-client coordination or save-state reconciliation is implemented.
