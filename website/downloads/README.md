# Project X — Release downloads

Installers are organized by platform:

| Directory | Platform | Public files |
|-----------|----------|--------------|
| `windows/` | Windows installer | `ProjectX-Setup.exe`, `SHA256SUMS` |
| `linux/` | Linux release | `ProjectX.deb` (recommended), `ProjectX.AppImage`, `SHA256SUMS` |

## Publish a new release

1. Build packages with `scripts/build_linux_release.sh` and/or `scripts/build_windows.bat`.
2. Run `./scripts/prepare_release.sh` to sync artifacts and checksums.
3. Update `website/releases.json` (`latest`, platform versions, sizes).
4. Add `website/releases/<version>.md` release notes.
5. Run `website/verify_releases.sh` locally.

No HTML editing is required. Do not link to or upload `installer/linux/` for public downloads.
