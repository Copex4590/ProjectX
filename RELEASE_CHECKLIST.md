# Project X — Release Readiness Checklist (SAVE-075)

**Audit date:** 2026-07-05  
**Branch inspected:** `feature/save-008-svg-icons`  
**Application version:** `0.3.0-alpha` (`src/version.py`)  
**Website release ID:** `0.3-alpha` (`website/releases.json`)  
**Scope:** Full repository audit — application, build, website, repository hygiene. No source code was modified.

---

## READY

### Application

| Area | Status | Evidence |
|------|--------|----------|
| **Startup** | Ready | `src/app/application.py` — friendly `sys.excepthook`, no user-facing tracebacks; `src/app/logging_config.py` (WARNING default, `PROJECTX_DEBUG=1` for verbose) |
| **Dashboard** | Ready | `src/gui/dashboardpage.py` — ship counts, connection status, logbook import card, RTL card |
| **Map** | Ready | `src/gui/mappage.py`, map widgets, offline Leaflet at `src/resources/map/leaflet/`, HTML via `app.paths.resource_path()` |
| **AIS** | Ready | `src/ais/` providers (AISStream, local, hybrid), AIS wizard, `ais_manager`, System Health checks |
| **RTL** | Partially ready | RTL-SDR wizard, diagnostics, `rtl_manager`, AIS-Catcher launcher present; hybrid RTL file playback depends on deployment-specific paths (see Needs Attention) |
| **Cameras** | Ready | Camera Manager, selection engine, preview panel, camera wizard, Hungary pack placeholders |
| **Playback** | Ready (limited) | Playback framework and settings exist; MPV is the production backend; others are stubs (documented in README) |
| **Logbook** | Ready | `src/logbook/` — import, XLSX generation, map integration, vessel card logbook button |
| **Statistics** | Ready | `src/gui/statisticspage.py`, `src/vessel_statistics/` |
| **Alerts** | Ready (UI + engine) | Alert Center, Rules page, SQLite engine; automatic monitoring hooks not yet wired (documented) |
| **Translations** | Ready | `en.json` / `hu.json` — 552 keys each, in sync; `language_manager` loads from bundled resources |
| **Settings** | Ready | Settings page (index 9), preferences auto-created, playback/camera diagnostics modules |
| **System Health** | Ready | `src/gui/systemhealthpage.py` — 12 subsystem checks, diagnostic report export with API key redaction |

**Additional application readiness**

- First-run wizard: language → observation → AIS → camera (`src/gui/firstrunwizard.py`)
- Runtime path resolution for packaged builds: `src/app/paths.py` (`%APPDATA%/Project X/` on Windows)
- Python compile check: `python3 -m compileall src` — **passes**
- Bundled resources present: translations, Leaflet, branding ICO/PNG/SVG, 250+ flag SVGs

### Build

| Area | Status | Evidence |
|------|--------|----------|
| **Windows build** | Ready (scripts) | `scripts/build_windows.bat`, `scripts/build_windows.ps1`, dual-boot workflow in `BUILD_WINDOWS.md` |
| **Linux build** | Ready (scripts) | `scripts/build_linux.sh`, auto `.venv`, asset checks |
| **PyInstaller** | Ready | `installer/projectx.spec` — `collect_all` for Qt WebEngine, resources, read-only config subset; runtime `data/` not bundled |
| **Windows installer script** | Ready | `installer/windows/projectx.iss` (Inno Setup 6) |
| **Linux installer script** | Ready | `installer/linux/install.sh`, desktop entry, uninstall script |
| **Runtime resources** | Ready | Leaflet offline bundle, map HTML, translations, flags, camera config packs |
| **Icons / branding** | Ready | `projectx-logo.svg`, `projectx-logo.png`, `projectx.ico` committed under `src/resources/branding/` |
| **Clean build** | Ready | `scripts/clean_build.sh` |

### Website

| Area | Status | Evidence |
|------|--------|----------|
| **Release configuration** | Ready | `website/releases.json` — single source of truth for version, filenames, metadata |
| **Dynamic download links** | Ready | `website/js/releases.js` — reads config, generates `downloads/windows/` and `downloads/linux/` URLs |
| **Documentation page** | Ready | `website/documentation.html` — getting started, requirements, install, source build |
| **Release notes (Markdown)** | Ready | `website/releases/0.3-alpha.md` loaded automatically on home, download, and documentation pages |
| **Site structure** | Ready | `index.html`, `download.html`, `documentation.html`, `screenshots.html`, responsive CSS |
| **Verification script** | Ready | `website/verify_releases.sh` — config, notes, local HTTP checks, URL generation simulation |
| **GitHub link** | Ready | Points to `https://github.com/Copex4590/ProjectX` |

### Repository

