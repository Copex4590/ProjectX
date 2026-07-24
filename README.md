# Project X

![Project X](src/resources/branding/projectx-logo.svg)

Danube / maritime vessel monitoring desktop platform: live AIS map, cameras, playback, vessel database, timeline, analytics, alerts, plugins, session recording, and backup.

**Version:** 0.3.1-beta  
**Status:** Beta

### Known issues (beta)

- Windows installer is prepared in-repo; `ProjectX-Setup.exe` must be built on Windows before publish.
- Rebuild Linux `.deb` / AppImage from this tag so embedded package metadata matches `0.3.1-beta`.
- MarineTraffic / AISHub and File → New Profile are Coming Soon (not activatable).
- Full list: [release notes](docs/RELEASE_NOTES_v0.3.1-beta.md) and [BETA_READY](docs/reports/BETA_READY.md).

## Project overview

Project X is a **PySide6** desktop application for professional vessel monitoring. It combines hybrid AIS + RTL sources, an interactive Leaflet map, camera selection / playback, SQLite vessel and timeline storage, a professional alerts engine, analytics charts, a plugin framework, and session recording/replay.

## Main features

| Area | Capabilities |
|------|----------------|
| **Monitoring & map** | Hybrid AIS + RTL engine, live Leaflet map, ship markers, vessel details panel, dashboard |
| **Vessel database** | SQLite vessel DB, search/filters, Database Manager, automatic sync scheduler |
| **Timeline** | Position recording, arrival/departure detection, timeline viewer, vessel playback trail |
| **Cameras** | Camera manager, selection / scoring, Camera Link (AIS-aware), preview, packs |
| **Alerts** | Professional Alerts Engine, Alert Center (ack/clear/export), rules management |
| **Analytics** | Live charts, interval filter, CSV / PNG / PDF export |
| **Session recording** | Record/replay `.pxsession` sessions (map, alerts, camera link) |
| **Plugins** | Discover / enable / disable installed plugins |
| **Settings & backup** | Application Settings Manager, Backup & Restore |
| **Diagnostics** | System Health, inspector APIs, camera diagnostics modules |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GUI (sidebar pages, panels, widgets)                       │
├─────────────────────────────────────────────────────────────┤
│  Application services (alerts, analytics, session, plugins) │
├─────────────────────────────────────────────────────────────┤
│  Engines (AIS, RTL hybrid, camera, playback, timeline)      │
├─────────────────────────────────────────────────────────────┤
│  Registries & persistence (ships, cameras, vessels, SQLite) │
│  EventBus · Preferences · Paths (user data dirs)            │
└─────────────────────────────────────────────────────────────┘
```

- **Monitoring:** Hybrid RTL Engine → ShipRegistry → EventBridge → GUI  
- **Camera:** CameraManager → scoring / selection → provider → playback backend  
- **Timeline:** ShipRegistry hooks → TimelineRecorder / ArrivalDepartureEngine → SQLite  
- **Alerts:** Professional Alerts Engine → EventBus → Alert Center  
- **Session:** SessionRecorder / SessionPlayer → `.pxsession` → map / alerts / camera replay  

Version identity: `src/version.py` (`PROJECT_VERSION`).

## Installation

### Linux (official release)

**Recommended — Debian package:**

```bash
sudo dpkg -i ProjectX.deb
sudo apt-get install -f
```

Launch **Project X** from the applications menu. Uninstall via Software Manager or `sudo dpkg -r projectx`.

**Portable AppImage:**

```bash
chmod +x ProjectX.AppImage
./ProjectX.AppImage
```

Optional: verify with `SHA256SUMS`. Details: [docs/LINUX_INSTALLER.md](docs/LINUX_INSTALLER.md).

### Windows (official release)

Download `ProjectX-Setup.exe` from the Project X website or GitHub Releases. Install, then launch from Start Menu. Uninstall from Apps & features. Details: [docs/WINDOWS_INSTALLER.md](docs/WINDOWS_INSTALLER.md).

> The installer script (`installer/windows/projectx.iss`) is versioned to `0.3.1-beta`; the binary is built on native Windows.

### Development (from source)

**Linux / macOS:**

```bash
git clone https://github.com/Copex4590/ProjectX.git
cd ProjectX
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd src
PYTHONPATH=. python3 main.py
```

**Windows:**

```powershell
git clone https://github.com/Copex4590/ProjectX.git
cd ProjectX
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd src
python main.py
```

Requires Qt WebEngine (via PySide6). Optional: `mpv` or `vlc` on `PATH` for external playback.

### Dependencies

| Package | Purpose |
|---------|---------|
| PySide6 | GUI (Qt WebEngine for map) |
| websocket-client | AIS stream client |

## Plugin Framework

- Plugins live under the user/repo `plugins/` tree (`plugin.json` + `plugin.py`).
- Core APIs: `src/plugins/` (loader, registry, manager, metadata, versioning).
- **Installed Plugins** sidebar page: list, enable/disable, metadata, dependencies.
- Sample plugin: `plugins/sample_info/`.

## Session Recording

- Record live AIS sessions to compressed **`.pxsession`** files.
- Captures ship positions, camera link changes, alerts, playback, and timeline events.
- **Session Recording** page: list, info, delete, import/export, Play / Pause / Seek / speed.
- Replay drives map, Vessel Details, Alert Center, and Camera Link together; live map updates pause during replay.

## Analytics

- **Analytics** dashboard: live charts with interval filter.
- Export: CSV, PNG, PDF.
- Uses ThemeColors and EventBus; timers stop on page shutdown / window close.

## Camera AI (Intelligent Camera & AIS Link)

- Scoring engine ranks cameras for the selected vessel (FOV, distance, coverage).
- Auto-switch thresholds and coverage zones on the map.
- **Camera Link** panel on the map page for AIS-linked camera selection.

## Alerts

- **Professional Alerts Engine** with live detectors.
- **Alert Center**: active/history, acknowledge, clear, export.
- **Alert Rules** page: rule CRUD, test, enable/disable.
- Rule types include arrival/departure, speed, region enter/exit, camera visible/lost.

## Backup

- **Backup & Restore** page: full / database / settings backups.
- List, restore, and delete backups under the user data tree (`backups_dir`).

## Database

- SQLite vessel database with ShipRegistry synchronization.
- **Vessel Database** viewer (search/filters) and **Database Manager** (info, sync, diagnostics, maintenance).
- Automatic sync scheduler with persisted last/next sync and EventBus events.
- Timeline and alerts use separate SQLite stores under user data paths.

## Sidebar pages (16)

Dashboard · Map · Vessels · Cameras · Vessel Database · Vessel Timeline · Statistics · Alert Center · Alert Rules · System Health · Database Manager · Backup & Restore · Settings · Installed Plugins · Analytics · Session Recording

## Folder structure (high level)

```
ProjectX/
├── docs/                 # Changelog, roadmap, release notes, reports
├── installer/            # PyInstaller spec, Windows Inno, Linux desktop/deb
├── plugins/              # Installed / sample plugins
├── release/              # Packaged artifacts + manifest + notes
├── scripts/              # Build / verify / prepare release
├── src/                  # Application source (PYTHONPATH root)
│   ├── version.py
│   ├── app/ gui/ engines/ alerts/ analytics/ session/ plugins/
│   ├── database/ timeline/ statistics/ vessels/ cameras/
│   └── resources/ config/
└── website/              # Download mirrors + releases.json
```

## Configuration & data

Bundled (read-only) samples live under `src/config/`. Writable runtime data (DBs, logbooks, photos, sessions, backups) use `app.paths` user-data directories — the repo `data/` tree is development-only and must not be bundled.

| Variable | Purpose |
|----------|---------|
| `PROJECTX_CAMERAS_CONFIG_DIR` | Camera config directory |
| `PROJECTX_CAMERA_PACKS_DIR` | Camera packs directory |
| `PROJECTX_PLAYBACK_PREFERENCES_FILE` | Playback preferences file |
| `PROJECTX_VESSEL_DATABASE_FILE` | Vessel database path |
| `PROJECTX_TIMELINE_DATABASE_FILE` | Timeline database path |
| `PROJECTX_ALERT_DATABASE_FILE` | Alert database path |

## Supported platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux | Primary | `.deb` + AppImage packaging |
| Windows | Supported | Inno Setup installer (native build) |
| macOS | Dev from source | PySide6 + WebEngine; `brew install mpv` optional |

## Documentation

- [CHANGELOG](docs/CHANGELOG.md)
- [ROADMAP](docs/ROADMAP.md)
- [Release Notes 0.3.1-beta](docs/RELEASE_NOTES_v0.3.1-beta.md)
- [Beta readiness](docs/reports/BETA_READY.md)
- [Linux installer](docs/LINUX_INSTALLER.md)
- [Windows installer](docs/WINDOWS_INSTALLER.md)
- [Project Status](docs/PROJECT_STATUS.md)
- [TODO](docs/TODO.md)

## License

MIT License — see [LICENSE](LICENSE).
