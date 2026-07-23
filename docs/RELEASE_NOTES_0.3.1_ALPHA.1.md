# Project X 0.3.1-alpha.1 — Full Release Notes

**Release:** 0.3.1-alpha.1  
**Channel:** First Public Test Release  
**Date:** 2026-07-23

Extended notes for testers and maintainers. Short form: `release/notes/0.3.1-alpha.1.md`.

## Stabilization track

| SAVE | Focus |
|------|--------|
| SAVE-200 | Baseline before performance / release initiative |
| SAVE-201 | Stabilization audit + readiness docs |
| SAVE-202 | Critical fixes (paths, I/O timeouts, joins, logbook, logging, QThreads) |
| SAVE-203 | High priority (FS writer queue, SQLite WAL/batch, map/radar incremental, provider isolation) |
| SAVE-204 | Release candidate audit |
| SAVE-205 | Release finalization (version identity, docs, menus, packaging metadata) |

## Installation methods

See README and `docs/LINUX_INSTALLER.md` / `docs/WINDOWS_INSTALLER.md`.

## Application data locations

| Mode | Data root |
|------|-----------|
| Linux installed / AppImage (frozen) | `~/.local/share/projectx/` |
| Windows installed (frozen) | `%APPDATA%\Project X\` |
| Development (source) | `<repo>/data/` |

## Known issues

See short release notes and `docs/reports/release_final.md`.

## License

MIT License — see `LICENSE`.
