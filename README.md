# RetroSync

RetroSync is a Python prototype for **read-only** inspection, comparison, and planning of RetroArch SRAM saves between a local device (such as a Steam Deck) and a NAS shared with Batocera.

## Status

**v0.9 — latest merged milestone (PR #9).** Validated on Steam Deck and merged on 2026-11-23.

The v0.9 platform preview has been exercised on a Steam Deck against a real NAS share (49 GBC files, two JSON reports and a human-readable report). The complete **118-test suite passed on Steam Deck** on 2026-11-23 (commit `0e0ea54`). These milestones are not necessarily packaged releases.

**No production save synchronization exists.** Normal inspection and planning commands never copy, overwrite, rename or delete saves. The only normal CLI file creation is an explicitly confirmed **new configuration file** via `--setup`. Experimental fixture-only copy/recovery modules are not wired to the CLI.

| Milestone | Capability |
| --- | --- |
| v0.1–v0.3 | Read-only inventory, SHA-256 SRAM decisions and plans |
| v0.4 | Local preflight, verified CIFS mount and terminal colors |
| v0.5–v0.6 | Isolated **fixture-only** copy and recovery experiments |
| v0.7 | Standalone Batocera RetroArch activity detector via SSH |
| v0.8 | Optional Batocera SSH activity check in `--check` |
| **v0.9 (PR #9)** | Guided setup, platform inventory, comparison and human report |

See [CHANGELOG.md](CHANGELOG.md) for milestone details, [development history](docs/DEVELOPMENT.md) for PRs and roadmap, and [architecture](docs/architecture.md) for safety boundaries.

## Requirements

- Python 3.9+
- For live NAS inventory on Linux: an **already mounted CIFS share** and `findmnt`
- For optional Batocera activity checks: OpenSSH client and independently configured, trusted key authentication
- No third-party Python packages

## Configuration

Use `config.example.json` as a starting point or the `--setup` wizard. Keep the real `config.json` private: **never commit personal configuration or SSH private keys**.

Schema version **1** remains in use and explicitly lists games for the existing per-game planner. The new platform preview does **not** persist platform mappings or automatically add games to the configuration.

An optional Batocera SSH endpoint can be declared:

```json
"batocera": {
  "host": "BATOCERA_HOST",
  "user": "root"
}
```

This enables read-only RetroArch activity detection in `--check`. It does **not** set up SSH trust or install keys; see [manual SSH setup](docs/SSH_SETUP.md).

## Guided setup (v0.9)

```bash
mkdir -p ~/retro-sync-lab
python3 retro_sync.py --config ~/retro-sync-lab/config.json --setup --dry-run
python3 retro_sync.py --config ~/retro-sync-lab/config.json --setup
```

The wizard asks for a device ID, existing NAS mount and expected CIFS source, NAS saves root, **one game**, its local and NAS-relative save directories, and an optional Batocera SSH endpoint. `--dry-run` only previews the proposed JSON. Without `--dry-run`, confirmation with `y` or `yes` creates a **new** configuration file with restrictive permissions. Existing files are never overwritten, and the parent directory must already exist.

Setup does not mount NAS shares, enroll SSH keys, modify SSH settings, or touch save files.

## Read-only platform preview (v0.9)

With an existing schema-v1 configuration and a verified CIFS mount:

```bash
python3 retro_sync.py --config ~/retro-sync-lab/config.json --platform-preview
```

The interactive preview asks for a platform ID (for example `gbc`), an absolute local save directory, a NAS-relative platform directory, and declared emulator/core information for each side. It scans **flat directories only** for `.srm`, `.state` and `.stateN` files. Subdirectories and symlinks are rejected; unknown extensions are ignored.

Output, in order:

1. **Inventory JSON**: both endpoints, filenames, category, state slot, size, modification time and SHA-256.
2. **Comparison JSON**: exact-relative-filename matches classified as `IDENTICAL`, `DIFFERENT`, `LOCAL_ONLY` or `REMOTE_ONLY`.
3. **Human-readable report**: SRAM/state counts, divergent and one-sided SRAM, same-side identical SRAM content under different filenames, and core compatibility warnings.

The comparison is by **exact relative filename**; SHA-256 determines whether matching filenames have identical contents. Timestamps do **not** select winners. Equal hashes under different filenames are advisory, **not proof of identical games**. Declared cores (including `unknown`) are not verified compatibility evidence. Save states are inventoried but **not synchronization candidates**.

The preview verifies the expected CIFS mount before scanning the NAS and makes **no configuration or save changes**.

## Existing per-game inventory and preflight

```bash
python3 retro_sync.py --config config.json --check
python3 retro_sync.py --config config.json --check --json
python3 retro_sync.py --config config.json --baseline baseline.json
python3 retro_sync.py --config config.json --json
python3 retro_sync.py --config config.json --check --color never
```

`--check` reports local and optional remote conditions. Batocera RetroArch `RUNNING` becomes `FAIL`, `STOPPED` becomes `PASS`, and SSH failure or unrecognized output becomes advisory `UNKNOWN`. A local failure or observed remote `RUNNING` produces exit code 2. An `UNKNOWN` result is **not** permission for future writes, and a `STOPPED` snapshot is not a lock.

The original per-game SRAM planner can propose `PUSH` or `PULL` when a trusted baseline supports a decision, but never executes the proposal. Missing files do not imply deletion.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The unit suite uses disposable fixtures and does not require live NAS or SSH access. **112 tests were confirmed passing** on Steam Deck before the final v0.9 report additions. The complete **118-test suite passed** on Steam Deck on 2026-11-23 (commit `0e0ea54`, 0.053 s). The human-readable report was exercised successfully against the live GBC inventory.

## Safety and next steps

All normal save operations remain read-only. `safe_copy.py` and `recovery.py` are **isolated fixture-only experiments**, not production tools. Do not run them against real saves.

Future SRAM conflict handling may offer an **opt-in** per-platform policy: `manual` (default), `prefer_local`, or `prefer_remote`. **Not implemented in v0.9.** One-sided files/deletions require separate rules, and save states remain excluded. Any future write mode needs reliable backups, quiescence and multi-writer coordination, hash rechecks, crash recovery and SMB-aware durability.

## Credits and license

RetroSync is created and maintained by [TheDiB](https://github.com/TheDiB), with development assistance from [ChatGPT by OpenAI](https://chatgpt.com) for design discussions, Python implementation, documentation and tests. All changes are reviewed and validated by the project maintainer.

Licensed under MIT.
