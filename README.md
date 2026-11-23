# RetroSync

RetroSync is a Python prototype for **read-only** inspection, comparison, and planning of RetroArch SRAM saves between a local device (such as a Steam Deck) and a NAS shared with Batocera.

## Status

**v0.10 — validated release candidate (PR #10, pending merge).** Latest merged milestone: v0.9.

The v0.10 candidate passed 186 tests on SteamOS and 178 on Windows (8 symlink privilege skips), at commit `567cf41`. The HTML simulator passed all 576 shared reference scenarios offline and over HTTP. Live GBC planning was validated with and without synthetic history.

**No production save synchronization exists.** Normal inspection and planning commands never copy, overwrite, rename or delete saves. The only normal CLI file creation is an explicitly confirmed **new configuration file** via `--setup`. Experimental fixture-only copy/recovery modules are not wired to the CLI.

| Milestone | Capability |
| --- | --- |
| v0.1–v0.3 | Read-only inventory, SHA-256 SRAM decisions and plans |
| v0.4 | Local preflight, verified CIFS mount and terminal colors |
| v0.5–v0.6 | Isolated **fixture-only** copy and recovery experiments |
| v0.7 | Standalone Batocera RetroArch activity detector via SSH |
| v0.8 | Optional Batocera SSH activity check in `--check` |
| v0.9 (PR #9) | Guided setup, platform inventory, comparison and human report |
| **v0.10 (PR #10)** | Schema v2, non-interactive scan, platform history, SRAM policy proposals and HTML simulator |

See [CHANGELOG.md](CHANGELOG.md) for milestone details, [development history](docs/DEVELOPMENT.md) for PRs and roadmap, and [architecture](docs/architecture.md) for safety boundaries.

## Requirements

- Python 3.9+
- For live NAS inventory on Linux: an **already mounted CIFS share** and `findmnt`
- For optional Batocera activity checks: OpenSSH client and independently configured, trusted key authentication
- No third-party Python packages

## Configuration

Use `config.example.json` as a starting point or the `--setup` wizard. Keep the real `config.json` private: **never commit personal configuration or SSH private keys**.

Schema version **1** remains supported for the existing per-game planner, setup and preview. Schema **2** explicitly maps platforms for non-interactive scanning and planning; it does not automatically infer game or platform identity.

An optional Batocera SSH endpoint can be declared:

```json
"batocera": {
  "host": "BATOCERA_HOST",
  "user": "root"
}
```

This enables read-only RetroArch activity detection in `--check`. It does **not** set up SSH trust or install keys; see [manual SSH setup](docs/SSH_SETUP.md).

## Platform configuration and planning (v0.10)

Example schema-v2 configuration (replace paths and share with your own):

```json
{
  "schema_version": 2,
  "device_id": "my-device",
  "nas": {"mount": "/mnt/nas", "expected_source": "//nas/Emulation", "remote_root": "Save"},
  "policy": {"sram": "manual", "missing": "create_new"},
  "platforms": [{
    "id": "gbc",
    "local": {"emulator": "retroarch", "core": "mgba", "save_dir": "/home/user/saves/gbc"},
    "remote": {"emulator": "retroarch", "core": "unknown", "save_dir": "gbc"}
  }]
}
```

Save privately as `config-v2.json`. The v2 CLI supports only these three modes:

```bash
python3 retro_sync.py --config config-v2.json --validate-config
python3 retro_sync.py --config config-v2.json --scan --platform gbc
python3 retro_sync.py --config config-v2.json --plan
python3 retro_sync.py --config config-v2.json --plan --baseline baseline-v2.json --json
```

Omit `--platform` to include all configured platforms. Validation is offline; scan and plan require the verified CIFS mount. All configured endpoint directories are checked for overlap even when selecting one platform. Local parent aliases may resolve to physical directories; remote symlinks and symlinked endpoint directories are refused. Use separate flat directories per platform.

Policies inherit defaults, then global settings, then optional per-platform overrides. `sram`: `manual` (default), `prefer_local`, `prefer_remote` apply only to conflicts. `missing`: `block`, `create_new` (default), `restore`. With no recorded history, creation may be proposed; a previously tracked missing file requires confirmation under `create_new`, or a restoration proposal under `restore`. Both missing is blocked. No deletion is proposed.

An optional v2 baseline contains `schema_version: 2`, the matching `device_id`, and a `platforms` object keyed by platform ID, each containing a `files` object keyed by exact SRAM filename. Each entry contains a 64-digit hexadecimal `last_synced_sha256` and UTC `last_synced_at` ending in Z. Explicit missing or invalid baseline files fail; omitting the option means no history. RetroSync does not create or update this history, and structural validation does not establish provenance.

All actions are proposals only. Save states are excluded from plans; attribution, compatibility and baseline provenance remain unverified. No write is authorized.

### SRAM simulator

Open [docs/simulator.html](docs/simulator.html) locally in a browser, or serve the docs directory with `python3 -m http.server 8080 --directory docs` and open `http://localhost:8080/simulator.html`. Run reference checks using the adjacent `simulator-scenarios.json` (select manually in offline mode). The same 576 cases are checked by Python tests. No real saves are accessed by the simulator.

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

The unit suite uses disposable fixtures and does not require live NAS or SSH access. At `567cf41`, 186 tests passed on SteamOS; Windows passed 178 with 8 symlink privilege skips. Live GBC plans covered 9 SRAM files and excluded 40 save states.

## Safety and next steps

All normal save operations remain read-only. `safe_copy.py` and `recovery.py` are **isolated fixture-only experiments**, not production tools. Do not run them against real saves.

SRAM conflict and missing-file policies are implemented as read-only proposals in v0.10. Any future write mode needs verified attribution and compatibility, trustworthy history, reliable backups, quiescence and multi-writer coordination, hash rechecks, crash recovery and SMB-aware durability.

## Credits and license

RetroSync is created and maintained by [TheDiB](https://github.com/TheDiB), with development assistance from [ChatGPT by OpenAI](https://chatgpt.com) for design discussions, Python implementation, documentation and tests. All changes are reviewed and validated by the project maintainer.

Licensed under MIT.
