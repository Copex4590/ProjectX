# Project X — Windows Build Pipeline (SAVE-067)

This document describes how to produce a native Windows release of Project X from a Linux development environment. No application features are involved — only build and packaging.

---

## 1. Build requirements audit

### Application stack

| Component | Version / notes |
|-----------|-----------------|
| Python | 3.10+ recommended |
| PySide6 | GUI + **Qt WebEngine** (maps) |
| websocket-client | AIS WebSocket client |
| openpyxl | Logbook / export |
| PyInstaller | 6.x (bundling) |
| Inno Setup | 6.x (Windows installer, optional) |

### Bundled runtime assets (must be present before build)

| Asset | Location |
|-------|----------|
| Leaflet (offline maps) | `src/resources/map/leaflet/` |
| Translations | `src/resources/translations/en.json`, `hu.json` |
| Map HTML / JS / CSS | `src/resources/map/*.html`, `leaflet/` |
| Flags, icons, logos | `src/resources/flags/`, `icons/`, `branding/` |
| Read-only config | `src/config/cameras/`, `camera_packs/`, `playback.json`, `*.example` |
| Seed data | `data/` |

Prepare assets automatically:

```bash
chmod +x scripts/fetch_leaflet.sh scripts/build_windows.sh scripts/build_linux.sh scripts/clean_build.sh
./scripts/build_windows.sh --prepare-only
```

### Can Windows binaries be built from Linux?

**Not with Linux Python alone.** PyInstaller, Nuitka, and cx_Freeze all target the host OS they run on. A Linux-hosted Python toolchain produces Linux binaries only.

Practical options from a Linux workstation:

| Method | Works for Project X? |
|--------|----------------------|
| **WSL + Windows Python** | Yes — recommended when the dev PC dual-boots or runs Windows |
| **Windows VM / physical Windows** | Yes — run `scripts/build_windows.sh` in Git Bash |
| **`PROJECTX_WINDOWS_PYTHON` pointing at `python.exe`** | Yes — from WSL or a mounted Windows drive |
| **Pure Linux Python → Windows .exe** | No — not supported reliably |
| **Wine + Windows Python** | Not recommended (Qt WebEngine breaks easily) |

The repository scripts automate asset prep, path checks, dependency install, and PyInstaller invocation once a **Windows Python** interpreter is available.

---

## 2. Build strategy

### Options evaluated

| Tool | PySide6 + Qt WebEngine | Cross-compile Linux → Windows | Maturity in this repo |
|------|------------------------|-------------------------------|------------------------|
| **PyInstaller** | Good; `collect_all` hooks for WebEngine | No (needs Windows Python) | **Already integrated** (SAVE-066) |
| **Nuitka** | Possible but complex; long compile; WebEngine plugin setup | Limited / experimental | Not configured |
| **cx_Freeze** | Weaker PySide6/WebEngine docs and hooks | No | Not configured |

### Recommendation: **PyInstaller**

Reasons:

1. **Already in use** — `installer/projectx.spec` bundles resources, config, Qt WebEngine, and branding.
2. **Best fit for Qt WebEngine** — `collect_all('PySide6.QtWebEngineCore')` pulls process helpers and resources maps need.
3. **One-dir layout** — Required for WebEngine subprocess and large asset trees; matches Inno Setup expectations (`dist/projectx/`).
4. **Lowest migration cost** — Nuitka would need a full rebuild of hooks, compile flags, and CI; cx_Freeze would need new spec format and untested WebEngine support.

Nuitka may be reconsidered later for startup time or binary protection, but it is not justified for the first Windows release.

---

## 3. Build scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_linux.sh` | Linux one-dir PyInstaller bundle → `dist/projectx/` |
| `scripts/build_windows.sh` | Windows bundle via Windows Python (WSL auto-detect or explicit path) |
| `scripts/clean_build.sh` | Remove `build/`, `dist/`, `__pycache__` |

Common flags:

- `--prepare-only` — fetch Leaflet, verify branding, run path checks; skip PyInstaller.

Environment variables:

| Variable | Purpose |
|----------|---------|
| `PROJECTX_PYTHON` | Linux/host Python for prep (default `python3`; build uses `.venv` on Linux) |
| `PROJECTX_WINDOWS_PYTHON` | Path to Windows `python.exe` when building from WSL/Linux |
| `PROJECTX_BUILD` | Optional build label (see `installer/README.md`) |

---

## 4. PyInstaller spec

File: `installer/projectx.spec`

Includes:

- **Qt WebEngine** — `collect_all` for `PySide6.QtWebEngineWidgets`, `QtWebEngineCore`, `QtWebChannel`
- **Leaflet** — via `src/resources/map/leaflet/` inside `resources/`
- **Translations** — `src/resources/translations/`
- **Icons / flags / logos** — full `src/resources/` tree
- **HTML / CSS / JavaScript** — map pages under `src/resources/map/`
- **Runtime config samples** — read-only `config/` subset (user JSON excluded)
- **Seed `data/`** — bundled under `data/`
- **Windows icon** — `projectx.ico` on the executable

