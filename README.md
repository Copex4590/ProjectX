# Project X

Danube vessel monitoring platform with live map, camera selection, playback, and diagnostics.

**Version:** 0.2.0-rc1  
**Status:** Release Candidate 1

## Features (SAVE-008 through SAVE-030)

### Monitoring

- Hybrid AIS + RTL engine with ship registry
- Live map (Leaflet) with custom SVG ship markers
- Vessel information cards with full registry fields
- Dashboard with ship counts and connection status

### Cameras

- Camera Manager with JSON configuration per country
- Automatic camera selection by vessel position, FOV, and radius
- Camera Preview panel on the map page
- Official Hungary camera pack (placeholder streams)
- Camera Pack Manager (install, enable/disable packs)

### Playback

- Camera provider framework (HLS, RTSP, Snapshot, YouTube)
- Playback backend framework (MPV, VLC, Qt, Browser, Custom)
- Live Camera workflow: selection → provider → backend → session
- Playback Settings (automatic / user-preferred mode, backend selection)

### Diagnostics

- Camera Diagnostics Engine (configuration, playback, selection)
- Camera Diagnostics panel in Settings (summary, table, filters)
- Project X Inspector for headless system health reports

## Installation

### Linux

```bash
git clone https://github.com/Copex4590/ProjectX.git
cd ProjectX
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd src
python3 main.py
```

### Dependencies

| Package | Purpose |
|---------|---------|
| PySide6 | GUI (requires Qt WebEngine for map) |
| websocket-client | AIS stream client |

Optional: `mpv` or `vlc` on PATH for external video playback.

## Project structure

```
rtl-hajomonitor/
├── docs/
│   ├── CHANGELOG.md
│   ├── RELEASE_NOTES_0.2_RC1.md
│   └── TODO.md                 # Known issues (SAVE-031+)
├── requirements.txt
└── src/
    ├── main.py                 # Application entry point
    ├── app/                    # Qt application shell
    ├── gui/                    # Pages, panels, widgets
    │   └── settings/           # Playback Settings, Camera Diagnostics
    ├── engines/
    │   ├── ais/                # AIS stream engine
    │   ├── rtl/                # Hybrid RTL engine
    │   ├── camera/             # Selection, providers, diagnostics
    │   └── playback/           # Backend framework
    ├── cameras/                # Manager, loader, pack manager
    ├── models/                 # Ship, Camera
    ├── database/               # Ship and camera registries
    ├── playback/               # Preferences, live workflow
    ├── inspector/              # System health inspector
    ├── config/
    │   ├── cameras/            # Legacy camera config (active)
    │   ├── camera_packs/       # Pack manifests (manager only)
    │   └── playback.json       # Playback preferences
    └── resources/
        ├── map/                # Leaflet map HTML
        └── icons/              # Ship SVG marker
```

## Configuration

| Path | Description |
|------|-------------|
| `src/config/cameras/index.json` | Legacy camera index (active loader) |
| `src/config/camera_packs/` | Installed camera packs |
| `src/config/camera_packs/state.json` | Enabled/disabled pack state |
| `src/config/playback.json` | Playback mode and backend preferences |

Environment overrides:

- `PROJECTX_CAMERAS_CONFIG_DIR`
- `PROJECTX_CAMERA_PACKS_DIR`
- `PROJECTX_PLAYBACK_PREFERENCES_FILE`

## Current limitations

- **SAVE-031:** Possible circular import between `CameraManager` and `engines.camera.diagnostics` — see [docs/TODO.md](docs/TODO.md)
- Camera packs are managed but not yet loaded into the active camera registry
- Hungary pack uses placeholder stream URLs
- Inspector is available programmatically, not in the GUI
- Settings pages live in the dashboard settings scaffold
- MPV is the only production playback backend; others are stubs
- Hybrid Engine paths are hardcoded for the original deployment environment

## Roadmap to 0.3

1. Fix circular import (SAVE-031)
2. Wire camera packs into CameraLoader
3. Real camera stream integration
4. Settings in main navigation
5. Inspector GUI / CLI tool
6. Production playback backends (VLC, Qt, Browser)
7. Configurable deployment paths and automated tests

## Documentation

- [CHANGELOG](docs/CHANGELOG.md)
- [Release Notes 0.2 RC1](docs/RELEASE_NOTES_0.2_RC1.md)
- [TODO / known issues](docs/TODO.md)

## License

See repository for license information.
