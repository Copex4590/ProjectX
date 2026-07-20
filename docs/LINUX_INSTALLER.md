# Project X — Linux Release Packages (SAVE-077 / SAVE-085)

Application version: **0.3.0-alpha**

Public Linux release contents:

| File | Role |
|------|------|
| `ProjectX.deb` | **Recommended** — Linux Mint, Ubuntu, Debian |
| `ProjectX.AppImage` | Portable / advanced — no system install |
| `SHA256SUMS` | Optional integrity verification |

The `installer/linux/` directory is **developer-only** (source-tree install). It is not part of any public release.

---

## Which file should I download?

- **Linux Mint, Ubuntu, or Debian:** download **`ProjectX.deb`**. You get a **Project X** entry in the applications menu and can uninstall from Software Manager.
- **Portable use without installing:** download **`ProjectX.AppImage`**. You must mark it executable and run it manually. It does **not** install a menu shortcut.
- **`SHA256SUMS`:** optional — run `sha256sum -c SHA256SUMS` only if you want to verify downloads.

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
  ProjectX.deb
  ProjectX.AppImage
  SHA256SUMS
```

Verify:

```bash
./scripts/verify_linux_release.sh
```

---

## .deb installation (recommended for Linux Mint)

1. Download `ProjectX.deb`
2. Double-click to open **GDebi Package Installer**, or run:

```bash
sudo dpkg -i ProjectX.deb
sudo apt-get install -f
```

3. Launch **Project X** from the applications menu

During installation the package can optionally:

- **Create a desktop shortcut** on the installing user's desktop (enabled by default)
- **Launch Project X** when installation completes (enabled by default)

These options use **debconf** when you install from a terminal with `sudo dpkg -i`. GDebi and Software Manager usually run the installer non-interactively, so both options default to **on**. To opt out from a terminal:

```bash
sudo debconf-set-selections <<'EOF'
projectx projectx/desktop-shortcut boolean false
projectx projectx/launch-after-install boolean false
EOF
sudo dpkg -i ProjectX.deb
```

Or use environment variables for a single install:

```bash
sudo PROJECTX_NO_DESKTOP=1 PROJECTX_NO_LAUNCH=1 dpkg -i ProjectX.deb
```

**Why not Windows-style checkboxes in GDebi?** Debian packages do not support Inno Setup–style task lists in graphical installers. The Linux-native approach is debconf (terminal), sensible defaults (desktop shortcut + launch on), and the applications menu entry always created via `/usr/share/applications/`.

Installs to:

| Path | Content |
|------|---------|
| `/opt/projectx/` | Application bundle |
| `/usr/bin/projectx` | Command-line launcher |
| `/usr/share/applications/projectx.desktop` | Menu entry (**Project X**) |
| `/usr/share/metainfo/projectx.appdata.xml` | Software Manager title and description |
| `/usr/share/icons/hicolor/*/apps/projectx.png` | Menu icons (16–512 px) |

Uninstall:

```bash
sudo dpkg -r projectx
```

Or remove **Project X** from Software Manager (package name `projectx`). The menu entry, system icons, and desktop shortcut (for the installing user) are removed automatically. **User configuration is kept** under `~/.local/share/projectx/` after uninstall (RC1 policy — reinstall restores settings). To wipe data manually: `rm -rf ~/.local/share/projectx/`.

**Complete uninstall (remove user data):** run **Project X Uninstall** from the applications menu, or `ProjectX-uninstall.sh`, and choose **Yes** when asked to remove user data. This removes bootstrap profile data, cache, and the configured Project X data root referenced in `preferences.json` (for example `~/Project X/`). Standard `sudo dpkg -r projectx` does **not** remove user data.

---

## Portable AppImage (advanced)

Use only when you need a single file without system installation.

1. Download `ProjectX.AppImage`
2. Mark executable: right-click → Properties → Permissions → **Allow executing file as program**, or:

```bash
chmod +x ProjectX.AppImage
```

3. Run: double-click the file, or `./ProjectX.AppImage` from a terminal

**Important:** This release does **not** support `./ProjectX.AppImage --install`. That flag is not handled by the AppImage launcher and will be passed to the application. The AppImage does not add itself to the applications menu. Optional third-party integration (e.g. AppImageLauncher) is outside this package.

To uninstall: delete `ProjectX.AppImage`. Remove any manual shortcuts you created.

The AppImage bundle includes `AppRun`, embedded desktop metadata, icon, and the full PyInstaller application tree.

---

## Verify downloads (optional)

```bash
sha256sum -c SHA256SUMS
```

Run from the folder containing `ProjectX.deb` and `ProjectX.AppImage`.

---

## Fresh Linux Mint checklist

1. Download **`ProjectX.deb`** (recommended)
2. Install via GDebi or `sudo dpkg -i ProjectX.deb`
3. Launch **Project X** from the menu → First Run Wizard should start
4. Confirm icon in the applications menu
5. Open Dashboard map (Qt WebEngine + offline Leaflet)
6. Run System Health full check

---

## Website integration

`website/releases.json` — primary Linux download is `ProjectX.deb`; portable option is `ProjectX.AppImage`.

Verify website config:

```bash
./website/verify_releases.sh
```

---

## Related scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_linux_release.sh` | Full Linux public release build |
| `scripts/build_linux.sh` | PyInstaller bundle only (developer smoke test) |
| `scripts/verify_linux_release.sh` | Post-build package verification |

Developer source-tree install (not for end users): see **`installer/README.md`**.

---

## Known limitations

- AppImage and `.deb` require a **glibc-based x86_64** Linux system
- Map tiles still load from OpenStreetMap CDN (Leaflet assets are bundled offline)
- AIS-Catcher is not bundled; configure `PROJECTX_AIS_CATCHER_EXECUTABLE` if needed
