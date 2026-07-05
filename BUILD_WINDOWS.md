# Project X — Windows Release Pipeline (SAVE-068)

This document describes the **recommended dual-boot workflow**: develop on **Linux Mint**, build and validate releases on **native Windows**. No WSL, Wine, or cross-compilation is required.

Application functionality is unchanged — this covers build and packaging only.

---

## Recommended workflow

### Linux (development)

Daily work happens entirely on Linux:

```bash
git add .
git commit -m "Your change"
git push
```

That is all the Linux side needs for a Windows release. Bundled assets (Leaflet, branding, translations) are committed in the repository.

Optional local Linux bundle for smoke-testing:

```bash
./scripts/build_linux.sh
```

### Windows (release build)

Boot into Windows, clone or pull the repository, then run **one command**:

```bat
scripts\build_windows.bat
```

PowerShell alternative:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Prerequisites on a fresh Windows machine:

| Tool | Purpose |
|------|---------|
| [Git for Windows](https://git-scm.com/download/win) | Clone / pull the repository |
| [Python 3.10+](https://www.python.org/downloads/) | Build virtual environment (enable **Add to PATH**) |

The batch file automatically:

1. Creates `.venv` if missing
2. Upgrades `pip`
3. Installs `requirements.txt`
4. Installs PyInstaller
5. Runs `installer/projectx.spec`
6. Produces `dist/projectx/`
7. Verifies `dist/projectx/projectx.exe` exists
8. Prints a clear success or failure report
9. Offers to compile `installer/windows/projectx.iss` when Inno Setup is installed

### Output

```
dist/projectx/
  projectx.exe
  projectx.ico
  projectx-logo.png
  resources/
  config/
  data/
  ... PySide6 / Qt WebEngine runtime ...
```

Smoke-test after build:

1. Run `dist\projectx\projectx.exe`
2. Complete the first-run wizard
3. Open the Dashboard map (Qt WebEngine + offline Leaflet)
4. Switch language (translations load from the bundle)
5. Confirm user config under `%APPDATA%\Project X\config\`

### Installer (optional)

If [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed, `build_windows.bat` offers to compile:

```
installer/windows/projectx.iss
```

Manual compile:

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\windows\projectx.iss
```

Output: `installer/windows/Output/ProjectX-Setup.exe` (default Inno Setup output path).

If Inno Setup is not installed, the build script prints a friendly message with the download link — the application bundle in `dist/projectx/` is still complete.

---

## Build strategy

**PyInstaller** remains the chosen bundler (`installer/projectx.spec`):

- Qt WebEngine via `collect_all` hooks
- One-dir layout required for WebEngine subprocess and large assets
- Matches Inno Setup expectations (`dist/projectx/`)

Nuitka and cx_Freeze were evaluated in SAVE-067 and not adopted.

---

## Build scripts reference

| Script | Platform | Purpose |
|--------|----------|---------|
| **`scripts/build_windows.bat`** | **Windows** | **Primary release build (one command)** |
| `scripts/build_windows.ps1` | Windows | PowerShell alternative to the batch file |
| `scripts/build_linux.sh` | Linux | Optional local Linux bundle |
| `scripts/build_windows.sh` | Linux / Git Bash | Asset prep; WSL alternative only |
| `scripts/clean_build.sh` | Linux | Remove `build/` and `dist/` |

---

## PyInstaller spec

File: `installer/projectx.spec`

Bundles:

- Qt WebEngine (`PySide6.QtWebEngineWidgets`, `QtWebEngineCore`, `QtWebChannel`)
- Leaflet (`src/resources/map/leaflet/`)
- Translations (`src/resources/translations/`)
- Map HTML / CSS / JavaScript
- Icons, flags, branding logos
- Read-only config samples and seed `data/`
- Windows icon on `projectx.exe`

Writable runtime files use `src/app/paths.py` (`%APPDATA%/Project X/` on Windows).

---

## Alternative: WSL (not recommended)

WSL is **not** part of the primary workflow. Use it only if you cannot reboot into Windows.

From WSL with Git Bash tools:

```bash
./scripts/build_windows.sh --prepare-only   # asset/path checks on Linux
export PROJECTX_WINDOWS_PYTHON='/mnt/c/Users/you/AppData/Local/Programs/Python/Python312/python.exe'
./scripts/build_windows.sh
```

Limitations:

- Requires a Windows Python install reachable from WSL
- More fragile than native `build_windows.bat`
- Not supported: Wine, Linux Python cross-compile

---

## Runtime paths

| Function | Development (Linux) | Frozen (Windows) |
|----------|---------------------|------------------|
| `bundle_dir()` | `src/` | PyInstaller `_MEIPASS` |
| `resource_path(...)` | `src/resources/...` | Bundled resources |
| `runtime_config_dir()` | `src/config/` | `%APPDATA%/Project X/config/` |
| `runtime_data_dir()` | `<repo>/data/` | `%APPDATA%/Project X/data/` |

**Known legacy exceptions (unchanged):**

- `src/engines/rtl/hybrid_engine.py` — deployment-specific Linux paths
- `src/config/aiscatcher.py` — default AIS-Catcher path (override with `PROJECTX_AIS_CATCHER_EXECUTABLE`)

---

## Known limitations

| Limitation | Notes |
|------------|-------|
| **Dual-boot required** | Windows `.exe` must be built on Windows; Linux dev machine cannot emit native Windows binaries |
| **Qt WebEngine size** | Bundle is large (~150–300 MB) |
| **AIS-Catcher not bundled** | External binary; set `PROJECTX_AIS_CATCHER_EXECUTABLE` on Windows |
| **HybridEngine paths** | Legacy Linux deployment paths only |
| **Code signing** | Unsigned builds may trigger SmartScreen |
| **Map tiles** | Leaflet is offline; tiles load from OpenStreetMap CDN unless cached separately |

Optional build metadata:

```bat
set PROJECTX_BUILD=2026.07.05
set PROJECTX_GITHUB_URL=https://github.com/Copex4590/ProjectX
scripts\build_windows.bat
```

---

## Verification checklist (SAVE-068)

- [x] Dual-boot workflow documented — Linux dev, Windows `build_windows.bat`
- [x] `scripts/build_windows.bat` — full automated Windows build
- [x] `scripts/build_windows.ps1` — optional PowerShell equivalent
- [x] Inno Setup offer / friendly fallback message
- [x] WSL documented as alternative only
- [x] `BUILD_WINDOWS.md` updated
