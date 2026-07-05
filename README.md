# Project X

![Project X](src/resources/branding/projectx-logo.svg)

Danube vessel monitoring platform with live AIS map, camera selection, playback, vessel database, timeline, statistics, and alert management.

**Version:** 0.3.0-alpha  
**Status:** Alpha release

## Architecture overview

Project X is a PySide6 desktop application organized into layered subsystems:

```
┌─────────────────────────────────────────────────────────────┐
│  GUI (pages, panels, widgets)                               │
├─────────────────────────────────────────────────────────────┤
│  Application services (statistics, timeline, alerts, etc.)  │
├─────────────────────────────────────────────────────────────┤
│  Engines (AIS, RTL hybrid, camera, playback, timeline)      │
├─────────────────────────────────────────────────────────────┤
│  Registries & persistence (ships, cameras, vessels, SQLite) │
└─────────────────────────────────────────────────────────────┘
```

- **Monitoring path:** Hybrid RTL Engine → ShipRegistry → EventBridge → GUI pages
- **Camera path:** CameraManager → Selection Engine → Provider → Playback backend
- **Timeline path:** ShipRegistry hooks → TimelineRecorder / ArrivalDepartureEngine → SQLite
- **Alert path:** AlertManager rule evaluation → SQLite events → Alert Center GUI
- **Inspector:** Headless health report across cameras, playback, and registries

Data flows are read-only at the GUI layer except for rule management and playback preferences.

## Features (SAVE-001 → SAVE-050)

### Monitoring & map

- Hybrid AIS + RTL engine with ship registry
- Live Leaflet map with custom SVG ship markers
- Vessel information card with photos and flags
- Dashboard with ship counts and connection status

### Vessel database & timeline

- SQLite vessel database with ShipRegistry synchronization
- Advanced vessel search, filters, and sorting
- Automatic timeline recording (position updates)
- Arrival/departure detection engine
- Vessel timeline viewer

### Statistics & alerts

- Cached vessel statistics framework
- Statistics dashboard with summary cards and charts
- Alert rules engine (SQLite, thread-safe evaluation API)
- Alert Center (read-only alert viewer)
- Alert Rules Management Center (CRUD, test, enable/disable)

### Cameras & playback

- Camera Manager with JSON configuration per country
- Automatic camera selection by vessel position, FOV, and radius
- Camera preview panel on the map page
- Official Hungary camera pack (placeholder streams)
- Camera Pack Manager (install, enable/disable packs)
- Camera provider framework (HLS, RTSP, Snapshot, YouTube)
- Playback backend framework (MPV, VLC, Qt, Browser, Custom)
- Live Camera workflow: selection → provider → backend → session
- Playback Settings (automatic / user-preferred mode, backend selection)

### Diagnostics

- Camera Diagnostics Engine (configuration, playback, selection)
- Camera Diagnostics panel (module available; not in main sidebar)
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

### Windows

```powershell
git clone https://github.com/Copex4590/ProjectX.git
cd ProjectX
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd src
python main.py
```

Requires Qt WebEngine (included with PySide6). For external playback, install `mpv` or `vlc` and ensure they are on PATH.

### Desktop installer (Linux)

```bash
chmod +x installer/linux/install.sh
installer/linux/install.sh --launch
```

Installs Project X to `~/.local/share/projectx`, creates a desktop shortcut, and adds an applications menu entry with the official icon.

See [installer/README.md](installer/README.md) for Windows packaging and build metadata.

### macOS

```bash
git clone https://github.com/Copex4590/ProjectX.git
cd ProjectX
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd src
python3 main.py
```

Install `mpv` via Homebrew for external video playback: `brew install mpv`.

### Dependencies

| Package | Purpose |
|---------|---------|
| PySide6 | GUI (requires Qt WebEngine for map) |
| websocket-client | AIS stream client |

Optional: `mpv` or `vlc` on PATH for external video playback.

## Folder structure

```
rtl-hajomonitor/
├── docs/
│   ├── CHANGELOG.md
│   ├── PROJECT_STATUS.md
│   ├── RELEASE_NOTES_0.3_ALPHA.md
│   └── TODO.md
├── requirements.txt
└── src/
    ├── main.py                 # Application entry point
    ├── app/                    # Qt application shell
    ├── gui/                    # Pages, panels, widgets
    │   ├── settings/           # Playback Settings, Camera Diagnostics
    │   └── widgets/            # MapWidget, CameraPreviewPanel
    ├── alerts/                 # Alert rules engine (SQLite)
    ├── timeline/               # Timeline recording & storage
    ├── statistics/             # Cached statistics
    ├── vessels/                # Photos, flags, providers
    ├── engines/
    │   ├── ais/                # AIS stream engine
    │   ├── rtl/                # Hybrid RTL engine
    │   ├── camera/             # Selection, providers, diagnostics
    │   ├── playback/           # Backend framework
    │   └── timeline/           # Arrival/departure detection
    ├── cameras/                # Manager, loader, pack manager
    ├── models/                 # Ship, Camera, VesselRecord
    ├── database/               # Ship, camera, vessel registries
    ├── playback/               # Preferences, live workflow
    ├── inspector/              # System health inspector
    ├── config/
    │   ├── cameras/            # Legacy camera config (active loader)
    │   ├── camera_packs/       # Pack manifests
    │   └── playback.json       # Playback preferences
    └── resources/
        ├── branding/           # Official Project X logo (SVG, PNG, ICO)
        ├── map/                # Leaflet map HTML
        ├── icons/              # Ship SVG marker
        └── flags/              # Vessel flag SVGs (250 countries)
```

