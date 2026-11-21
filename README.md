# RetroSync

Read-only prototype for inspecting RetroArch SRAM and save states across local devices and a NAS.

## Status

**v0.1 — inventory only.** No files are copied, modified, or deleted. Initial development and real-world testing target Steam Deck and a NAS shared with Batocera.

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
```

## Tests

Cross-platform unit tests (no NAS required):

```bash
python -m unittest discover -s tests -v
```

## Design

See [docs/architecture.md](docs/architecture.md). The decision engine and synchronization transactions are future work.

Licensed under MIT.
