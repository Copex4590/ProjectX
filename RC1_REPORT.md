# Project X — Release Candidate RC1 Report (SAVE-080)

**Audit date:** 2026-07-05  
**Candidate:** RC1 (first public Alpha)  
**Application version:** `0.3.0-alpha`  
**Website release ID:** `0.3-alpha`  
**RC1 package path:** `release/RC1/`  
**Assembly script:** `./scripts/prepare_rc1.sh`

---

## Executive summary

Repository **metadata, website portal, build scripts, and release workflow** are complete and internally consistent. **Platform binaries, checksums, and end-user download paths are not present.** RC1 cannot be published until Windows and Linux builds are produced and synced.

**FINAL STATUS: PUBLIC RELEASE BLOCKED**

---

## 1. Full repository audit

### Source tree

| Area | Status | Notes |
|------|--------|-------|
| Application entry (`src/main.py`, `src/version.py`) | ✓ Ready | Version `0.3.0-alpha` |
| Core modules (gui, engine, ais, alerts, etc.) | ✓ Ready | Source tree intact |
| PyInstaller spec (`installer/projectx.spec`) | ✓ Ready | WebEngine + resources configured |
| Requirements (`requirements.txt`) | ✓ Ready | Present |
| Runtime branding | ✓ Ready | `projectx.ico`, `projectx-logo.png` |
| Translations | ✓ Ready | `en.json`, `hu.json` |
| Offline map (Leaflet) | ✓ Ready | `src/resources/map/leaflet/leaflet.js` |
| Config defaults | ✓ Ready | `src/config/playback.json` (not under `resources/config`) |
| PyInstaller output (`dist/`, `build/`) | ✗ Missing | No local build artifacts |

### Build scripts

| Script | Status | Result |
|--------|--------|--------|
| `scripts/build_linux_release.sh` | ✓ Present | Not run (long build; no AppImage/deb output) |
| `scripts/build_linux.sh` | ✓ Present | PyInstaller smoke-test path |
| `scripts/build_windows.bat` / `.ps1` | ✓ Present | Native Windows workflow |
| `scripts/build_windows.sh` | ✓ Present | Asset/path checks pass; WSL Python not configured |
| `scripts/build_installer.bat` | ✓ Present | Inno Setup compile |
| `scripts/prepare_release.sh` | ✓ Present | Sync notes, website, checksums |
| `scripts/prepare_rc1.sh` | ✓ Present | Assembled `release/RC1/` |
| `scripts/generate_release_checksums.sh` | ✓ Present | No artifacts to hash |
| Shell syntax (`bash -n scripts/*.sh`) | ✓ Pass | All scripts parse |

### Installers

| Component | Status | Notes |
|-----------|--------|-------|
| Windows Inno Setup (`installer/windows/projectx.iss`) | ✓ Ready | Version, icon, uninstall configured; output → `release/windows/` |
| Linux AppImage pipeline | ✓ Script ready | Artifact not built |
| Linux `.deb` pipeline | ✓ Script ready | Artifact not built |
| `ProjectX-Setup.exe` | ✗ Missing | Requires Windows build |
| AppImage / `.deb` | ✗ Missing | Requires `./scripts/build_linux_release.sh` |

### Website

| Check | Status |
|-------|--------|
| Pages (home, download, docs, screenshots) | ✓ HTTP 200 |
| Dynamic release portal (`releases.json`, `js/releases.js`) | ✓ Working |
| Release notes (`releases/0.3-alpha.md`) | ✓ Present |
| Internal links / assets | ✓ No broken links |
| Download artifacts | ✗ HTTP 404 for both platforms |

### Release folder

| Path | Status |
|------|--------|
| `release/manifest.json` | ✓ Present |
| `release/notes/` | ✓ Present (2 files) |
| `release/windows/` | ✓ Directory; **no `.exe`** |
| `release/linux/` | ✓ Directory; **no packages** |
| `release/checksums/` | ✓ Directory; **no SHA256SUMS** |
| `release/RC1/` | ✓ Assembled (metadata + notes only) |

### Documentation