## Configuration

| Path | Description |
|------|-------------|
| `src/config/cameras/index.json` | Legacy camera index (active loader) |
| `src/config/camera_packs/` | Installed camera packs |
| `src/config/camera_packs/state.json` | Enabled/disabled pack state |
| `src/config/playback.json` | Playback mode and backend preferences |
| `src/config/*.json.example` | Runtime config templates (copied on first run) |
| `src/database/vessels.db` | Vessel database (auto-created) |
| `src/timeline/timeline.db` | Vessel timeline events (auto-created) |
| `src/alerts/alerts.db` | Alert rules and events (auto-created) |

Environment overrides:

| Variable | Purpose |
|----------|---------|
| `PROJECTX_CAMERAS_CONFIG_DIR` | Camera config directory |
| `PROJECTX_CAMERA_PACKS_DIR` | Camera packs directory |
| `PROJECTX_PLAYBACK_PREFERENCES_FILE` | Playback preferences file |
| `PROJECTX_VESSEL_DATABASE_FILE` | Vessel database path |
| `PROJECTX_TIMELINE_DATABASE_FILE` | Timeline database path |
| `PROJECTX_ALERT_DATABASE_FILE` | Alert database path |

## Camera packs

Camera packs are versioned bundles under `src/config/camera_packs/`. Each pack contains:

- `manifest.json` — name, version, author, country, description
- Regional JSON files — camera definitions per area

The **Hungary** pack (`hungary/`) ships with placeholder stream URLs. The Pack Manager can install and enable/disable packs; the active camera loader still uses the legacy `config/cameras/` index.

## Playback system

1. **Preferences** (`config/playback.json`) — automatic or user-preferred mode, backend choice
2. **Provider** — resolves stream URL from camera metadata (HLS primary)
3. **Backend** — launches external player (MPV production-ready; VLC/Qt/Browser stubs)
4. **Live Camera workflow** — ties selection, provider, and backend into a session

## Timeline system

- **TimelineRecorder** — async, deduplicated `POSITION_UPDATE` events from ShipRegistry
- **ArrivalDepartureEngine** — detects `ARRIVAL` / `DEPARTURE` after configurable absence timeout
- **TimelineManager** — SQLite persistence and query API
- **Vessel Timeline page** — read-only viewer with search and filters

## Statistics

- **StatisticsManager** — cached read-only aggregates from VesselDatabase and TimelineManager
- **Statistics Dashboard** — summary cards, top lists, hourly bar charts

## Alert engine

- **AlertManager** — thread-safe rule registration and evaluation API
- **Rule types:** ARRIVAL, DEPARTURE, SPEED_OVER, ENTER_REGION, EXIT_REGION, CAMERA_VISIBLE, CAMERA_LOST
- **Alert Center** — read-only alert viewer with filters
- **Rules page** — full rule CRUD, test, enable/disable
- Automatic alert execution from monitoring is not yet wired (evaluation API only)

## Supported platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux | Primary | Tested target; AIS-catcher integration |
| Windows | Supported | PySide6 + WebEngine; paths may need adjustment |
| macOS | Supported | PySide6 + WebEngine; install mpv via Homebrew |

## Current limitations

- Camera packs are managed but not yet loaded into the active camera registry
- Hungary pack uses placeholder stream URLs
- Alert engine has no automatic monitoring hooks or notifications yet
- Playback Settings and Camera Diagnostics are module-ready but not in the main sidebar
- Inspector is available programmatically, not in the GUI
- MPV is the only production playback backend; others are stubs
- Hybrid Engine paths are hardcoded for the original deployment environment
- Menu bar actions (File/View/Tools) are placeholders

## Roadmap toward Beta

1. Wire camera packs into CameraLoader
2. Real camera stream integration
3. Automatic alert evaluation from timeline and monitoring events
4. Notification delivery (desktop, sound, tray)
5. Settings and diagnostics in main navigation
6. Inspector GUI / CLI tool
7. Production playback backends (VLC, Qt, Browser)
8. Configurable deployment paths and automated test suite
9. Cross-platform packaging (AppImage, installer) — **Linux installer available** (`installer/linux/`)

## Branding

Official Project X artwork lives in `src/resources/branding/`:

- `projectx-logo.svg` — master vector logo (two ship bows forming an X)
- `projectx-logo.png` — application, splash, and About dialog
- `projectx.ico` — Windows / installer icon
- `projectx.icns` — macOS bundle icon (future)

Regenerate raster assets:

```bash
python3 scripts/generate_branding_assets.py
```

## Documentation

- [CHANGELOG](docs/CHANGELOG.md)
- [Release Notes 0.3 Alpha](docs/RELEASE_NOTES_0.3_ALPHA.md)
- [Project Status](docs/PROJECT_STATUS.md)
- [TODO / known issues](docs/TODO.md)

## License

MIT License — see [LICENSE](LICENSE).
