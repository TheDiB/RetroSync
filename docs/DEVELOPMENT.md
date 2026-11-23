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
| [#9](https://github.com/TheDiB/RetroSync/pull/9) | v0.9 (release candidate) | Guided setup, platform discovery, comparison and human report |

## v0.9 release-candidate validation

- **Confirmed:** 112 tests passed on Steam Deck before the final human-report changes.
- **Confirmed:** live GBC inventory/comparison and human-readable report ran successfully on Steam Deck against a mounted NAS (49 files).
- **Confirmed:** complete **118-test** suite passed on Steam Deck on 2026-11-23 (commit `0e0ea54`, 0.053 s).
- **Pending:** maintainer approval and PR #9 merge. Do not label the milestone merged before that happens.

## Safety decisions

- Save inventory, comparison, planning and preflight are read-only.
- `--setup` is an exception only for creating a **new**, explicitly confirmed configuration file; it never changes saves.
- `UNKNOWN` means insufficient evidence, **not** that Batocera is off.
- `STOPPED` means no RetroArch process was observed at one instant, **not** that NAS writes are safe.
- The platform preview compares exact filenames; identical SHA-256 values across different filenames are **not** proof of game identity.
- Save states are inventory-only; declared core identity does not establish compatibility.
- Experimental copy/recovery modules are restricted to disposable fixtures; never use on production saves.
- Other emulators, NAS clients, time-of-check/time-of-use races, locking and crash consistency remain open problems.

## v0.10 candidates (design discussion, not commitments)

1. **SRAM authority policy:** explicit per-platform `manual` (default), `prefer_local`, or `prefer_remote` for divergent files, with optional per-game overrides. Policy selection must not itself enable writes.
2. **Historical baseline:** distinguish a genuine two-sided conflict from an unchanged or missing file; never interpret one-sided presence as deletion without explicit history/policy.
3. **Safe-write prerequisites:** verified mount, all relevant writers quiescent, destination backup, integrity rechecks, atomicity/durability considerations and recovery.
4. **Discovery evolution:** persist platform mappings safely, support multiple platforms and eventually nested layouts with explicit adapters; assess core/state compatibility separately.
5. **SSH onboarding:** optional guided host-key verification and key enrollment without overwriting existing keys; never silently trust a host.

Do not enable production synchronization until its safety model and tests are complete. Keep the README status and CHANGELOG aligned with the latest merged milestone.
