# Project X 0.3-alpha — Release Notes

**Release:** 0.3-alpha  
**Date:** 2026-07-05  
**Status:** Alpha

Project X 0.3-alpha focuses on stabilization, documentation, version alignment, and release packaging readiness.

## Highlights

- Vessel database with ShipRegistry synchronization, search, filters, and sorting
- Vessel photo framework and 250 SVG flags in the vessel information card
- Timeline recording with arrival and departure detection
- Statistics dashboard with cached aggregates and charts
- Alert rules engine, Alert Center, and rules management UI
- Camera packs, playback backends, and diagnostics tooling
- System Health center and RTL-SDR setup assistant
- Native Windows build pipeline and official website release portal

## Packaging

- **Windows:** Inno Setup installer — `ProjectX-Setup.exe`
- **Linux (primary):** AppImage — `ProjectX-0.3.0-alpha-x86_64.AppImage`
- **Linux (secondary):** Debian package — `projectx_0.3.0-alpha_amd64.deb`

## Linux installation

### AppImage (recommended)

```bash
chmod +x ProjectX-0.3.0-alpha-x86_64.AppImage
./ProjectX-0.3.0-alpha-x86_64.AppImage
```

Optional menu integration:

```bash
./ProjectX-0.3.0-alpha-x86_64.AppImage --install
```

### Debian / Linux Mint (.deb)

```bash
sudo dpkg -i projectx_0.3.0-alpha_amd64.deb
sudo apt-get install -f
projectx
```

Build packages from source:

```bash
./scripts/build_linux_release.sh
```

See **`docs/LINUX_INSTALLER.md`** for full details.

## Windows installation

1. Download `ProjectX-Setup.exe` from the official website.
2. Run the installer (administrator privileges required for Program Files).
3. Launch **Project X** from the Start Menu.
4. Complete the First Run Wizard on first launch.

Silent install (enterprise / scripted deployment):

```bat
ProjectX-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

With desktop shortcut:

```bat
ProjectX-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="desktopicon"
```

## Notes

- AIS-Catcher is not bundled; configure `PROJECTX_AIS_CATCHER_EXECUTABLE` on Windows if needed
- Map tiles still load from OpenStreetMap CDN; Leaflet assets are bundled offline
- Unsigned builds may trigger SmartScreen until code signing is configured
