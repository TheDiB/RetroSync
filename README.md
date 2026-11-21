# RetroSync

Read-only prototype for inspecting RetroArch SRAM and save states across local devices and a NAS.

## Status

**v0.2 development — read-only inventory and SRAM decisions.** No files are copied, modified, or deleted. Initial development and real-world testing target Steam Deck and a NAS shared with Batocera.

## Requirements

- Python 3.9+ (the code uses `str.removeprefix`)
- Linux with `findmnt` and a mounted CIFS share for the full inventory command
- No third-party Python dependencies

## Configuration

Copy `config.example.json` to `config.json` and adapt it for your device. **Do not commit `config.json`**, which may include personal paths and NAS addresses.

## Usage

```bash
python3 retro_sync.py
python3 retro_sync.py --json
python3 retro_sync.py --config /path/to/config.json
python3 retro_sync.py --baseline /path/to/trusted-baseline.json
```

## Tests

Cross-platform unit tests (no NAS required):

```bash
python -m unittest discover -s tests -v
```

## Design

See [docs/architecture.md](docs/architecture.md). The decision engine is implemented for SRAM only. Save-state reconciliation and synchronization transactions are future work.

Licensed under MIT.

## SRAM decision engine (v0.2)

The decision engine compares local and NAS SRAM SHA-256 hashes against an **optional, trusted last-synchronized hash**. It never copies files or changes the baseline.

- `IN_SYNC`: local and remote hashes match (does not establish a trusted historical baseline).
- `PUSH`: only the local hash differs from the trusted baseline.
- `PULL`: only the remote hash differs from the trusted baseline.
- `CONFLICT`: both hashes differ from the baseline and from each other.
- `INITIAL_CONFLICT`: local and remote differ, and no trusted baseline exists.
- `MISSING_LOCAL`, `MISSING_REMOTE`, `MISSING_BOTH`: one or both SRAM files are absent. **Never interpreted as deletion requests.**

To try a baseline, copy `baseline.example.json` to a **local file** such as `baseline.json`, set `device_id` to your configuration's value, and only set `last_synced_sha256` if you can prove that hash was the common version after an actual synchronization. Otherwise leave it `null`. Baseline files are ignored by Git.

For the historical Wario Land II experiment, the Steam Deck SRAM hash copied to the NAS was `91f6e75149f3f6477a9cdc72fd1d2879ddf3a24dc265a6687136f9303661018a`. With that trusted baseline, the previously observed NAS SRAM `14a77e2aa76063a636fd5f65223751baf086e11154e5317b49442ba74e66fa6b` should produce `PULL` if the files have not changed since. **Do not use those hashes as a baseline for unrelated devices or new save histories.**

`--json` includes `sram_decision` and `baseline_sha256` while retaining the v0.1 inventory and `sram_status` fields.

**Limitations:** only SRAM is classified; save states are still listed without sync decisions. The baseline is read-only and not persisted by RetroSync. Decisions are informational, not authorization to overwrite saves.

## Credits

RetroSync is created and maintained by [TheDiB](https://github.com/TheDiB), with development assistance from [ChatGPT by OpenAI](https://chatgpt.com) for design discussions, Python implementation, documentation, and tests. All changes are reviewed and validated by the project maintainer.

## Read-only synchronization plans (v0.3)

RetroSync now includes a conservative SRAM planner. Each game report contains `sram_plan`, which records the decision, proposed source/destination paths, the observed source/destination SHA-256 hashes, and whether manual review is required.

- `IN_SYNC` → `NONE`: no action.
- `PUSH` or `PULL` with a trusted baseline → `COPY_PROPOSED`: a **proposal only**, never executed.
- `CONFLICT`, `INITIAL_CONFLICT`, or missing files → `BLOCKED`: human review required; never assume deletion or overwrite.

Run the same commands as v0.2; optionally pass `--baseline /path/to/trusted-baseline.json`. Both console output and `--json` now show the plan.

**Safety boundary:** v0.3 does not copy, rename, delete, back up, or update any save or baseline. Proposed hashes are *observations*, not verified execution preconditions. Before any future write-enabled version, we must design and test: process/game shutdown detection, fresh hash verification immediately before commit, source/destination path and mount safety, locks, backup/rollback, temporary-file writes and atomic replacement (including SMB constraints), and baseline updates only after verified success. Save states remain inventory-only.

## Preflight diagnostics (v0.4)

Run `python3 retro_sync.py --config config.json --check` to inspect configuration, the exact CIFS NAS mount, local and remote game directories, and local RetroArch processes. Add `--json` for machine-readable checks. The command performs **no writes**, does not attempt to mount the NAS, and returns exit code `2` for blocking failures (or unknown local process state), `0` when local checks pass.

On Linux, process detection examines `/proc/<pid>/comm` and executable argv[0]. On Windows the process check reports `UNKNOWN`, so `--check` fails closed; Windows unit tests use a simulated Linux process tree. Process scanning is a diagnostic snapshot, not a guarantee that RetroArch cannot start afterward.

**Important:** `remote_emulator_activity: UNKNOWN` is an informational warning because RetroSync cannot determine whether Batocera or another NAS client has a game open. It does not by itself fail the diagnostic command, but **must block any future write-enabled synchronization** until remote concurrency is addressed. No write-enabled mode exists in v0.4. Existing inventory and planner commands remain read-only.

### Colored terminal status labels

Preflight labels are colored automatically when standard output is an interactive terminal: green `PASS`, red `FAIL`, yellow `UNKNOWN`/`WARN`, gray `SKIP`. Only the status label is colored. Colors are disabled for redirected output, `TERM=dumb`, or when the `NO_COLOR` environment variable is present. Use `--color always` to force ANSI colors or `--color never` for plain-text logs. The `--json` output is never colored, and exit codes are unchanged.

## Experimental safe-copy foundation (PR #5)

`safe_copy.py` contains `copy_fixture(...)`, an **isolated-fixture-only** experiment. It is deliberately **not imported by the CLI or planner**. It validates full SHA-256 preconditions, preserves the old destination in a uniquely named verified backup, stages the source in the destination directory, verifies staged bytes, rechecks both inputs, replaces the destination using `os.replace`, and verifies the result. The backup is retained for manual recovery.

Run `python -m unittest discover -s tests -v` to exercise it exclusively with disposable temporary files. **Do not call `copy_fixture` on actual RetroArch saves or NAS data.** This prototype has no inter-process lock, no Batocera coordination, no guarantee against TOCTOU races, and no full power-loss durability protocol (fsync/SMB semantics). Even a successful preflight cannot authorize a real write. Crash recovery and remote concurrency must be designed before a production executor is added.

## Experimental recovery audit (PR #6)

`recovery.py` is **fixture-only** and disconnected from the CLI. Given an explicit backup path and its *trusted* expected SHA-256, `inspect_fixture` reports whether the backup is missing, corrupt, or verified; optionally it compares the current destination with a trusted expected SHA-256. `export_backup_fixture` copies a verified backup to a **new, exclusively created path** for manual review; it never overwrites the destination and never restores automatically.

Tests use disposable local files only: `python -m unittest discover -s tests -v`. No automatic discovery of orphan staging files, no journal, no lock/coordination with Batocera, no atomic recovery transaction, and no guarantee against concurrent writers or power loss. A recovery candidate must be reviewed manually; never run this experimental code against real save files or the NAS.