| Area | Status | Evidence |
|------|--------|----------|
| **README** | Ready | Comprehensive architecture, install, features, limitations, branding, doc links |
| **LICENSE** | Ready | MIT License present at repository root |
| **`.gitignore`** | Ready | Runtime config, SQLite DBs, build artifacts, venv excluded |
| **Core folder structure** | Ready | `src/`, `installer/`, `scripts/`, `docs/`, `website/`, `data/` |
| **Release documentation** | Ready | `RELEASE_AUDIT.md`, `BUILD_WINDOWS.md`, `docs/RELEASE_NOTES_0.3_ALPHA.md`, `docs/CHANGELOG.md` |
| **Build / packaging docs** | Ready | `installer/README.md`, SAVE-066 through SAVE-074 pipeline docs |

---

## NEEDS ATTENTION

### Application

| Item | Notes |
|------|-------|
| **HybridEngine deployment paths** | `src/engines/rtl/hybrid_engine.py` uses hardcoded `/home/zoli/...` paths for RTL file playback, cache, and API key. Functional on original Linux deployment only unless env/deployment is adjusted. |
| **AIS-Catcher default executable** | `src/config/aiscatcher.py` defaults to `/home/zoli/AIS-catcher/build/AIS-catcher`. Windows/end-user installs must set `PROJECTX_AIS_CATCHER_EXECUTABLE`. |
| **Vessel photo storage paths** | Fixed — `photo_registry.py` uses `runtime_data_dir()`; `ensure_runtime_data_dirs()` creates structure at startup |
| **Playback config path** | `src/config/playback.py` uses package directory, not frozen runtime config dir — read-only defaults OK, user overrides via env only. |
| **Alert automation** | Alert evaluation API exists; automatic hooks from monitoring/timeline not wired (documented in README). |
| **Camera packs → active registry** | Packs managed but not fully loaded into active camera registry (README limitation). |
| **Map tiles** | Leaflet bundled offline; map tiles still fetched from OpenStreetMap CDN — not fully offline. |
| **Windows/Qt WebEngine validation** | PyInstaller hooks added but no recorded smoke test on a clean Windows VM in this audit. |

### Build

| Item | Notes |
|------|-------|
| **No CI release pipeline** | No GitHub Actions or automated build on tag. Builds are manual (dual-boot Windows + Linux scripts). |
| **Inno Setup output not in repo** | `projectx.iss` ready; compiled `ProjectX-Setup.exe` not produced or committed (expected). |
| **UPX enabled in spec** | May trigger antivirus false positives on some Windows systems. |
| **No code signing** | Unsigned `.exe` and installer may trigger SmartScreen warnings. |

### Website

| Item | Notes |
|------|-------|
| **Screenshots are placeholders** | `website/images/screenshots/*.svg` are stylized mockups, not real application captures. |
| **Installer file sizes** | `releases.json` lists `"size": "TBD"` for both platforms. |
| **Version string mismatch** | App/docs use `0.3.0-alpha`; website release portal uses `0.3-alpha`. Consistent enough for alpha but confusing for users and filenames. |
| **Documentation still references repo release doc name** | `docs/RELEASE_NOTES_0.3_ALPHA.md` vs website `0.3-alpha.md` — two parallel naming schemes. |

### Repository

| Item | Notes |
|------|-------|
| **Legacy backup trees in Git** | `src_backup_001/`, `src_backup_002/`, `src_backup_003/` — ~106 tracked files; increases repo noise and confusion for release consumers. |
| **macOS icon placeholder** | `projectx.icns.placeholder` only — no macOS bundle pipeline. |
| **No automated test suite** | Manual verification only; no pytest/CI gate before release. |

---

## OPTIONAL

1. **GitHub Actions** — Windows build on tag + artifact upload to `website/downloads/`.
2. **AppImage build script** — Only needed if Linux distribution remains AppImage-based (see Blockers).
3. **Code signing** — Authenticode for `projectx.exe` and Inno Setup installer.
4. **Real website screenshots** — Replace SVG mockups with PNG/WebP from a running build.
5. **User data migration tool** — Import dev `src/config/*.json` into `%APPDATA%/Project X/config/`.
6. **Offline tile cache** — Bundle or cache OSM tiles for fully offline map use.
7. **Remove `src_backup_*` from repository** — Archive externally or move to a release branch/tag only.
8. **Unified version naming** — Align `0.3-alpha`, `0.3.0-alpha`, and installer filenames.
9. **Desktop notifications for alerts** — Future beta feature.
10. **Inspector GUI** — Currently programmatic only.

---

## BLOCKERS

### 1. Release installer files not published

