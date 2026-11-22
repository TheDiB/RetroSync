# RetroSync architecture (v0.9 design)

RetroSync inventories local and NAS-backed RetroArch saves without modifying them.

- Steam Deck: Python agent; local saves remain available offline.
- NAS: shared save repository, mounted through CIFS on Linux.
- Batocera: accesses the NAS share directly, with system-specific save folders.
- Local saves may be grouped by core (e.g. mGBA); Batocera saves may be grouped by system (e.g. gbc).
- Existing schema v1 explicitly lists games; v0.9 setup initially creates one such entry.
- Each discovered file is hashed with SHA-256. Timestamps are informational, never synchronization authority.
- The agent verifies the expected CIFS mount before accessing NAS files.

## Platform discovery proposal (v0.9)

**Design only, not yet a supported config schema or synchronization mode.** A future read-only discovery stage will scan configured pairs of local and NAS save directories, using bounded, explicit platform mappings instead of one user-entered entry per ROM.

Discovery must inventory both categories from the outset:

| Category | Recognized examples | Discovery | Synchronization |
| --- | --- | --- | --- |
| SRAM | `.srm` | Names, relative paths, size, mtime, SHA-256 | Existing read-only decision/plan only |
| Save states | `.state`, `.state1`, `.state2` | Names, relative paths, slot suffix, size, mtime, SHA-256 | **Not planned for execution in v0.9** |
| Other files | Unknown extensions, metadata, screenshots | Report or ignore according to a future explicit policy | Never implicitly synchronize |

A state slot is a **filename observation**, not proof of compatibility. Some emulators use other extensions, compression, companion files, per-core formats, or slot naming conventions. These require explicit future adapters, not guesses.

### Discovery invariants

1. Read-only scan: no copy, rename, delete, baseline update, or SSH changes.
2. Scan both sides independently; files present on only one side must remain visible.
3. Keep file category and full relative path; do not collapse different cores, platforms, or slots into the same logical identity.
4. Do not use modification times or filename matches to resolve divergent content automatically.
5. Never follow symlinks outside a configured root; treat inaccessible files, path collisions, and ambiguous mappings as uncertainty.
6. Bound traversal and report failures explicitly; a partial scan must not masquerade as a complete inventory.
7. Preserve the existing schema v1 and SRAM decision engine until a separately tested migration or adapter is designed.
8. State compatibility must be established independently of matching hashes or slot numbers; no state synchronization until that policy exists.

### Test fixtures to build before enabling discovery

- Hundreds or thousands of synthetic filenames (not actual ROMs).
- Mixed `.srm`, `.state`, `.stateN`, and unrelated extensions.
- Missing-on-one-side saves; differing content; duplicate basenames in distinct subdirectories.
- Symlinks, unreadable entries, traversal boundaries, malformed filenames and changing files.
- Windows and Linux path representations, plus case-collision behavior.

## Safety

All current CLI operations are read-only. `safe_copy.py` and `recovery.py` are fixture-only experiments, not production synchronization tools. Before any future write mode, RetroSync needs verified backups, multi-writer coordination, integrity rechecks, SMB-aware durability, crash recovery and fail-closed conflict handling.