Output: **one-dir** bundle `dist/projectx/` with `projectx.exe` (Windows) or `projectx` (Linux).

---

## 5. Runtime paths

All packaged runtime lookups go through `src/app/paths.py`:

| Function | Development | Frozen (Windows) |
|----------|-------------|------------------|
| `bundle_dir()` | `src/` | PyInstaller `_MEIPASS` |
| `resource_path(...)` | `src/resources/...` | Bundled resources |
| `runtime_config_dir()` | `src/config/` | `%APPDATA%/Project X/config/` |
| `runtime_data_dir()` | `<repo>/data/` | `%APPDATA%/Project X/data/` |

Build scripts fail if new hardcoded `"/home/..."` paths appear outside intentionally excluded legacy modules.

**Known legacy exceptions (unchanged by design):**

- `src/engines/rtl/hybrid_engine.py` — deployment-specific Linux paths
- `src/config/aiscatcher.py` — default AIS-Catcher build path (override with `PROJECTX_AIS_CATCHER_EXECUTABLE`)

---

## 6. Build steps (Windows release)

### Step 1 — Prepare (from Linux or WSL)

```bash
./scripts/build_windows.sh --prepare-only
```

### Step 2 — Build the bundle

**WSL (Windows Python auto-detected):**

```bash
./scripts/build_windows.sh
```

**Explicit Windows Python:**

```bash
export PROJECTX_WINDOWS_PYTHON='/mnt/c/Users/you/AppData/Local/Programs/Python/Python312/python.exe'
./scripts/build_windows.sh
```

**Native Windows (Git Bash):**

```bash
./scripts/build_windows.sh
```

### Step 3 — Output

```
dist/projectx/
  projectx.exe
  projectx.ico
  projectx-logo.png
  resources/          # translations, maps, leaflet, flags, branding
  config/             # bundled read-only config
  data/               # seed data
  ... PySide6 / Qt WebEngine runtime DLLs ...
```

Smoke-test on a clean Windows machine:

1. Run `projectx.exe`
2. Complete first-run wizard
3. Open Dashboard map (Qt WebEngine + offline Leaflet)
4. Switch language (translations load from bundle)
5. Confirm user config appears under `%APPDATA%\Project X\config\`

### Step 4 — Installer preparation

On Windows, compile the Inno Setup script:

```
installer/windows/projectx.iss
```

Prerequisites:

- Build output in `dist/projectx/` (Step 2)
- [Inno Setup 6](https://jrsoftware.org/isinfo.php)

The installer creates Start Menu / optional desktop shortcuts and copies the full `dist/projectx/` tree to `{autopf}\Project X`.

Optional metadata before building:

```bash
export PROJECTX_BUILD="2026.07.05"
export PROJECTX_GITHUB_URL="https://github.com/Copex4590/ProjectX"
```

### Step 5 — Clean rebuild

```bash
./scripts/clean_build.sh
./scripts/build_windows.sh
```

---

## 7. Known limitations

| Limitation | Notes |
|------------|-------|
| **No true cross-compile** | Linux Python cannot emit Windows `.exe`; use WSL + Windows Python or a Windows host |
| **Qt WebEngine size** | Bundle is large (~150–300 MB); expected for Chromium-based maps |
| **AIS-Catcher not bundled** | External binary; set `PROJECTX_AIS_CATCHER_EXECUTABLE` on Windows |
| **HybridEngine paths** | Legacy Linux deployment paths; RTL/AIS file playback not portable without env overrides |
| **Code signing** | Unsigned builds may trigger SmartScreen; sign `projectx.exe` and the installer for production |
| **UPX compression** | Enabled in spec; disable if antivirus false-positives occur |
| **Map tiles** | Leaflet is offline; tiles still load from OpenStreetMap CDN unless cached separately |

---

## 8. Linux bundle (optional)

To validate the same spec on Linux (creates `.venv` automatically if needed):

```bash
./scripts/build_linux.sh
```

Produces `dist/projectx/projectx` for local smoke-testing. This does not replace `installer/linux/install.sh` (source-tree install for development).

---

## Verification checklist (SAVE-067)

- [x] Build strategy selected — **PyInstaller**
- [x] Build scripts — `build_linux.sh`, `build_windows.sh`, `clean_build.sh`
- [x] Spec file — `installer/projectx.spec` with WebEngine hooks and full resource bundle
- [x] Runtime paths — verified via `paths.py`; build scripts grep for disallowed hardcoded paths
- [x] `BUILD_WINDOWS.md` — this document
