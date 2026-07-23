# Project X — Release Finalization (SAVE-205)

**Release:** `0.3.1-alpha.1`  
**Channel:** First Public Test  
**Branch:** `release/0.3.1-alpha.1`  
**Date:** 2026-07-23  
**Scope:** Release engineering only (version identity, docs, menus, packaging metadata).

---

## Final recommendation

**READY FOR PUBLIC TEST**

Linux-first public test may proceed after rebuild of Linux packages from this finalized tree (so embedded `.deb` version matches `0.3.1-alpha.1`). Windows remains prepared-but-unbuilt until a native Windows packaging run produces `ProjectX-Setup.exe`.

---

## Release contents

| Item | Location / value |
|------|------------------|
| Application version | `0.3.1-alpha.1` (`src/version.py`, `__version__`) |
| About / splash / window title | Driven by `PROJECT_VERSION` |
| Qt application version | `Application.setApplicationVersion(PROJECT_VERSION)` |
| Manifest | `release/manifest.json` → `0.3.1-alpha.1` |
| Website releases | `website/releases.json` → `latest: 0.3.1-alpha.1` |
| Release notes | `release/notes/0.3.1-alpha.1.md`, `docs/RELEASE_NOTES_0.3.1_ALPHA.1.md` |
| Website page | `website/releases/0.3.1-alpha.1.md` |
| CHANGELOG | `docs/CHANGELOG.md` section `[0.3.1-alpha.1]` |
| README | Version + known issues for public test |
| License | MIT (`LICENSE`) |
| Stabilization | SAVE-202 / SAVE-203 runtime hardening included on branch |

### Menu finalization

| Action | Behavior |
|--------|----------|
| File → Exit | Implemented (`exit_requested` → `QApplication.quit`) |
| File → New Profile | Disabled — **Coming Soon** |
| MarineTraffic / AISHub | Not activatable (SAVE-203) |

---

## Supported platforms

| Platform | Support for this release |
|----------|---------------------------|
| Linux Mint 21+ / Ubuntu 22.04+ / Debian amd64 | **Yes** — `.deb` (recommended) + AppImage |
| Windows 10+ x64 | **Prepared** — build Inno installer on Windows before publish |
| macOS | Not supported |

---

## Installation methods

### Linux — Debian package (recommended)

```bash
sudo dpkg -i ProjectX.deb
sudo apt-get install -f
```

Uninstall: Software Manager, `sudo dpkg -r projectx`, or `ProjectX-uninstall.sh`.

### Linux — AppImage (portable)

```bash
chmod +x ProjectX.AppImage
./ProjectX.AppImage
```

Data directory: `~/.local/share/projectx/`

### Windows — Inno Setup installer

```bat
scripts\build_windows.bat
```

Output: `release/windows/ProjectX-Setup.exe`  
Data directory: `%APPDATA%\Project X\`  
Script prepared: `installer/windows/projectx.iss` (`MyAppVersion "0.3.1-alpha.1"`, numeric `0.3.1.1`, icon `projectx.ico`).

### Development

```bash
# from repo with venv
PYTHONPATH=src python -m main
```

---

## Release assets

| Asset | Path | Status |
|-------|------|--------|
| Linux AppImage | `release/linux/ProjectX.AppImage` | Present; SHA256 verified after SAVE-205 refresh |
| Linux `.deb` | `release/linux/ProjectX.deb` | Present; **rebuild required** so control `Version:` becomes `0.3.1-alpha.1` (currently embeds `0.3.1-alpha`) |
| Linux uninstall | `release/linux/ProjectX-uninstall.sh` | Present |
| Linux checksums | `release/linux/SHA256SUMS` | Regenerated to match current binaries |
| Website Linux mirror | `website/downloads/linux/` | Synced checksums |
| Windows installer | `release/windows/ProjectX-Setup.exe` | **Missing** — audit/prepare only on this host |
| Windows checksums | `release/windows/SHA256SUMS` | Not created until installer exists |
| Release archive | N/A as separate tarball — use Git tag + `release/` folder | Tag `v0.3.1-alpha.1` when publishing |

Website mirror for Windows: `website/downloads/windows/` (README only until build).

---

## Known issues

1. **Linux packages must be rebuilt** from HEAD so `.deb` control version and in-app binary match `0.3.1-alpha.1`.
2. **Windows `ProjectX-Setup.exe` not produced** on Linux; Inno script and docs are ready.
3. **File → New Profile** Coming Soon (disabled).
4. **MarineTraffic / AISHub** Coming Soon / not activatable.
5. AIS reconnect backoff up to 60s after repeated failures.
6. Logbook XLSX may lag CSV until background worker / open.
7. Legacy absolute Hybrid/logbook paths not auto-migrated.
8. Alpha quality — not for unsupervised production fleets.

---

## Verification performed (SAVE-205)

- `PROJECT_VERSION` / `__version__` == `0.3.1-alpha.1`
- Manifest + website JSON aligned
- Inno `MyAppVersion` / `MyAppVersionNumeric` updated
- README, CHANGELOG, installer docs, release notes updated
- Menu Exit wired; New Profile disabled with Coming Soon
- Linux `SHA256SUMS` regenerated and verifies AppImage, `.deb`, uninstall script
- Windows packaging: script, icon path, output naming audited — no binary build

---

## Publish steps (operators)

1. Run `scripts/build_linux_release.sh` from this branch; refresh website downloads.  
2. On Windows: `scripts\build_windows.bat` → place `ProjectX-Setup.exe` + SHA256SUMS.  
3. Tag `v0.3.1-alpha.1` and attach assets + notes.  
4. Complete `docs/reports/v0.3.1-alpha.1_first_public_test_checklist.md`.

---

## Recommendation (exact)

**READY FOR PUBLIC TEST**
