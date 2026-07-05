# Project X 0.3.0-alpha — Release Notes

**Release:** 0.3.0-alpha  
**Date:** 2026-07-05  
**Milestone:** SAVE-050 — Project X 0.3 Alpha Release

No new features are included in this release. Changes are limited to stabilization,
documentation, version alignment, and removal of unused legacy code.

## Highlights since 0.2.0-rc1

### Vessel database (SAVE-032 → SAVE-035)

- SQLite vessel database with ShipRegistry synchronization
- Vessel Database viewer with advanced search, filters, and sorting

### Vessel enrichment (SAVE-036 → SAVE-040)

- Vessel photo framework with local and external provider stubs
- Photo display in vessel information card
- Vessel flag framework (250 SVG flags) integrated in vessel card

### Timeline (SAVE-041 → SAVE-044)

- Timeline framework with SQLite storage
- Automatic position update recording
- Arrival/departure detection engine
- Vessel Timeline viewer page

### Statistics (SAVE-045 → SAVE-046)

- Statistics framework with cached aggregates
- Statistics dashboard with summary cards and bar charts

### Alerts (SAVE-047 → SAVE-049)

- Alert rules engine (SQLite, thread-safe evaluation API)
- Alert Center (read-only viewer)
- Alert Rules Management Center (CRUD, test, enable/disable)

### Stabilization (SAVE-050)

- Removed legacy dashboard scaffold and unused dev scripts
- Resolved lint warnings in package `__init__` re-exports
- Version bumped to `0.3.0-alpha`
- Full compile, import, and startup verification
- Comprehensive documentation update

## Verified subsystems

| Subsystem | Status |
|-----------|--------|
| Dashboard | ✓ |
| Live Map | ✓ |
| Vessel List | ✓ |
| Vessel Database | ✓ |
| Vessel Timeline | ✓ |
| Statistics Dashboard | ✓ |
| Alert Center | ✓ |
| Alert Rules Management | ✓ |
| Camera Preview | ✓ |
| Camera Diagnostics | ✓ (module) |
| Playback Settings | ✓ (module) |
| Live Camera workflow | ✓ |
| Inspector | ✓ (headless) |

## Navigation (sidebar pages)

| Index | Page |
|-------|------|
| 0 | Dashboard |
| 1 | Live Map |
| 2 | Vessels |
| 3 | Cameras |
| 4 | Vessel Database |
| 5 | Vessel Timeline |
| 6 | Statistics |
| 7 | Alert Center |
| 8 | Alert Rules |

## Upgrade notes

- Version string is now `0.3.0-alpha` (was `0.2.0-rc1`)
- Legacy `gui/dashboard.py` scaffold and related unused panels removed
- Dev test scripts (`test_ais.py`, etc.) removed from `src/`
- No database migration required; SQLite databases auto-create on first use

## Known limitations

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for full subsystem status and Beta roadmap.

## Roadmap toward Beta

1. Wire camera packs into active camera loader
2. Automatic alert evaluation from monitoring events
3. Notification delivery
4. Settings and diagnostics in main navigation
5. Inspector GUI / CLI
6. Production playback backends beyond MPV
7. Configurable deployment paths
8. Automated test suite and packaging
