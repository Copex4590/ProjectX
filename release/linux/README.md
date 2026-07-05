# Linux release artifacts

| File | Format |
|------|--------|
| `ProjectX-0.3.0-alpha-x86_64.AppImage` | Primary AppImage |
| `projectx_0.3.0-alpha_amd64.deb` | Secondary Debian package |

Built by `./scripts/build_linux_release.sh`.

Checksums: `release/checksums/` (via `./scripts/generate_release_checksums.sh`).

Website copies synced by `./scripts/prepare_release.sh`.

See **`docs/LINUX_INSTALLER.md`** and **`RELEASE_PROCESS.md`**.
