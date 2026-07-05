# Project X 0.2.0-rc1 — Release Notes

**Release candidate:** 0.2.0-rc1  
**Date:** 2026-07-05  
**Branch:** `feature/save-008-svg-icons`

## Overview

Project X 0.2 RC1 is the first release candidate for the camera monitoring platform.
This build completes the camera, playback, diagnostics, and settings stack introduced
in SAVE-011 through SAVE-029, with a stabilization pass in SAVE-030.

No new features are included in RC1. Changes are limited to cleanup, version alignment,
and documentation.

## What's included

### Live monitoring

- Hybrid AIS + RTL engine with automatic startup
- Live map with custom ship markers and vessel information cards
- Ship registry with interpolation support

### Camera system

- Camera Manager with country-based JSON configuration
- Automatic camera selection by vessel position
- Camera Preview panel on the map page
- Official Hungary camera pack (9 placeholder cameras, 3 regions)
- Camera Pack Manager (discover, enable/disable packs)

### Playback

- Provider framework (HLS, RTSP, Snapshot, YouTube)
- Backend framework (MPV, VLC, Qt, Browser, Custom)
- Live Camera workflow (selection → provider → playback)
- Playback Settings page (mode, preferred backend, custom executable)

### Diagnostics & inspection

- Camera Diagnostics Engine (configuration, playback, selection checks)
- Camera Diagnostics panel in Settings (summary, table, filter, refresh)
- Project X Inspector (headless system health report)

## Installation (Linux)

### Requirements

- Python 3.10+
- PySide6 with Qt WebEngine
- `websocket-client`
- Optional: `mpv` or `vlc` on PATH for external playback

### Setup

```bash
git clone https://github.com/Copex4590/ProjectX.git rtl-hajomonitor
cd rtl-hajomonitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
cd src
python3 main.py
```

The application expects local AIS/RTL infrastructure (AIS-catcher, API keys) as
configured in the Hybrid Engine. See [Current limitations](#current-limitations).

## Verification (SAVE-030)

The following areas were reviewed for RC1:

| Area | Status | Notes |
|------|--------|-------|
| Settings — Playback Settings | OK | Loads preferences; saves to `src/config/playback.json` |
| Settings — Camera Diagnostics | OK | UI loads; refresh uses `CameraDiagnosticsEngine` |
| Camera Pack Manager | OK | Discovers Hungary pack (`hungary-official`, 9 cameras) |
| Camera loading (legacy config) | OK | `src/config/cameras/` loads via CameraManager |
| Live Camera workflow | OK | Pipeline present; requires stream URLs and MPV for live play |
| Inspector | OK | `get_system_report()` available; not wired to GUI |
| Linux startup | Partial | GUI requires PySide6; import chain issue noted below |
| Python compile | OK | `python3 -m compileall src` passes |

## Known issues

### SAVE-031 — Circular import (CameraManager ↔ Diagnostics)

Importing `engines.camera.diagnostics` after `cameras` may hang depending on import
order. This affects cold-start import chains and automated verification.

**Tracked in:** [docs/TODO.md](TODO.md)  
**Fix planned:** SAVE-031

### Other limitations

- Camera packs are **not yet wired** into `CameraLoader`; legacy `src/config/cameras/` is still used
- Hungary pack URLs are placeholders (`placeholder.projectx.local`)
- Inspector is not exposed in the GUI
- Settings panel is embedded in the dashboard scaffold, not the main sidebar navigation
- Quick Settings placeholders in Settings have no handlers
- MPV backend launches external processes; VLC/Qt/Browser backends are architecture stubs
- Hybrid Engine uses hardcoded local paths for AIS/RTL data

## Stabilization changes (SAVE-030)

- Removed unused `CAMERAS_INDEX_FILE` import from camera loader
- Removed unused `_FILTER_LABELS` constant from diagnostics panel
- Removed no-op region camera counting in pack manager
- Bumped version strings to `0.2.0-rc1`
- Added `requirements.txt`

## Roadmap to 0.3

1. **SAVE-031** — Resolve circular import (CameraManager ↔ Diagnostics)
2. Wire Camera Pack Manager into CameraLoader
3. Replace placeholder stream URLs with real sources
4. Add Settings to main navigation (sidebar)
5. Expose Inspector in GUI or CLI
6. Complete VLC/Qt/Browser playback backends
7. Production hardening (configurable paths, error recovery, tests)

## Upgrade from 0.1.0-alpha

- Version strings updated in `main.py`, `application.py`, and `inspector.py`
- New config files: `src/config/playback.json`, `src/config/camera_packs/state.json`
- No database migrations required
