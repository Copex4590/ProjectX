# Project X — Release Audit (SAVE-066)

Audit date: 2026-07-05  
Target: First Windows release (`0.3.0-alpha`)  
Scope: Packaging and release readiness only — no new features.

## Summary

Project X is **ready for a first Windows release candidate build** after the fixes in this audit. Core resources, runtime file handling, PyInstaller configuration, startup error handling, and offline map assets are in place.

---

## Ready

### Resources
- **Branding**: `projectx-logo.svg`, generated `projectx-logo.png`, `projectx.ico` present under `src/resources/branding/`
- **Translations**: `en.json` and `hu.json` (540+ keys each, in sync)
- **Map HTML**: `map.html`, `observation_map.html`, `camera_map.html` load via `app.paths.resource_path()`
- **Leaflet**: Bundled locally at `src/resources/map/leaflet/` (offline — no CDN dependency)
- **Flags**: SVG flag assets under `src/resources/flags/`
- **Camera packs / static camera config**: Bundled under `src/config/cameras/` and `src/config/camera_packs/`

### Runtime files
- User-writable files are **not required in Git** (`.gitignore` updated)
- Auto-created on first run:
  - `preferences.json`
  - `observation_points.json`
  - `cameras.json`
  - `ais_api_key.txt`
  - SQLite databases (`alerts.db`, `timeline.db`, `vessels.db`)
  - Logbook folder under user data / `data/Hajók/`
- **Frozen builds** store writable config under `%APPDATA%/Project X/config/` and data under `%APPDATA%/Project X/data/`

### Build readiness
- PyInstaller spec: `installer/projectx.spec`
  - Bundles `resources/` and read-only `config/` subsets only
  - `hiddenimports` for Qt WebEngine, WebChannel, openpyxl, websocket
  - Windowed mode with tracebacks disabled (`disable_windowed_traceback=True`)
- Build commands documented in `installer/README.md`
- Windows Inno Setup script: `installer/windows/projectx.iss`

### Settings & first run
- Default preferences created automatically when missing
- First-run wizard covers: Language → Observation Point → AIS → Camera (optional)
- RTL-SDR remains optional (Dashboard / System Health)

### Logging & errors
- Central logging via `app/logging_config.py` (WARNING by default; `PROJECTX_DEBUG=1` for verbose)
- Main window and AIS-Catcher launcher debug output moved to logging (not printed to console)
- EventBus handler failures logged, not printed
- Startup `sys.excepthook` shows friendly QMessageBox — no Python traceback to users
- `HybridEngine` console output unchanged (intentionally excluded from this audit)

### System Health
- Central diagnostics page aggregates subsystem status
- Diagnostic report export (`diagnostics.txt`) redacts API keys

---

## Needs Attention

| Item | Status | Action before release |
|------|--------|----------------------|
| **Windows test build** | Not run in CI | Run `pyinstaller installer/projectx.spec` on Windows and smoke-test the `.exe` |
| **Qt WebEngine runtime** | Hidden imports added | Verify map loads on a clean Windows VM; add PyInstaller hook if WebEngine process missing |
| **AIS-Catcher path** | Linux default in `aiscatcher.py` | Set `PROJECTX_AIS_CATCHER_EXECUTABLE` in Windows installer docs or user guide |
| **Branding assets in Git** | Generated PNG/ICO now present | Commit `projectx-logo.png`, `projectx.ico`, and Leaflet bundle with release |
| **Leaflet fetch script** | Added `scripts/fetch_leaflet.sh` | Re-run before release if Leaflet version changes |

---

## Optional Improvements

1. **PyInstaller Qt WebEngine hook** — Use `collect_all('PySide6.QtWebEngineWidgets')` if map fails on Windows until manual hook is verified.
2. **Code signing** — Sign `projectx.exe` and the Inno Setup installer for SmartScreen trust.
3. **macOS `.icns`** — Placeholder exists; generate real icon for future macOS bundle.
4. **HybridEngine console output** — Redirect to logging behind `PROJECTX_DEBUG` (requires separate change; excluded from SAVE-066 scope).
5. **Automatic Windows CI build** — GitHub Actions workflow for PyInstaller + Inno Setup on tag.
6. **User data migration** — Tool to import dev `src/config/*.json` into `%APPDATA%/Project X/config/` for testers upgrading from source builds.
7. **Offline tile cache** — Map tiles still load from OpenStreetMap CDN; bundle or cache tiles for fully offline operation.

---

## PyInstaller Data Files

| Source | Destination | Notes |
|--------|-------------|-------|
| `src/resources/` | `resources/` | Translations, maps, flags, branding, Leaflet |
| `src/config/cameras/` | `config/cameras/` | Static camera definitions |
| `src/config/camera_packs/` | `config/camera_packs/` | Country packs (read-only) |
| `src/config/playback.json` | `config/` | Playback defaults |
| `src/config/*.example` | `config/` | Reference only |
| `projectx.ico`, `projectx-logo.png` | `.` | Windows icon and splash |

**Not bundled:** runtime `data/` (DBs, logbooks, photos). Created in user data at first launch.

**Excluded from bundle** (created at runtime): `preferences.json`, `cameras.json`, `observation_points.json`, `ais_api_key.txt`, `camera_packs/state.json`, all SQLite databases

---

## Hidden Imports

```
PySide6.QtWebEngineWidgets
PySide6.QtWebEngineCore
PySide6.QtWebChannel
openpyxl
openpyxl.cell
openpyxl.workbook
websocket
websocket._abnf
websocket._core
```

---

## Pre-release Checklist

- [ ] `python3 scripts/generate_branding_assets.py`
- [ ] `scripts/fetch_leaflet.sh`
- [ ] `pip install -r requirements.txt pyinstaller`
- [ ] `pyinstaller installer/projectx.spec`
- [ ] Compile `installer/windows/projectx.iss`
- [ ] First launch on clean Windows: language wizard, map, AIS configure, System Health full check
- [ ] Confirm `%APPDATA%/Project X/config/` created and writable
- [ ] Confirm no console window or traceback on startup failure

---

## Files Changed in SAVE-066

- `src/app/paths.py` — unified dev/frozen path resolution
- `src/app/logging_config.py` — release logging defaults
- `src/app/application.py` — startup exception hook
- Map widgets, branding, i18n, flags — use `resource_path()`
- Preferences, observation, cameras, databases — use runtime user paths when frozen
- `installer/projectx.spec` — hiddenimports, selective config bundling
- `src/resources/map/leaflet/` — offline Leaflet bundle
- Map HTML — local Leaflet references
- `.gitignore` — runtime DB and state files
