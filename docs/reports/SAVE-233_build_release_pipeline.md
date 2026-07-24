# SAVE-233 — Build & Release Pipeline Finalization

**Date:** 2026-07-24  
**Version:** `0.3.1-beta`  
**Build stamp:** `0.3.1-beta-20260724`  
**Branch:** `release/0.3.1-alpha.1`  
**Linux Alpha packages:** **PASS**  
**Windows installer binary:** **FAIL** (not buildable on this Linux host)  
**Dual-platform public release:** **FAIL**

---

## Executive verdict

Linux `.deb` and AppImage were rebuilt with a real bundled `PROJECTX_BUILD` stamp, passed `verify_linux_release.sh`, extract-based install/upgrade/uninstall checks, and uninstall `--self-test`. Windows ISS metadata is ready, but `ProjectX-Setup.exe` is still absent and must be produced on native Windows (`scripts\build_windows.bat`).

---

## Packaging fixes in this ticket

| Change | Why |
|--------|-----|
| Write `src/resources/build_stamp` during release builds | Exporting `PROJECTX_BUILD` alone never reached the frozen About dialog (`os.environ` is runtime-only). |
| `version.py` reads stamp file when env unset | Packaged binaries report real build id instead of `dev`. |
| AppStream component id → reverse-DNS + `<developer>` | Cleaner metadata; avoid appimagetool validation failure from duplicate metainfo files. |
| Stronger `verify_linux_release.sh` | Stamp, version, MIT license, themes, map HTML, camera packs. |

---

## Linux package checklist

| Check | Result |
|-------|--------|
| Rebuild `.deb` | **PASS** — `release/linux/ProjectX.deb` |
| Rebuild AppImage | **PASS** — `release/linux/ProjectX.AppImage` |
| `PROJECTX_BUILD` stamp | **PASS** — `0.3.1-beta-20260724` in both packages |
| Version metadata | **PASS** — deb `Version: 0.3.1-beta` |
| Desktop integration | **PASS** — `projectx.desktop`, `/usr/bin/projectx` |
| Icons (hicolor 16–512) | **PASS** |
| MIME/AppStream metadata | **PASS** — MIT; `io.github.copex4590.projectx.appdata.xml` |
| Uninstall script | **PASS** — packaged launcher + `ProjectX-uninstall.sh --self-test` |
| Fresh install test | **PASS\*** — extract-root (not live `dpkg -i`) |
| Upgrade test | **PASS\*** — re-extract over same root |
| Uninstall test | **PASS** — simulation + uninstall self-test |

\*Live system `sudo dpkg -i` / upgrade on a desktop Mint/Ubuntu image still recommended before public announce.

---

## Windows installer checklist

| Check | Result |
|-------|--------|
| Rebuild Setup.exe | **FAIL** — no ISCC / native Windows on this host |
| Installer metadata (ISS) | **PASS** — `MyAppVersion 0.3.1-beta`, VersionInfo\* set |
| Version resources (ISS) | **PASS** — `0.3.1.2` numeric |
| Start Menu | **PASS** (script) — `{group}\Project X` + Uninstall |
| Desktop shortcut option | **PASS** (script) — task `desktopicon` |
| Uninstall entry | **PASS** (script) — `UninstallDisplayName` / icon |
| Application icon | **PASS** (script) — `SetupIconFile` → `projectx.ico` |
| Fresh / upgrade / uninstall install tests | **FAIL** — blocked without `ProjectX-Setup.exe` |
| Stamp wiring in `build_windows.bat` | **PASS** (script updated; needs Windows run) |

---

## Cross-platform resource checks (from Linux packages)

| Asset | Result |
|-------|--------|
| Bundled resources | **PASS** |
| Translations `en` / `hu` | **PASS** |
| Theme `resources/theme/colors.css` | **PASS** |
| Map Leaflet + `map.html` | **PASS** |
| Camera packs (`config/camera_packs/hungary/*`) | **PASS** |
| Database creation (no `data/` in bundle; runtime user dir) | **PASS** |
| First-run wizard (code present in app) | **PASS\*** — not GUI-smoked this ticket |
| Settings migration (`Preferences.migrate`) | **PASS\*** — unit-level import check |

---

## Installed file inventory (`.deb` extract highlights)

- `opt/projectx/projectx` + PyInstaller one-dir bundle  
- `opt/projectx/resources/build_stamp`  
- `opt/projectx/resources/translations/{en,hu}.json`  
- `opt/projectx/resources/map/` (Leaflet + HTML)  
- `opt/projectx/resources/theme/colors.css`  
- `opt/projectx/resources/branding/`  
- `opt/projectx/config/{playback.json,cameras,camera_packs}`  
- `usr/bin/projectx`, `usr/bin/projectx-uninstall`  
- `usr/share/applications/projectx{,-uninstall}.desktop`  
- `usr/share/metainfo/io.github.copex4590.projectx.appdata.xml`  
- `usr/share/icons/hicolor/{16..512}/apps/projectx.png`

Full listing: `/tmp/save233_inventory.txt` (local verify run).

---

## Package size comparison

| Artifact | Previous (bytes) | New (bytes) | Δ |
|----------|------------------|-------------|---|
| `ProjectX.deb` | 178 134 316 | 178 179 056 | +44 740 |
| `ProjectX.AppImage` | 232 539 328 | 232 576 192 | +36 864 |
| `ProjectX-uninstall.sh` | — | 20 969 | — |

Human: **~170 MB** `.deb`, **~222 MB** AppImage (unchanged class).

---

## Release artifact list

| Path | SHA-256 (this build) |
|------|----------------------|
| `release/linux/ProjectX.AppImage` | `45f5f5a57ab5742d50ee898fd176eafe899cd152a5ea040aeafdf796be6dd679` |
| `release/linux/ProjectX.deb` | `2e95e15ec0281c122b2a628892994405f64399adfb217df0145d88790bb2c15d` |
| `release/linux/ProjectX-uninstall.sh` | `9108c673e67be704c915946489c24e4f206d49db0f6f406d2369c59bede7a090` |
| `release/linux/SHA256SUMS` | present |
| `website/downloads/linux/*` | mirrored |
| `release/windows/ProjectX-Setup.exe` | **missing** |

---

## PASS / FAIL summary

| Gate | Verdict |
|------|---------|
| Linux packaging pipeline | **PASS** |
| Windows packaging pipeline (binary) | **FAIL** |
| Dual-platform release readiness | **FAIL** |

### Next (Windows host)

```bat
scripts\build_windows.bat
scripts\verify_windows_installer.bat
```

Then sync with `scripts\prepare_release.sh` / website downloads.

---

## How to reproduce Linux verify

```bash
export PROJECTX_BUILD=0.3.1-beta-20260724
./scripts/build_linux_release.sh
./scripts/verify_linux_release.sh
./scripts/save233_verify_packaging.sh
./release/linux/ProjectX-uninstall.sh --self-test
```
