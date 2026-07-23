# Changelog

All notable changes to Project X are documented in this file.

## [0.3.1-alpha.1] — 2026-07-23

First Public Test release (SAVE-205 finalization). Stabilization track SAVE-200…SAVE-205. No new product features in this tag beyond release engineering.

### Added

- Release notes for `0.3.1-alpha.1`
- Release candidate and finalization reports (`docs/reports/release_candidate.md`, `release_final.md`)
- First public test checklist
- **SAVE-208** — Vessel Database Manager page (sidebar): local DB info, sync controls, session statistics, diagnostics, and maintenance actions (UI + backend hooks)
- **SAVE-209** — Automatic vessel database synchronization (scheduler, persisted last/next sync, EventBus, online provider hook)
- **SAVE-210** — Backup & Restore Manager (full/database/settings backup, list, restore, delete)
- **SAVE-211** — Application Settings Manager (General, AIS, Cameras, Database, Notifications, Advanced)
- **SAVE-212** — Plugin Framework and Installed Plugins page (enable/disable, metadata, dependencies)
- **SAVE-213** — Vessel Details Panel 2.0 (map side panel: overview, position, voyage, live status, camera, database)
- **SAVE-214** — Vessel Timeline & Playback (Play/Pause, speed, scrubber, trail, Live mode)

### Changed

- Application version unified to `0.3.1-alpha.1` (`src/version.py`, manifests, installer script, About, window title)
- File → Exit wired; File → New Profile disabled as Coming Soon
- HybridEngine async filesystem writer; SQLite WAL + batched writes; incremental map/radar (SAVE-203)
- Critical runtime hardening (SAVE-202)

### Known issues

- Windows `ProjectX-Setup.exe` requires a native Windows build before publish
- Rebuild Linux `.deb` / AppImage from this version so package metadata matches `0.3.1-alpha.1`
- Future AIS providers (MarineTraffic, AISHub) not activatable
- See `docs/reports/release_final.md`

---

## [0.3.0-alpha] — 2026-07-05

Project X 0.3 Alpha release (SAVE-050). Stabilization and documentation pass. No new features.

### Added

- **SAVE-032** — Vessel Database Framework (`src/database/vessel_database.py`)
- **SAVE-033** — ShipRegistry vessel database synchronization
- **SAVE-034** — Vessel Database Viewer (`src/gui/vesseldatabasepage.py`)
- **SAVE-035** — Advanced vessel search and filters
- **SAVE-036** — Vessel Photo Framework (`src/vessels/`)
- **SAVE-037** — Vessel Photo Provider Framework
- **SAVE-038** — Vessel photo integration in vessel card
- **SAVE-039** — Vessel Flag Framework (`src/vessels/flags/`, 250 SVG flags)
- **SAVE-040** — Vessel flag integration in vessel card
- **SAVE-041** — Vessel Timeline Framework (`src/timeline/`)
- **SAVE-042** — Automatic timeline recording
- **SAVE-043** — Arrival/departure detection engine
- **SAVE-044** — Vessel Timeline Viewer (`src/gui/vesseltimelinepage.py`)
- **SAVE-045** — Vessel Statistics Framework (`src/statistics/`)
- **SAVE-046** — Statistics Dashboard (`src/gui/statisticspage.py`)
- **SAVE-047** — Alert Rules Engine (`src/alerts/`)
- **SAVE-048** — Alert Center (`src/gui/alertcenterpage.py`)
- **SAVE-049** — Alert Rules Management Center (`src/gui/rulespage.py`)
- **SAVE-050** — 0.3 Alpha release documentation (`docs/PROJECT_STATUS.md`, `docs/RELEASE_NOTES_0.3_ALPHA.md`)

### Changed

- Application version bumped to `0.3.0-alpha`
- Main window title displays version from `PROJECT_VERSION`
- Removed legacy dashboard scaffold and unused dev scripts
- Resolved package `__init__` lint warnings with explicit `__all__` exports

### Removed

- Legacy `gui/dashboard.py` scaffold and dependent unused panels
- Dev test scripts (`test_ais.py`, `test_engine.py`, `test_parser.py`, `test_live_ais.py`)

---

## [0.2.0-rc1] — 2026-07-05

Release candidate 1. Stabilization and documentation pass (SAVE-030). No new features.

### Added

- **SAVE-026** — Official Hungary Camera Pack (`src/config/camera_packs/hungary/`)
- **SAVE-025** — Project X Inspector (`src/inspector/`)
- **SAVE-027** — Camera Pack Manager (`src/cameras/pack_manager.py`)
- **SAVE-028** — Playback Settings page (`src/gui/settings/playbacksettings.py`)
- **SAVE-029** — Camera Diagnostics panel (`src/gui/settings/cameradiagnosticspanel.py`)
- **SAVE-030** — RC1 documentation (`docs/`, `README.md`, `requirements.txt`)

### Changed

- Application version bumped to `0.2.0-rc1`
- Removed unused imports and dead code in loader, pack manager, and settings panels
- Settings panel integrates Playback Settings and Camera Diagnostics

### Known issues (deferred to Beta)

- Camera packs managed but not loaded into active camera registry
- Alert engine has no automatic monitoring hooks or notifications
- Settings and diagnostics modules not in main navigation
- Inspector available programmatically only

---

## [0.1.0-alpha] — Pre-0.2 development

### Map & Vessels

- **SAVE-002** — Map communication layer
- **SAVE-003** — MapWidget update interface
- **SAVE-004** — Ship interpolation foundation
- **SAVE-005** — Registry interpolation support
- **SAVE-006** — Faster map refresh (5 FPS)
- **SAVE-007** — Vessel information popup
- **SAVE-008** — Custom ship SVG map marker
- **SAVE-009** — Hybrid migration checkpoint
- **SAVE-010** — Hybrid Engine integrated startup
- **SAVE-011** — Professional Vessel Information Card
- **SAVE-012** — Complete Vessel Card data pipeline

### Cameras

- **SAVE-013** — Camera Manager framework
- **SAVE-014** — Automatic Camera Selection Engine
- **SAVE-015** — Camera Preview Panel integration
- **SAVE-016** — Camera Provider Framework
- **SAVE-017** — Production-ready HLS Provider
- **SAVE-023** — Camera metadata extension (playback/location fields)

### Playback

- **SAVE-018** — Playback Backend Framework
- **SAVE-019** — Playback Preferences
- **SAVE-020** — MPV launch configuration
- **SAVE-021** — First Live Camera workflow

### Diagnostics & health

- **SAVE-024** — Camera Diagnostics & Health Engine
