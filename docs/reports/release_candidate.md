# Project X — Release Candidate Audit (SAVE-204)

**Target release:** Project X **v0.3.1-alpha.1** — First Public Test Release  
**Branch:** `release/0.3.1-alpha.1`  
**Audited commit:** `388b493` (`SAVE-203 High Priority Release Stabilization`)  
**Date:** 2026-07-23  
**Scope:** Audit only — no feature work, no optimization, no refactoring.

---

## Recommendation

**GO WITH KNOWN ISSUES**

---

## 1. Executive summary

Runtime stabilization from SAVE-202/203 is in place. Headless/core smoke and an offscreen MainWindow start → navigate all pages → stop completed without crash or unhandled exception. Linux `.deb` / AppImage artifacts exist with checksums. **Do not announce a clean “v0.3.1-alpha.1” dual-platform public release yet:** Windows installer artifact is missing, version metadata is inconsistent (`0.3.1-alpha` vs branch `0.3.1-alpha.1` vs docs/ISS still on `0.3.0-alpha`), and two File menu actions are dead.

A first public **Linux-focused** test wave is acceptable if known issues below are disclosed and the attached checklist is completed.

---

## 2. Subsystem results

| Subsystem | Result | Evidence / notes |
|-----------|--------|------------------|
| Startup / shutdown | **PASS** | Offscreen `MainWindow` constructed; HybridEngine start + `closeEvent` stop; exit code 0. |
| Crashes / unhandled exceptions | **PASS** | No process abort; AISStream failure logged and handled (reconnect path). |
| Tracebacks in logs | **WARNING** | Handled `ERROR` + traceback when AISStream proxy/network fails in audit env; expected offline noise, not a crash. |
| Unit tests | **WARNING** | 19 tests PASS; `test_obs_freeze_trace_gate` ERROR — `pytest` not installed in `.venv`. |
| AISStream provider | **WARNING** | Enabled in prefs; live connect failed in audit network (proxy reset). Code path starts/stops; full live reconnect not proven here. |
| RTL provider | **WARNING** | Offline correctly reports AIS-Catcher unavailable (`WARNING`); live RTL hardware not present in audit env. |
| Provider enable/disable | **PASS** | Future providers filtered; `sync_enabled_providers([])` disables AIS+RTL; wizard checkboxes for MT/AISHub disabled. |
| Reconnect | **WARNING** | Code present (SAVE-202 backoff); not exercised against a live flaky network in this audit. |
| Offline mode | **PASS** | Empty enabled set → no AIS/RTL workers; Hybrid `on_stop` joins cleanly. |
| GUI pages (10) | **PASS** | Dashboard, Map, Vessels, Cameras, Vessel DB, Timeline, Statistics, Alert Center, Alert Rules, System Health — all in stack; navigated index 0–9. |
| GUI menus | **WARNING** | View/Tools/About wired. **File → New Profile** and **File → Exit** have **no handlers** (`menubar.py` vs `mainwindow.py`). |
| GUI dialogs / wizards | **PASS** with notes | About, AIS, RTL, First-run, Camera, Observation wizards/dialogs present. Future AIS providers visible but disabled. |
| Dead / stub controls | **WARNING** | Dead: File → New Profile, File → Exit. Disabled-by-design: MarineTraffic / AISHub checkboxes. Abstract `NotImplementedError` in `provider_window.py` base class only. |
| Persistence — settings | **PASS** | Preferences load (schema v1); path via preferences manager. |
| Persistence — vessel DB | **PASS** | Opens; count readable; `PRAGMA journal_mode=wal`. |
| Persistence — timeline | **PASS** | Opens; count readable; WAL. |
| Persistence — logbook | **PASS** (code) | Paths under `runtime_data_dir()/Hajók` (+ `PROJECTX_LOGBOOK_DIR`); SAVE-202 async writer retained. Live GUI open not clicked in CI. |
| Persistence — configuration | **PASS** (code) | `runtime_config_dir()` / preferences; frozen → user data. |
| Packaging — Linux | **PASS** | `release/linux/ProjectX.deb`, `ProjectX.AppImage`, uninstall script, `SHA256SUMS` present (also under `website/downloads/linux/`). |
| Packaging — Windows | **FAIL** | `release/windows/` has README only — **no `ProjectX-Setup.exe`**. Website Windows download likewise empty of installer. |
| Packaging — portable | **PASS** (design) | Linux AppImage = portable path; installed `.deb` uses menu entry. Paths: frozen → `%APPDATA%/Project X` / `~/.local/share/projectx`. |
| Packaging — installed mode | **PASS** (design) / **WARNING** (freshness) | Inno + PyInstaller scripts exist; Windows binary not built. Linux packages dated ~2026-07-20 — may predate SAVE-202/203. |
| Application data paths | **PASS** | `app.paths`: dev `repo/data`, frozen `user_data_dir()/data`; hybrid under `data/hybrid`. |
| Logging | **WARNING** | Central config OK. Audit run: RTL unavailable WARNING (OK); AISStream ERROR+traceback on connect fail (noisy if left enabled offline). |
| Release metadata — version | **FAIL** | Target **0.3.1-alpha.1** ≠ `src/version.py` **0.3.1-alpha** ≠ README/CHANGELOG/Inno **0.3.0-alpha**. |
| Release metadata — build | **WARNING** | `PROJECT_BUILD` defaults to `dev` unless `PROJECTX_BUILD` set. |
| Release metadata — git revision | **FAIL** | Not shown in About dialog; not in `version.py`. `git describe`: `v0.3.1-alpha-8-g388b493`. |
| About dialog | **WARNING** | Shows name / version / build / license; GitHub link hidden when `GITHUB_URL` empty (env default). |
| License | **PASS** | Root `LICENSE` = MIT; About uses `LICENSE_NAME`. |
| README | **FAIL** | Still advertises **0.3.0-alpha**. |
| CHANGELOG | **FAIL** | Latest section **[0.3.0-alpha]**; no 0.3.1 / alpha.1 entry. |
| Manifest / website JSON | **WARNING** | Both say `0.3.1-alpha` (not `.1`); release notes paths still point at `0.3.0-alpha*.md`. |
| Inno Setup script | **FAIL** | `MyAppVersion "0.3.0-alpha"` — stale vs app version. |

