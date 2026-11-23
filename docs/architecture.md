# RetroSync architecture (v0.9 release candidate)

RetroSync currently inventories and compares local and NAS-backed RetroArch saves **without changing save files**.

- **Steam Deck / local device:** Python agent; local saves remain available offline.
- **NAS:** shared save repository mounted through CIFS on Linux; expected source verified before a CLI NAS scan.
- **Batocera:** accesses the NAS share directly; optional SSH process detection is a read-only advisory check, **not** a direct inventory of Batocera's own storage.
- Local saves may be grouped by core (e.g. mGBA); NAS/Batocera saves may be grouped by system (e.g. gbc).
- **Schema v1:** explicitly lists individual games for the existing planner. The v0.9 wizard creates one game entry; platform mappings entered in the preview are not persisted.
- File SHA-256 determines byte equality. Timestamps are informational, never synchronization authority.

## Read-only platform discovery and comparison (v0.9)

The CLI exposes `--platform-preview`, implemented using `platform_discovery.py`, `platform_comparison.py` and `platform_report.py`. It prompts for a local platform directory, a NAS-relative platform directory and declared emulator/core identities.

The first implementation scans **flat directories only**, rejecting subdirectories and symlinks. It does not infer game identities, verify declared cores, or discover every platform automatically.

| Category | Recognized examples | Observations | Synchronization |
| --- | --- | --- | --- |
| SRAM | `.srm` | Exact filename, size, mtime, SHA-256 | Read-only comparison; existing per-game planner is separate |
| Save states | `.state`, `.state1`, `.state2` | Exact filename, slot suffix, size, mtime, SHA-256 | **Inventory only; no automatic synchronization** |
| Other files | Metadata, screenshots, unknown extensions | Ignored by the current flat scan | Never implicitly synchronized |

The preview prints three successive outputs:

1. Complete local/NAS inventory JSON.
2. Exact-relative-filename comparison JSON with `IDENTICAL`, `DIFFERENT`, `LOCAL_ONLY`, `REMOTE_ONLY`.
3. Human-readable counts split by SRAM/state, divergent and one-sided SRAM, duplicate-content advisories and core warnings.

A save-state slot is a **filename observation**, not proof of compatibility. Equal hashes under different names do not prove two games are the same. Unknown or different cores require caution; even identical declared cores are not a compatibility guarantee.

### Safety invariants

1. Discovery, comparison and reporting are read-only: no copy, rename, deletion, baseline update, config update or SSH change.
2. Verify the expected CIFS source before reading the NAS through the CLI.
3. Scan endpoints independently; one-sided files remain visible and never imply deletion.
4. Compare by exact relative filename, not by hash-only identity; retain category and state slot.
5. Do not use mtime to select a winner or resolve divergent SRAM.
6. Reject subdirectories and symlinks in the initial flat scan; bound traversal and fail closed rather than presenting partial results as complete.
7. Preserve schema v1 and the existing per-game SRAM decision/planner until a separately tested migration is designed.
8. Do not synchronize save states without independently established format/core compatibility.
9. Do not let a future `prefer_local` or `prefer_remote` setting bypass backups, activity checks, integrity rechecks or recovery.

## Future conflict policy (not implemented in v0.9)

Potential opt-in SRAM authority policies: `manual` (default), `prefer_local`, `prefer_remote`. These apply to **divergent SRAM**, not implicitly to one-sided files, deletions or save states. A policy preference is not a write authorization.

## Validation and limitations

The GBC preview and human report have been exercised against 49 real files on Steam Deck. The final **118-test** suite passed on Steam Deck on 2026-11-23 (commit `0e0ea54`). Further testing should include larger libraries, changing files during scan, unusual names, case collisions, nested layouts and cross-platform path behavior.

All current save-facing CLI operations remain read-only. `safe_copy.py` and `recovery.py` are fixture-only experiments, not production tools. Any future write mode requires verified backups, multi-writer coordination, integrity rechecks, SMB-aware durability and crash recovery.
