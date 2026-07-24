# Beta Ready Report — Project X 0.3.1-beta

**Ticket:** SAVE-220  
**Date:** 2026-07-24  
**Branch context:** release track toward `0.3.1-beta`  
**Scope:** Beta preparation only — no new product features; no intentional behavior changes.

---

## ✔ Build

| Check | Result | Notes |
|-------|--------|-------|
| `python -m compileall src` | **PASS** | No syntax errors |
| Import smoke (core GUI + engines + session + plugins) | **PASS** | Modules load under `PYTHONPATH=src` |
| Version source | **PASS** | `src/version.py` → `0.3.1-beta` |
| Windows Inno metadata | **PASS** | `MyAppVersion "0.3.1-beta"`, numeric `0.3.1.2` |
| Linux package version source | **PASS** | `scripts/build_linux_release.sh` reads `PROJECT_VERSION`; AppImage now gets `VERSION=` env |
| Native Windows PyInstaller + Inno | **N/A (this host)** | Requires Windows; scripts present (`scripts/build_windows.*`) |
| Linux PyInstaller + `.deb` / AppImage rebuild | **PENDING publish** | Tooling present (`dpkg-deb`, `mksquashfs`); rebuild required so artifacts match beta |

---

## ✔ Smoke Test

Environment: `QT_QPA_PLATFORM=offscreen`, `QTWEBENGINE_DISABLE_SANDBOX=1`, `.venv`, `PYTHONPATH=src`.

| Check | Result |
|-------|--------|
| MainWindow start | **PASS** |
| Sidebar pages **0–15** (16 total) | **PASS** — all instantiate and switch |
| Menu View → Dashboard / Map | **PASS** (indices 0 / 1) |
| Menu Tools → Settings | **PASS** (index 12) |
| Close path | **PASS** — `APP_OK` |
| Expected env noise | AISStream / OpenGL / dbus (sandbox) — not treated as product failure |

---

## ✔ Release Audit

| Item | Result | Evidence |
|------|--------|----------|
| Every sidebar page loads | **PASS** | 16/16 `PAGE_OK` |
| Menu points work | **PASS** | File/View/Tools/Help present; Exit/About/Settings/Dashboard/Map wired; New Profile disabled (Coming Soon) |
| Missing imports | **PASS** | compileall + import smoke |
| Circular imports (startup path) | **PASS** | MainWindow and page stack import cleanly |
| RuntimeError on smoke path | **PASS** | None observed |
| QObject warnings | **PASS** | 0 QObject destroy messages in smoke handler |
| Console exceptions (app logic) | **PASS** | No unhandled GUI exceptions; AISStream fail is env/network |
| EventBus leak | **PASS with note** | Worker/page unsubscribes on close; few process-lifetime listeners may remain until window GC (documented) |
| Leftover threads | **PASS** | After close: `MainThread` only |
| Leftover timers | **PASS** | Active `QTimer` count **0** after close |

---

## ✔ Documentation

| Document | Status |
|----------|--------|
| `README.md` | Updated for beta (overview, features, architecture, install, plugins, session, analytics, camera AI, alerts, backup, database) |
| `docs/ROADMAP.md` | Created — SAVE-208…SAVE-220 marked completed |
| `docs/RELEASE_NOTES_v0.3.1-beta.md` | Created |
| `docs/CHANGELOG.md` | Updated with SAVE-220 / `0.3.1-beta` |
| `docs/CHANGELOG_SAVE-220.md` | Created |
| Installer docs / release manifest / website `releases.json` | Version bumped to `0.3.1-beta` |

---

## ✔ Packaging

| Platform | Artifact | Status |
|----------|----------|--------|
| **Windows** | Build scripts | Ready (`build_windows.bat` / `.ps1` / `.sh`) |
| **Windows** | Installer script | Version `0.3.1-beta` in `projectx.iss` |
| **Windows** | `ProjectX-Setup.exe` | **Not produced on this Linux host** — build on Windows |
| **Windows** | Startup / uninstall | Documented in `docs/WINDOWS_INSTALLER.md`; verify after native build |
| **Linux** | Build script | `scripts/build_linux_release.sh` |
| **Linux** | AppImage | Packaging path OK; **rebuild** to embed `0.3.1-beta` (`VERSION` env now set) |
| **Linux** | DEB | Control `Version:` from `PROJECT_VERSION`; **rebuild** required |
| **Linux** | Startup | Menu entry via `.desktop` in deb; AppImage via `AppRun` |

---

## ✔ Known Issues

1. Windows installer binary missing until native Windows build  
2. Published Linux packages must be rebuilt for beta version string  
3. Coming Soon: MarineTraffic, AISHub, File → New Profile  
4. Camera packs managed but legacy loader still primary  
5. Non-MPV playback backends are stubs  
6. Residual EventBus listeners possible until MainWindow GC (threads/timers clean)  
7. Offscreen/sandbox OpenGL and AISStream connection errors are environmental  

---

## ✔ Recommendation

**READY FOR BETA** — with packaging caveats.

- Application identity, docs, roadmap, and release audit are in place for **v0.3.1-beta**.  
- **Do not** announce dual-platform download completeness until:
  1. Linux `.deb` + AppImage are rebuilt from this tree, and  
  2. Windows `ProjectX-Setup.exe` is built and smoke-tested on Windows.  

Until then, treat this as **beta-ready source / metadata**, with Linux binary refresh as the next packaging step.
