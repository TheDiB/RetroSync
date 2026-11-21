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
