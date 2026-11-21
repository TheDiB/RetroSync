# RetroSync architecture (v0.1)

RetroSync currently inventories local and NAS-backed RetroArch saves without modifying them.

- Steam Deck: Python agent; local saves remain available offline.
- NAS: shared save repository, mounted through CIFS on Linux.
- Batocera: uses the NAS share directly, with system-specific save folders.
- The Steam Deck can organize saves by core (e.g. mGBA), while Batocera uses system folders (e.g. gbc).
- SRAM files (.srm) and save states (.state, .stateN) are inventoried separately.
- Each file is hashed with SHA-256. Timestamps are informational, not a synchronization authority.
- Before inventory, the agent checks that the configured CIFS share is mounted at the expected path.

## Planned v0.2

A read-only decision engine will compare local and remote SRAM hashes against a trusted last-synchronized baseline. Divergent copies without a baseline must not be automatically reconciled. Save-state slot naming varies by platform, so save-state reconciliation requires a separate design.

## Safety

No automatic copying, overwriting, deletion or manifest mutation is implemented in v0.1. Future writes require backups, mount verification, atomic operations, and conflict handling.