| Document | Version aligned |
|----------|-----------------|
| `docs/RELEASE_NOTES_0.3_ALPHA.md` | ✓ `0.3.0-alpha` |
| `docs/CHANGELOG.md` | ✓ `[0.3.0-alpha]` |
| `docs/WINDOWS_INSTALLER.md` | ✓ `0.3.0-alpha` |
| `docs/LINUX_INSTALLER.md` | ✓ References AppImage/deb names |
| `RELEASE_PROCESS.md` | ✓ |
| `RELEASE_CHECKLIST.md` | ✓ |
| `RELEASE_VALIDATION.md` | ✓ |

---

## 2. Version consistency

All checked locations agree on the public Alpha version:

| Location | Value | Match |
|----------|-------|-------|
| `src/version.py` (`PROJECT_VERSION`) | `0.3.0-alpha` | ✓ |
| `release/manifest.json` → `version` | `0.3.0-alpha` | ✓ |
| `release/manifest.json` → `website_version` | `0.3-alpha` | ✓ |
| `website/releases.json` → `latest` | `0.3-alpha` | ✓ |
| `website/releases.json` → `windows.version` | `0.3.0-alpha` | ✓ |
| `website/releases.json` → `linux.version` | `0.3.0-alpha` | ✓ |
| `installer/windows/projectx.iss` (`MyAppVersion`) | `0.3.0-alpha` | ✓ |
| `docs/CHANGELOG.md` | `0.3.0-alpha` | ✓ |
| Linux artifact filenames | `…0.3.0-alpha…` | ✓ |

**Note:** Website marketing label (`0.3-alpha`) intentionally differs from semver app string (`0.3.0-alpha`); both are documented and cross-linked in manifest.

---

## 3. Artifact validation

| Artifact | Expected location | Present | Checksums |
|----------|-------------------|---------|-----------|
| Windows installer | `release/windows/ProjectX-Setup.exe` | **NO** | **NO** |
| Linux AppImage | `release/linux/ProjectX-0.3.0-alpha-x86_64.AppImage` | **NO** | **NO** |
| Linux `.deb` | `release/linux/projectx_0.3.0-alpha_amd64.deb` | **NO** | **NO** |
| Combined checksums | `release/checksums/SHA256SUMS` | **NO** | — |
| Per-file `.sha256` | `release/checksums/*.sha256` | **NO** | — |
| Release notes | `release/notes/0.3.0-alpha*.md` | **YES** | — |
| Manifest | `release/manifest.json` | **YES** | — |
| Website download copies | `website/downloads/{windows,linux}/` | **NO** | — |

### RC1 package contents (`release/RC1/`)

Assembled via `./scripts/prepare_rc1.sh`:

```
release/RC1/
├── manifest.json
├── releases.json
├── INVENTORY.md
├── notes/
│   ├── 0.3.0-alpha.md
│   ├── 0.3.0-alpha-full.md
│   └── website-0.3-alpha.md
├── checksums/          (empty — no hashes yet)
├── windows/            (empty — no installer)
├── linux/              (empty — no packages)
└── website-downloads/  (empty — no mirrored binaries)
```

---

## 4. Verification script results

| Script | Exit | Summary |
|--------|------|---------|
| `./scripts/verify_release.sh` | 0 | Structure PASS; 4 warnings (missing artifacts, checksums, website copies) |
| `./scripts/verify_linux_release.sh` | 1 | **FAIL** — AppImage not found |
| `./scripts/validate_public_download.sh` | 1 | **FAIL** — download URLs return HTTP 404 |
| `website/verify_releases.sh` | 0 | Config PASS; installers not uploaded |
| `./scripts/build_windows.sh` | 0 | Asset/path checks PASS; full Windows build requires native Windows |

### Final verification checklist

| Gate | Result |
|------|--------|
| ✓ Build | **BLOCKED** — no `dist/projectx/`; Linux release build not run |
| ✓ Installer | **BLOCKED** — `ProjectX-Setup.exe` missing |
| ✓ Linux package | **BLOCKED** — AppImage and `.deb` missing |
| ✓ Website | **PASS** — pages and portal functional |
| ✓ Downloads | **FAIL** — binaries return 404 |
| ✓ Checksums | **FAIL** — nothing generated |
| ✓ Manifest | **PASS** — valid and aligned with `releases.json` |
| ✓ Documentation | **PASS** — version-aligned release docs |

---

## READY ITEMS