---

## 3. Task-by-task verification log

### 3.1 Complete project verification

| Check | Result |
|-------|--------|
| Clean startup | **PASS** (offscreen MainWindow) |
| Clean shutdown | **PASS** (`closeEvent` stops workers + HybridEngine) |
| No crashes | **PASS** |
| No traceback | **WARNING** (handled AISStream ERROR traceback under failed network) |
| No unhandled exception | **PASS** |

### 3.2 Providers

| Check | Result |
|-------|--------|
| AISStream | **WARNING** — not live-verified; connect error handled |
| RTL | **WARNING** — no AIS-Catcher in audit env; disable path OK |
| Enable/disable | **PASS** |
| Reconnect | **WARNING** — code only |
| Offline | **PASS** |

### 3.3 GUI

| Surface | Result |
|---------|--------|
| Every page | **PASS** (navigation smoke) |
| Every button | **WARNING** — not exhaustive click-test; dead File actions found |
| Every dialog/wizard | **PASS** (inventory + construct About) |
| Every menu | **WARNING** — dead New Profile / Exit |
| Dead controls | **WARNING** — listed above |

### 3.4 Persistence

| Store | Result |
|-------|--------|
| Settings | **PASS** |
| Vessel database | **PASS** |
| Logbook | **PASS** (path/code) |
| Timeline | **PASS** |
| Configuration | **PASS** |

### 3.5 Packaging readiness

| Mode | Result |
|------|--------|
| Windows | **FAIL** — no installer artifact |
| Linux | **PASS** — deb + AppImage + checksums |
| Portable | **PASS** (AppImage + path design) |
| Installed | **WARNING** — Linux ready; Windows build pending; rebuild after SAVE-203 recommended |
| App data paths | **PASS** |

### 3.6 Logging

| Check | Result |
|-------|--------|
| Unexpected ERROR | **WARNING** — AISStream ERROR when enabled but unreachable |
| WARNING spam | **WARNING** — RTL unavailable once per start if enabled without catcher |

### 3.7 Release metadata

| Item | Result |
|------|--------|
| Version | **FAIL** (identity mismatch vs 0.3.1-alpha.1) |
| Build number | **WARNING** (`dev`) |
| Git revision | **FAIL** (not surfaced) |
| About | **WARNING** |
| License | **PASS** |
| README | **FAIL** |
| CHANGELOG | **FAIL** |

---

## 4. Known issues (must disclose if shipping)

1. **Windows First Public Test package not available** — no `ProjectX-Setup.exe` in tree.  
2. **Version string not unified to `0.3.1-alpha.1`** — app shows `0.3.1-alpha`; docs/installer remnants at `0.3.0-alpha`.  
3. **Dead menu items:** File → New Profile, File → Exit.  
4. **About/build:** default build `dev`; no git SHA in UI.  
5. **Linux packages may be older than SAVE-202/203** — rebuild before public links if those fixes must ship in the binary.  
6. **Live AISStream/RTL + multi-hour GUI soak** not completed in this audit environment.  
7. **pytest missing** in project venv → one gate test not runnable.

---

## 5. What passed cleanly

- HybridEngine offline start/stop and provider isolation (SAVE-203).  
- SQLite WAL vessel + timeline DBs.  
- Preferences load.  
- Portable/installed path model in `app.paths`.  
- Linux release folder + website mirror artifacts + SHA256SUMS.  
- MIT license file.  
- Main window 10-page navigation smoke + orderly shutdown.

---

## 6. Final recommendation

**GO WITH KNOWN ISSUES**

Ship a **First Public Test** only with the checklist in  
`docs/reports/v0.3.1-alpha.1_first_public_test_checklist.md`,  
explicit known-issue notes, and preferably **Linux-first** until Windows installer + version metadata are aligned.
