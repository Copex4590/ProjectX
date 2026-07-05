# Changelog

All notable changes to Project X are documented in this file.

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

### Known issues (deferred to SAVE-031)

- Possible circular import between `CameraManager` and `engines.camera.diagnostics` — see [docs/TODO.md](TODO.md)

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