- Application version `0.3.0-alpha` consistent across source, manifest, installer script, and docs
- Website release portal (`releases.json`, dynamic download cards, release notes loading)
- All main website pages serve correctly; no broken internal navigation
- Release folder structure, manifest, and release notes copies complete
- Windows Inno Setup script (version, icon, uninstall entry) ready for compile
- Linux release build + verify scripts ready (`build_linux_release.sh`, `verify_linux_release.sh`)
- Release workflow documented (`RELEASE_PROCESS.md`, `RELEASE_VALIDATION.md`)
- RC1 staging folder assembled with inventory (`release/RC1/INVENTORY.md`)
- 15 build/verify scripts present; shell syntax valid

---

## WARNINGS

| # | Item | Impact |
|---|------|--------|
| W1 | `releases.json` file sizes show `"TBD"` | Download cards lack size info for users |
| W2 | Screenshot pages use SVG placeholders | Acceptable for alpha; replace with real captures before marketing push |
| W3 | Linux `.deb` listed in manifest but no secondary download button on website | Users must read release notes for `.deb` path |
| W4 | `RELEASE_CHECKLIST.md` contains stale pre-SAVE-077 references | Audit doc not updated after Linux pipeline landed |
| W5 | No `dist/` or `build/` in repo | Expected (gitignored); confirms no local smoke build was retained |
| W6 | WSL Windows Python not configured | `build_windows.sh` cannot produce installer from Linux host |

---

## BLOCKERS

| # | Blocker | Required action |
|---|---------|-----------------|
| B1 | **Windows installer missing** | On Windows: `scripts\build_windows.bat` → `scripts\verify_windows_installer.bat` |
| B2 | **Linux AppImage missing** | `./scripts/build_linux_release.sh` → `./scripts/verify_linux_release.sh` |
| B3 | **Linux `.deb` missing** | Produced by same Linux release script |
| B4 | **Checksums missing** | `./scripts/generate_release_checksums.sh` after artifacts exist |
| B5 | **Website download copies missing** | `./scripts/prepare_release.sh` to sync `website/downloads/` |
| B6 | **RC1 package incomplete** | Re-run `./scripts/prepare_rc1.sh` after B1–B5 |
| B7 | **End-user install smoke tests not done** | Clean VM: install → First Run Wizard → app launch (Windows + Linux) |
| B8 | **Public download validation failing** | `./scripts/validate_public_download.sh` must exit 0 before publish |

---

## RECOMMENDATIONS

1. **Build sequence** — Windows native build first (or copy artifact into `release/windows/`), then Linux `./scripts/build_linux_release.sh` on Mint/Ubuntu host.
2. **Single prep command** — After both artifacts land in `release/`:
   ```bash
   ./scripts/prepare_release.sh
   ./scripts/prepare_rc1.sh
   ./scripts/verify_release.sh
   ./scripts/validate_public_download.sh
   ```
3. **Update `releases.json` sizes** — Fill in `"size"` fields after builds for user-facing download cards.
4. **GitHub Release** — Attach RC1 binaries + `SHA256SUMS` from `release/checksums/`; paste `release/notes/0.3.0-alpha.md`.
5. **Re-audit** — Re-run SAVE-080 checklist after blockers cleared; `RC1_REPORT.md` should then show **READY FOR PUBLIC RELEASE**.
6. **Tag** — `git tag -a v0.3.0-alpha` only after all verification scripts pass (see `RELEASE_PROCESS.md`).

---

## FINAL STATUS

### PUBLIC RELEASE BLOCKED

RC1 **metadata and infrastructure** are publication-ready. RC1 **binaries and checksums** are absent. Publishing today would deliver broken download links to end users.

**Minimum path to unblock:**

```
Windows:  scripts\build_windows.bat  +  scripts\verify_windows_installer.bat
Linux:    ./scripts/build_linux_release.sh  +  ./scripts/verify_linux_release.sh
Publish:  ./scripts/prepare_release.sh  +  ./scripts/prepare_rc1.sh
Verify:   ./scripts/verify_release.sh  +  ./scripts/validate_public_download.sh
Manual:   Clean VM install + First Run Wizard on both platforms
```

When all blockers are resolved and verification scripts pass, update this report’s final section to:

**READY FOR PUBLIC RELEASE**
