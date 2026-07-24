# CHANGELOG — SAVE-239

## Fully automated cross-platform release synchronization

- New `scripts/sync_windows_installer.py`:
  - `publish` — upload `ProjectX-Setup.exe` + `SHA256SUMS` to GitHub Release tag `v<manifest.version>` (idempotent `--clobber`)
  - `fetch` — download the version-matched installer when missing locally; verify SHA256 when `SHA256SUMS` is available
- Windows build (`build_windows.bat` / `.ps1`) publishes automatically after a successful installer build
- `prepare_release.sh` and `verify_windows_release.sh` auto-fetch before requiring a local `.exe`
- Clear actionable errors when `gh`/auth/release assets are unavailable
- Opt-out: `PROJECTX_SKIP_WINDOWS_PUBLISH=1`
