# RetroSync

Read-only prototype for inspecting and planning RetroArch SRAM synchronization between a local device and a NAS shared with Batocera.

## Status

**v0.8 development (PR #8) — optional Batocera SSH activity in preflight.** Latest merged milestone: **v0.7** (remote RetroArch detector, tested on Batocera 44 and Steam Deck). All normal CLI operations remain read-only. There is **no production save synchronization or write mode**.

| Milestone | Capability |
| --- | --- |
| v0.1–v0.3 | Inventory, SHA-256 SRAM decisions and read-only plans |
| v0.4 | Preflight checks and terminal status colors |
| v0.5–v0.6 | Experimental **fixture-only** safe-copy and recovery audit (not connected to CLI) |
| v0.7 | Standalone Batocera SSH RetroArch detector |
| v0.8 (in progress) | Optional remote activity check in `--check`, plus documentation cleanup |

See [CHANGELOG.md](CHANGELOG.md) for detailed milestones and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for PR history and future work.

## Requirements

- Python 3.9+
- Linux and `findmnt` with an already mounted CIFS share for full inventory/preflight
- OpenSSH client and preconfigured, trusted key authentication for optional Batocera activity checks
- No third-party Python packages

## Configuration

Copy `config.example.json` to a private `config.json` and adjust device paths, NAS source, and games. **Never commit private configuration or SSH private keys.**

The optional `batocera` object enables the read-only SSH process check:

```json
"batocera": {
  "host": "192.168.1.75",
  "user": "root"
}
```

If omitted, remote activity stays `UNKNOWN` (advisory). Configure and verify SSH separately using [docs/SSH_SETUP.md](docs/SSH_SETUP.md); an automated `--setup` wizard is planned, not implemented.

## Usage

```bash
python3 retro_sync.py --config config.json --check
python3 retro_sync.py --config config.json --check --json
python3 retro_sync.py --config config.json --baseline baseline.json
python3 retro_sync.py --config config.json --json
python3 retro_sync.py --config config.json --check --color never
```

`--check` reports local and remote conditions. If configured, remote RetroArch `RUNNING` is reported as `FAIL`; `STOPPED` as `PASS`; SSH failures as `UNKNOWN` (advisory). A local `FAIL` or a remote `RUNNING` makes the diagnostic exit with code 2. An `UNKNOWN` remote state alone does not make `--check` fail, **but must never authorize future writes**. A remote `STOPPED` snapshot is not a lock: other emulators, NAS clients, or a newly launched game may still write.

The SRAM planner can propose `PUSH` or `PULL` with a trusted baseline, but does not execute either. Missing files are never treated as deletion instructions. Save states are inventoried, not synchronized.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Unit tests do not require a live NAS or SSH server. Test fixture write operations must **never** be used against real saves.

## Design and safety

See [docs/architecture.md](docs/architecture.md). Future write-enabled synchronization needs verified backups, locking/coordination with Batocera and other writers, integrity rechecks, crash recovery and SMB-aware durability. `safe_copy.py` and `recovery.py` are isolated experiments, **not production write tools**.

## Credits

RetroSync is created and maintained by [TheDiB](https://github.com/TheDiB), with development assistance from [ChatGPT by OpenAI](https://chatgpt.com) for design discussions, Python implementation, documentation, and tests. All changes are reviewed and validated by the project maintainer.

Licensed under MIT.
