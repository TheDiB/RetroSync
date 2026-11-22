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
| [#8](https://github.com/TheDiB/RetroSync/pull/8) | v0.8 (draft) | Remote preflight and documentation |

## Safety decisions

- All inventory, decision, planning and preflight commands are read-only.
- `UNKNOWN` means evidence is insufficient, **not** that Batocera is off.
- `STOPPED` means no RetroArch process was observed at one instant, **not** that NAS writes are safe.
- Standalone emulators, other NAS clients, TOCTOU races, locks and crash consistency remain open problems.
- Experimental copy/recovery modules operate only on disposable fixtures; do not use on real saves.

## Next steps

1. Review and test v0.8 on Windows and Steam Deck, including remote RUNNING/STOPPED/UNKNOWN.
2. Plan an interactive `--setup` wizard for verified SSH trust, client keys, Batocera public-key authorization and per-game configuration; preserve existing keys and require authenticated initial access.
3. Design multi-writer coordination and robust recovery **before** enabling writes.

Keep `README.md` status aligned with the latest merged milestone and mark draft work explicitly.


## v0.9 (draft)

- Guided setup: dry run, explicit confirmation, new-file-only config creation.
- Later increments: SSH key enrollment with verified host identity, recovery/rollback, richer multi-game setup.
