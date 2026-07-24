# SAVE-230 — Release Readiness Audit

**Date:** 2026-07-24  
**Version:** `0.3.1-beta` (`src/version.py`)  
**Branch:** `release/0.3.1-alpha.1`  
**Readiness score:** **74 / 100**  
**Full public dual-platform release:** **FAIL**  
**Linux Alpha (after package rebuild):** **PASS\***

---

## Executive verdict

Startup, lifecycle, and progressive data-loading work (SAVE-224–229) is in good shape for a **Linux Alpha** test build. The tree is **not** ready for a full public dual-platform release: Windows installer binary is missing, current Linux artifacts are stale vs HEAD, and two architectural risks (dual camera stacks; EventBus coalesce bypass) remain unresolved.

Do **not** redesign features in this ticket. Safe cleanups from this audit are committed separately.

---

## Critical issues

| # | Issue | Area | Evidence |
|---|--------|------|----------|
| 1 | **Dual camera stacks** | Architecture | `src/camera/` (user/observation cameras) vs `src/cameras/` (geographic packs). Different `Camera` models. Map linking / analytics / scoring use packs; Dashboard wizards use user cameras. |
| 2 | **EventBus bypass of GUI coalesce** | Performance | `EventBridge` coalesces `ship.updated` (~8 Hz). `AnalyticsDashboardPage` and `VesselDetailsPanel` subscribe to the bus directly → full publish rate under load. |
| 3 | **Stale Linux packages** | Packaging | `release/linux/ProjectX.deb` / `.AppImage` older than SAVE-221–229 (progressive pipeline, lifecycle). Shipping without rebuild delivers yesterday’s binary under today’s version string. |
| 4 | **Windows installer missing** | Packaging | `release/windows/` has README only. `scripts/prepare_release.sh` / public download validation **FAIL** without `ProjectX-Setup.exe`. |

---

## Recommended improvements

1. **Complete `initialize` / `activate` on remaining pages** — Vessels, Camera, Rules, System Health, Vessel DB Manager, Backup, Installed Plugins, Session Recording still do one-shot work in `__init__` and skip revisit refresh via `PageRegistry`.
2. **Break or fence `database` ↔ `engines.timeline` import cycle** — `ship_registry` eagerly imports arrival/departure; engine lazily imports `registry`.
3. **Add packaging CI** — build/verify `.deb`, AppImage, and (when available) Windows; currently only `.github/workflows/pages.yml`.
4. **Refresh docs** — `docs/CHANGELOG.md`, `ROADMAP.md`, release notes lag SAVE-221+; SAVE-225/226 changelogs missing; `RELEASE_CHECKLIST.md` still has obsolete blockers.
5. **First-run navigation** — `firstrunwizard` uses `pages.setCurrentIndex(0)` instead of `MainWindow.show_page` (skips `activate`).
6. **Quarantine remaining dead modules on disk** — `engines/ais/aisstream_engine.py`, `runtime_providers.py`, `vessels/providers/`, `inspector/`, `engines/camera/camera_engine.py` (exports trimmed; files still present).

---

## Nice-to-have cleanup

- Route all GUI `ship.updated` consumers through `EventBridge`
- Exclude `*.placeholder` / unused `resources/icons/ship.svg` from bundles
- Authenticode (Windows) / GPG (Linux checksums)
- Central environment-variable guide for testers
- Clarify or remove empty `CameraPage` sidebar destination
- Sample plugin packaging policy (document vs bundle)

---

## Architecture (summary)

| Check | Result |
|-------|--------|
| Duplicate services | **Fail** — dual camera managers (intentional domains, unsafe naming) |
| Dead code | **Partial** — loader/export cleanup done; several obsolete modules remain |
| Obsolete startup paths | **Pass** — single `src/main.py` → `Application` → `MainWindow` |
| Lifecycle hooks | **Partial** — major pages OK; 8 pages incomplete |
| Circular imports | **Warn** — database/timeline; map controller/widget (lazy-safe) |
| Legacy page creation | **Mostly pass** — `PageRegistry` lazy; first-run index bypass |

## Performance (summary)

| Check | Result |
|-------|--------|
| UI-thread blocking at page open | **Improved** — progressive pipeline + lazy pages |
| Sync DB at startup | **Low** — observation emptiness checks only; heavy DB deferred |
| Duplicate EventBus subscriptions | **Warn** — multi-sink alerts OK; ship.updated fan-out not coalesced |
| Unnecessary timers / polling | **Acceptable** — map marker/popup, analytics/stats refresh, alert center |

## Resources / packaging / logging

- **Resources:** translations, Leaflet map, flags, branding, camera packs — present and in PyInstaller datas.
- **Logging:** rotating file under XDG / LocalAppData; env `PROJECTX_LOG_LEVEL` / prefs.
- **Linux packaging tooling:** solid (`.deb`, AppImage, uninstall, checksums, website mirror).
- **Windows:** scripts/ISS ready; **binary absent**.
- **No packaging CI.**

## Code quality markers

- `TODO` / `FIXME` / `HACK` in `src/`: **none found**
- Commented-out large legacy blocks: **not a pattern**
- “Coming Soon” UI stubs remain (intentional)

---

## Score breakdown

| Category | Score | Notes |
|----------|------:|-------|
| Architecture | 68 | Lazy + progressive solid; dual camera + EventBus topology |
| Performance | 78 | SAVE-224–229; coalesce bypass remains |
| Resources | 85 | Assets packaged correctly |
| Packaging | 55 | Tooling good; artifacts stale; Windows missing; no CI |
| Docs / config | 70 | Install guides strong; changelog/roadmap lag |
| Code hygiene | 82 | No debt markers; safe cleanups applied |
| **Overall** | **74** | Weighted release readiness |

---

## Alpha PASS / FAIL

| Gate | Result |
|------|--------|
| Linux Alpha test distribution (rebuild from HEAD first) | **PASS\*** |
| Full public dual-platform release | **FAIL** |

\*Mandatory before any Alpha binary drop: rebuild Linux packages from current HEAD with `scripts/build_linux_release.sh`, run `scripts/verify_linux_release.sh`, confirm About build id ≠ `dev`.

---

## Safe cleanups applied (this ticket)

Verified and committed separately:

1. `MainWindow` imports `PROJECT_VERSION` from `version` (no longer loads `inspector` singleton).
2. Removed unused `DeferredDataLoader`; kept `make_loading_label`.
3. `engines.ais` no longer eagerly exports dead `AISStreamEngine` / stub runtime providers.
4. AppStream `project_license`: Proprietary → **MIT**.
5. Deleted junk `src/resources/map/map.html.save`.
6. `build_linux_release.sh` stamps `PROJECTX_BUILD` (default `VERSION-YYYYMMDD`).
7. Corrected AppStream install path in `docs/LINUX_INSTALLER.md`.
