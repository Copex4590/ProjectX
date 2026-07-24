# Project X — Windows Installer (SAVE-076)

Documentation for the first installable Windows release using **Inno Setup 6** and **PyInstaller**.

Application version: **0.3.1-beta**  
Installer output: **`release/windows/ProjectX-Setup.exe`**

---

## What the installer does

| Feature | Behavior |
|---------|----------|
| **Install location** | `{autopf}\Project X` (64-bit Program Files) |
| **Start Menu** | Shortcut to `projectx.exe` with application icon |
| **Desktop shortcut** | Optional task during setup (unchecked by default) |
| **Application icon** | `projectx.ico` on shortcuts; `projectx.exe` uses bundled icon |
| **Uninstall** | Control Panel / Settings → Apps, or Start Menu → Uninstall Project X |
| **User data** | Preserved under `%APPDATA%\Project X\` after uninstall |

---

## Build the installer

### Prerequisites (Windows)

- Python 3.10+ with PATH enabled
- Git
- [Inno Setup 6](https://jrsoftware.org/isinfo.php)

### One-command build

From the repository root on native Windows:

```bat
scripts\build_windows.bat
```

This runs:

1. PyInstaller → `dist\projectx\projectx.exe`
2. Inno Setup → `release\windows\ProjectX-Setup.exe`

PyInstaller-only (skip installer):

```bat
set SKIP_INSTALLER=1
scripts\build_windows.bat
```

Installer only (after PyInstaller bundle exists):

```bat
scripts\build_installer.bat
```

---

## Silent install and uninstall

### Interactive install

Double-click `ProjectX-Setup.exe` or run from an elevated command prompt.

### Silent install

```bat
ProjectX-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

With desktop shortcut:

```bat
ProjectX-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="desktopicon"
```

Launch after install:

```bat
ProjectX-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="launch"
```

### Silent uninstall

```bat
"%ProgramFiles%\Project X\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

---

## Verification

### Automated (Windows)

After building the installer:

```bat
scripts\verify_windows_installer.bat
```

Checks:

- Silent install to a temp directory
- Bundled resources present
- Silent uninstall removes the install directory

### Manual (clean VM recommended)

1. Copy or build `ProjectX-Setup.exe`
2. Install interactively to Program Files
3. Confirm Start Menu shortcut and optional desktop icon
4. Launch Project X
5. Confirm **First Run Wizard** appears
6. Complete wizard; confirm Dashboard and map load
7. Uninstall from Settings → Apps
8. Confirm `{ProgramFiles}\Project X` is removed

---

## Website integration

The release portal reads `website/releases.json`:

```json
"windows": {
  "file": "ProjectX-Setup.exe"
}
```

Download URL: `website/downloads/windows/ProjectX-Setup.exe` (synced by `scripts/prepare_release.sh`)

After building on Windows, publish the installer binary to the web host (the `.exe` is gitignored; upload separately or attach to a GitHub Release).

Verify website config:

```bash
./website/verify_releases.sh
```

---

## Files

| File | Purpose |
|------|---------|
| `installer/windows/projectx.iss` | Inno Setup script |
| `scripts/build_windows.bat` | Full Windows release build |
| `scripts/build_installer.bat` | Compile installer only |
| `scripts/verify_windows_installer.bat` | Silent install/uninstall test |
| `release/windows/ProjectX-Setup.exe` | Release artifact (generated) |

---

## Known limitations

- **Code signing** not configured — SmartScreen may warn on first run
- **AIS-Catcher** not bundled — set `PROJECTX_AIS_CATCHER_EXECUTABLE` if using RTL-SDR
- **HybridEngine** uses deployment-specific Linux paths — hybrid RTL file mode is not portable to generic Windows installs without configuration
