# Project X Installer

Packaging assets and scripts for distributing Project X as a desktop application.

## Branding assets

| File | Purpose |
|------|---------|
| `src/resources/branding/projectx-logo.svg` | Master vector logo |
| `src/resources/branding/projectx-logo.png` | Application / About / splash |
| `src/resources/branding/projectx.ico` | Windows icon |
| `src/resources/branding/projectx.icns` | macOS icon (future) |

Regenerate PNG and ICO from the master artwork:

```bash
python3 scripts/generate_branding_assets.py
```

Fetch bundled Leaflet map assets (offline map support):

```bash
chmod +x scripts/fetch_leaflet.sh
scripts/fetch_leaflet.sh
```

## Build scripts (SAVE-067 / SAVE-068)

| Script | Purpose |
|--------|---------|
| `scripts/build_windows.bat` | **Native Windows release build (primary — dual-boot workflow)** |
| `scripts/build_installer.bat` | Compile `ProjectX-Setup.exe` after PyInstaller |
| `scripts/verify_windows_installer.bat` | Silent install/uninstall verification (Windows) |
| `scripts/verify_windows_release.sh` | Verify `release/windows/` artifact, website copy, checksums (Linux) |
| `scripts/build_windows.ps1` | PowerShell alternative to `build_windows.bat` |
| `scripts/build_linux_release.sh` | **Official Linux release packages → `release/linux/`** |
| `scripts/prepare_release.sh` | Sync notes, website copies, checksums |
| `scripts/generate_release_checksums.sh` | SHA256 checksum generation |
| `scripts/verify_release.sh` | Full public release verification |
| `scripts/verify_linux_release.sh` | Verify AppImage / .deb contents |
| `scripts/build_linux.sh` | PyInstaller one-dir bundle → `dist/projectx/` (Linux smoke-test) |
| `scripts/build_windows.sh` | Linux asset/path checks; optional WSL alternative |
| `scripts/clean_build.sh` | Remove `build/` and `dist/` |

Full Windows workflow: **`BUILD_WINDOWS.md`**  
Full Linux release workflow: **`docs/LINUX_INSTALLER.md`**  
Public release workflow: **`RELEASE_PROCESS.md`**

## Linux release packages (SAVE-077 / SAVE-085)

Build official public Linux release (AppImage + `.deb` + SHA256SUMS):

```bash
chmod +x scripts/build_linux_release.sh scripts/verify_linux_release.sh
./scripts/build_linux_release.sh
```

Output: `release/linux/` (`ProjectX.deb`, `ProjectX.AppImage`, `SHA256SUMS`) and copies under `website/downloads/linux/`

**Recommended for end users:** `ProjectX.deb` (Linux Mint / Debian). Menu entry displays **Project X** with summary *Professional Maritime Monitoring Platform*. **AppImage** is portable/advanced only.

The `.deb` package includes AppStream metadata for Software Manager, multi-size hicolor icons, optional desktop shortcut and post-install launch (debconf / defaults), and clean uninstall via `sudo dpkg -r projectx`.

## Developer install (source tree — not for public release)

For local development only. **Never distribute `installer/linux/` to end users.**

Installs Project X to `~/.local/share/projectx`, creates a launcher, desktop shortcut, and applications menu entry.

```bash
chmod +x installer/linux/install.sh
installer/linux/install.sh --launch
```

Options:

- `--prefix DIR` — custom install directory
- `--no-desktop` — skip desktop shortcut
- `--no-start-menu` — skip applications menu entry
- `--launch` — start Project X after installation

Uninstall (complete removal — restores never-installed state):

```bash
installer/linux/uninstall.sh
```

For `.deb` installs, run with sudo so system files and the package are removed:

```bash
sudo projectx-uninstall
# or
sudo installer/linux/uninstall.sh
```

Options:

- `--dry-run` — preview paths that would be removed
- `--yes` — skip confirmation prompt
- `--appimage PATH` — also remove a portable AppImage file
- `--self-test` — run built-in verification

Removes program files, configuration, observation points, cache, logs, language/first-run state, icons, desktop entries, and Project X autostart entries. Does **not** remove exported files, unrelated backups, or the development source tree at `~/ProjectX`.

## Windows installer (SAVE-076)

1. Build the PyInstaller bundle and Inno Setup installer on native Windows:

```bat
scripts\build_windows.bat
```

2. Output: `website\downloads\windows\ProjectX-Setup.exe`

3. Verify:

```bat
scripts\verify_windows_installer.bat
```

See **`docs/WINDOWS_INSTALLER.md`** for silent install, uninstall, and clean-VM checklist.

The installer provides:

- Install to **Program Files** (`{autopf}\Project X`)
- **Start Menu** shortcut with official icon
- **Desktop shortcut** (optional task)
- **Launch after installation** (optional task)
- **Clean uninstall** via Windows Settings → Apps
- **Silent install:** `ProjectX-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`

## macOS (future)

- Bundle with `projectx.icns`
- `.app` packaging

## Build metadata

Set at package time:

```bash
export PROJECTX_BUILD="2026.07.05"
export PROJECTX_GITHUB_URL="https://github.com/Copex4590/ProjectX"
```
