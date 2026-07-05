# Project X — Linux Installer & Release Packages (SAVE-077)

Application version: **0.3.0-alpha**

Primary release format: **AppImage**  
Secondary format: **`.deb`** (Debian/Ubuntu/Linux Mint)

---

## Build release packages

From the repository root on Linux:

```bash
chmod +x scripts/build_linux_release.sh scripts/verify_linux_release.sh
./scripts/build_linux_release.sh
```

Output:

```
release/linux/
  ProjectX-0.3.0-alpha-x86_64.AppImage
  projectx_0.3.0-alpha_amd64.deb
  SHA256SUMS
```

Website copies (for the release portal):

```
website/downloads/linux/
```

Verify:

```bash
./scripts/verify_linux_release.sh
```

Skip `.deb` generation:

```bash
SKIP_DEB=1 ./scripts/build_linux_release.sh
```

---

## AppImage installation (recommended)

1. Download `ProjectX-0.3.0-alpha-x86_64.AppImage`
2. Make executable: `chmod +x ProjectX-0.3.0-alpha-x86_64.AppImage`
3. Run: `./ProjectX-0.3.0-alpha-x86_64.AppImage`

Optional desktop integration:

```bash
./ProjectX-0.3.0-alpha-x86_64.AppImage --install
```

Or integrate manually with your desktop environment’s “Add application” flow.

The AppImage includes:

- `AppRun` launcher
- `projectx.desktop` (menu entry template)
- `projectx.png` application icon
- Full PyInstaller bundle (`resources/`, translations, branding, config)

---

## .deb installation (Linux Mint / Ubuntu / Debian)

```bash
sudo dpkg -i projectx_0.3.0-alpha_amd64.deb
sudo apt-get install -f
```

Installs to:

| Path | Content |
|------|---------|
| `/opt/projectx/` | Application bundle |
| `/usr/bin/projectx` | Launcher |
| `/usr/share/applications/projectx.desktop` | Menu entry |
| `/usr/share/icons/hicolor/256x256/apps/projectx.png` | Icon |

Launch from the applications menu or run `projectx`.

Uninstall:

```bash
sudo dpkg -r projectx
```

User data remains under `~/.local/share/projectx/` or frozen paths as configured by the application.

---

## Package contents verified at build time

- Application executable (`projectx`)
- Icons (`projectx.ico`, `projectx-logo.png`, menu icon)
- Desktop launcher metadata
- Resources (maps, Leaflet, flags)
- Translations (`en.json`, `hu.json`)
- Branding assets
- Bundled read-only configuration (`config/playback.json`, camera packs)

---

## Fresh Linux Mint checklist

1. Build or download release artifacts
2. **AppImage:** run the file → First Run Wizard should start
3. **AppImage:** confirm menu integration if using `--install`
4. **.deb:** `sudo dpkg -i …` → launch **Project X** from menu
5. Confirm icon displays in the applications menu
6. Open Dashboard map (Qt WebEngine + offline Leaflet)
7. Run System Health full check

---

## Website integration

`website/releases.json`:

```json
"linux": {
  "file": "ProjectX-0.3.0-alpha-x86_64.AppImage"
}
```

Download URL: `website/downloads/linux/ProjectX-0.3.0-alpha-x86_64.AppImage`

Verify website config:

```bash
./website/verify_releases.sh
```

Release binaries are gitignored; upload to the web host after building.

---

## Related scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_linux_release.sh` | Full Linux release build |
| `scripts/build_linux.sh` | PyInstaller bundle only |
| `scripts/verify_linux_release.sh` | Post-build package verification |
| `installer/linux/install.sh` | Legacy source-tree dev installer |

---

## Known limitations

- AppImage and `.deb` require a **glibc-based x86_64** Linux system
- Map tiles still load from OpenStreetMap CDN (Leaflet assets are bundled offline)
- AIS-Catcher is not bundled; configure `PROJECTX_AIS_CATCHER_EXECUTABLE` if needed
- HybridEngine uses deployment-specific paths on non-portable RTL setups
