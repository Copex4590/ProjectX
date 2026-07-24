# SAVE-234 — Windows Installer Completion

**Date:** 2026-07-24  
**Version:** `0.3.1-beta`  
**Branch:** `release/0.3.1-alpha.1`  
**Overall:** **FAIL** (blocked — native Windows build/verify required)  
**Closes SAVE-230 critical item:** *not yet* — `ProjectX-Setup.exe` still absent

---

## Executive verdict

Linux packaging is complete (SAVE-233). This host is Linux; a valid Windows PyInstaller + Inno Setup product cannot be finished here.

| Attempt | Result |
|---------|--------|
| Native Windows build | **Not run** — machine booted into Linux |
| Dual-boot Windows volume | **Mounted** — Inno Setup 6 + Python 3.12 present under `Users\Apa` |
| Wine + Windows Python PyInstaller | **FAIL** — `Qt6Core.dll` needs `icuuc.dll` (not loadable under Wine); incomplete bundle (no `qwindows.dll` / WebEngine process) discarded |
| `ProjectX-Setup.exe` in `release/windows/` | **MISSING** |

**Do not commit a PASS for SAVE-234 until the Windows one-shot script succeeds on real Windows.**

---

## Windows release checklist

| Check | Result |
|-------|--------|
| `scripts/build_windows.bat` complete | **PASS** (script ready; includes build stamp) |
| Build `ProjectX-Setup.exe` | **FAIL** — not produced |
| Version metadata (ISS `0.3.1-beta` / `0.3.1.2`) | **PASS** (script audit) |
| Icon / branding (`projectx.ico`) | **PASS** (script audit) |
| Desktop shortcut option | **PASS** (ISS task `desktopicon`) |
| Start Menu shortcut | **PASS** (ISS `{group}`) |
| Launch after install | **PASS** (ISS task `launch`) |
| Uninstall entry | **PASS** (ISS UninstallDisplay*) |
| File associations | **N/A** — none used (documented in ISS) |
| Upgrade existing install | **PASS** (ISS `UsePreviousAppDir` + verify script step) — *runtime untested* |
| Clean uninstall | **PASS** (verify script) — *runtime untested* |
| Fresh VM install / app smoke | **FAIL** — not executed |
| No missing DLLs / resources / console / exceptions | **FAIL** — not executed |

### Application smoke (pending Windows)

First launch, settings, DB creation, map, cameras, AIS, theme, translations — **not run** on this host.

---

## Deliverables (current)

| Item | Status |
|------|--------|
| Installer size | **N/A** — no exe |
| Installed file inventory | **N/A** — no install |
| Windows release checklist | This document |
| PASS / FAIL | **FAIL** |

---

## Prepared tooling (run on Windows)

Dual-boot already has **Inno Setup 6** and **Python 3.12**. After reboot into Windows:

```bat
cd C:\path\to\ProjectX
git pull
scripts\save234_windows_release.bat
```

That script builds the installer, runs fresh + upgrade + uninstall silent tests, checks stamp/theme/map/cameras, and writes `docs/reports/SAVE-234_windows_verify_log.txt`.

Then manually:

1. Interactive install → Start Menu / optional desktop / launch task  
2. First Run Wizard → confirm `%APPDATA%\Project X\config` + `data`  
3. Map, cameras, AIS, theme, language  
4. On Linux: `./scripts/prepare_release.sh` to refresh Windows checksums / website copy  

Also: `scripts\verify_windows_installer.bat` (expanded for SAVE-234).

---

## Host evidence

- Windows NTFS: `/dev/nvme0n1p3` (mounted during investigation)  
- `Program Files (x86)\Inno Setup 6\ISCC.exe` present  
- Prefetch shows prior `PROJECTX-SETUP.EXE` / `PROJECTX.EXE` runs on that Windows install  
- `%APPDATA%\Project X\` still has prior `config` / `data` from earlier Windows sessions  

---

## PASS / FAIL

**FAIL** — Windows installer binary and verification not completed on this Linux session.