| Field | Detail |
|-------|--------|
| **Priority** | **P0 — Critical** |
| **Reason** | The official release portal links to `downloads/windows/ProjectX-0.3-alpha-Setup.exe` and `downloads/linux/ProjectX-0.3-alpha.AppImage`, but neither file exists in the repository or upload directory. New users following the website get **404** on download. |
| **Recommended fix** | Build on native Windows (`scripts/build_windows.bat`), compile Inno Setup, produce Linux artifact, copy both into `website/downloads/windows/` and `website/downloads/linux/`, update `releases.json` sizes, run `website/verify_releases.sh`, then publish the website. |

### 2. Linux distribution format mismatch (AppImage vs actual build pipeline)

| Field | Detail |
|-------|--------|
| **Priority** | **P0 — Critical** |
| **Reason** | `website/releases.json` and release notes advertise **`ProjectX-0.3-alpha.AppImage`**, but the repository provides **`installer/linux/install.sh`** (source-tree shell installer) and **`scripts/build_linux.sh`** (PyInstaller one-dir bundle). **No AppImage build script or artifact pipeline exists.** |
| **Recommended fix** | Either (a) add an AppImage build step and produce the advertised file, or (b) change `releases.json`, release notes, and documentation to match the actual Linux deliverable (e.g. tarball of `dist/projectx/` or the shell installer script) before publishing. |

### 3. Windows release not validated on a clean target system

| Field | Detail |
|-------|--------|
| **Priority** | **P1 — High** |
| **Reason** | First public Windows release requires proof that `projectx.exe` starts, Qt WebEngine map loads, first-run wizard completes, and user data lands in `%APPDATA%/Project X/`. This audit found scripts and spec ready but **no recorded clean-VM smoke test**. |
| **Recommended fix** | On a fresh Windows 10/11 VM: `git pull` → `scripts/build_windows.bat` → run `dist/projectx/projectx.exe` → verify map, translations, System Health full check → compile and test Inno Setup installer end-to-end. Document results in release notes or a short `docs/WINDOWS_SMOKE_TEST.md`. |

### 4. Version identifier inconsistency across release surfaces

| Field | Detail |
|-------|--------|
| **Priority** | **P1 — High** |
| **Reason** | Application and Inno Setup use **`0.3.0-alpha`** (`src/version.py`, `installer/windows/projectx.iss`); website portal uses **`0.3-alpha`** and filenames like `ProjectX-0.3-alpha-Setup.exe`. Support, caching, and user trust suffer when version strings diverge. |
| **Recommended fix** | Pick one canonical public version (recommend `0.3.0-alpha` to match the app) and align `website/releases.json`, release notes filename, installer filenames, and marketing copy in a single maintenance pass. |

### 5. HybridEngine unusable on default Windows/end-user installs

| Field | Detail |
|-------|--------|
| **Priority** | **P1 — High** (for RTL/hybrid AIS users) |
| **Reason** | Hybrid RTL mode relies on hardcoded Linux paths in `hybrid_engine.py` for ship folders, cache, and API key. A Windows user installing from the release portal **cannot use hybrid RTL file playback** without manual path/env changes not covered by the installer. |
| **Recommended fix** | Before marketing RTL/hybrid mode on the website, document it as Linux-only OR route hybrid paths through `app.paths` / preferences (separate change). For alpha, explicitly label RTL-SDR and AIS-Catcher as optional advanced setup in website documentation. |

---

## Pre-release action summary

| Step | Owner | Blocker addressed |
|------|-------|-------------------|
| Resolve Linux artifact format (AppImage vs installer script) | Release | #2 |
| Build and upload Windows + Linux installers to `website/downloads/` | Release | #1 |
| Align version strings across app, installer, website | Release | #4 |
| Clean Windows VM smoke test | QA | #3 |
| Document RTL/hybrid limitations on website docs | Docs | #5 |
| Replace screenshot placeholders before public launch | Website | — |
| Run `./website/verify_releases.sh` after uploads | Release | #1 |

---

## Audit verification performed

| Check | Result |
|-------|--------|
| `python3 -m compileall src` | Pass |
| Bundled resources (`paths.resource_path`) | Pass — translations, Leaflet, ICO present |
| `website/verify_releases.sh` | Pass — config, markdown notes, local HTTP 200; installer files **warn** (missing) |
| Translation key parity | Pass — 552 lines each in `en.json` / `hu.json` |
| `.gitignore` excludes runtime DB/config | Pass |
| `LICENSE` present | Pass — MIT |
| PyInstaller spec WebEngine hooks | Pass — `collect_all` in `installer/projectx.spec` |
| Website dynamic links from `releases.json` | Pass — simulated 0.4-beta URL generation |

**Overall assessment:** Project X is **structurally ready for an alpha release candidate** — application subsystems, build scripts, packaging spec, and release portal infrastructure are in place. **Public release is blocked** until installer artifacts are produced/uploaded, the Linux distribution format mismatch is resolved, and a clean Windows validation pass is completed.
