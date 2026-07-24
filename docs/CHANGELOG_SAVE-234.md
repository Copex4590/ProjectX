# CHANGELOG — SAVE-234

## Packaging / release (in progress — Windows binary pending)

- Add `scripts/save234_windows_release.bat` one-shot build + silent install/upgrade/uninstall verification.
- Expand `scripts/verify_windows_installer.bat` for build stamp, theme, map HTML, camera packs, and upgrade step.
- Align `scripts/build_windows.ps1` with build-stamp + expanded bundle checks.
- Inno Setup: `UsePreviousAppDir` / group / tasks for upgrades; document no file associations.
- Report: `docs/reports/SAVE-234_windows_installer.md` — **FAIL** until native Windows produces `ProjectX-Setup.exe`.
