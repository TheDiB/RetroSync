# Development history and roadmap

## Pull requests

| PR | Milestone | Scope |
| --- | --- | --- |
| [#1](https://github.com/TheDiB/RetroSync/pull/1) | v0.1 | Read-only inventory |
| [#2](https://github.com/TheDiB/RetroSync/pull/2) | v0.2 | SRAM hash decisions |
| [#3](https://github.com/TheDiB/RetroSync/pull/3) | v0.3 | Read-only planner |
| [#4](https://github.com/TheDiB/RetroSync/pull/4) | v0.4 | Preflight and colors |
| [#5](https://github.com/TheDiB/RetroSync/pull/5) | v0.5 | Fixture-only copy |
| [#6](https://github.com/TheDiB/RetroSync/pull/6) | v0.6 | Fixture-only recovery |
| [#7](https://github.com/TheDiB/RetroSync/pull/7) | v0.7 | Batocera SSH detector |
| [#8](https://github.com/TheDiB/RetroSync/pull/8) | v0.8 | Remote preflight and documentation |
| [#9](https://github.com/TheDiB/RetroSync/pull/9) | v0.9 (merged) | Guided setup, platform discovery, comparison and human report |

| [#10](https://github.com/TheDiB/RetroSync/pull/10) | v0.10 (merged) | Platform configuration, history, policy planning and simulator |

## v0.9 validation

- **Confirmed:** 112 tests passed on Steam Deck before the final human-report changes.
- **Confirmed:** live GBC inventory/comparison and human-readable report ran successfully on Steam Deck against a mounted NAS (49 files).
- **Confirmed:** complete **118-test** suite passed on Steam Deck on 2026-11-23 (commit `0e0ea54`, 0.053 s).
- **Confirmed:** maintainer merged PR #9 on 2026-11-23 (`fe13a78`); merged content matches the final feature branch.

## Safety decisions

- Save inventory, comparison, planning and preflight are read-only.
- `--setup` is an exception only for creating a **new**, explicitly confirmed configuration file; it never changes saves.
- `UNKNOWN` means insufficient evidence, **not** that Batocera is off.
- `STOPPED` means no RetroArch process was observed at one instant, **not** that NAS writes are safe.
- The platform preview compares exact filenames; identical SHA-256 values across different filenames are **not** proof of game identity.
- Save states are inventory-only; declared core identity does not establish compatibility.
- Experimental copy/recovery modules are restricted to disposable fixtures; never use on production saves.
- Other emulators, NAS clients, time-of-check/time-of-use races, locking and crash consistency remain open problems.

## v0.10 validation and closure

All eight development stages have been implemented: schema v2, CLI integration, non-interactive discovery, platform baselines, policies, global plan, HTML simulator and final validation/documentation.

- Tested code: `567cf41`.
- Windows: 186 tests collected, 178 passed, 8 skipped for symlink privileges.
- SteamOS: 186 passed, no skips.
- Browser: 576/576 shared reference cases passed both offline and via HTTP.
- Live GBC: 9 SRAM, 40 states excluded; no-history and synthetic-history plans, all three conflict and missing-file policies, invalid baseline/platform and incompatible CLI modes checked.
- Synthetic history is test data only, not evidence of real synchronization.
- PR #10 merged on 2026-11-23 (`67dd2fa`); release tagging and Pages publication are separate steps.

## Future work

Verify platform attribution, save compatibility and baseline provenance; design safe creation/overwrite, writer coordination, backup, recovery and durability before production writes. Nested layouts and SSH onboarding remain future work. Publish the simulator through GitHub Pages after merge if enabled.

