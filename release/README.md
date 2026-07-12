# Project X — Public release layout (SAVE-078 / SAVE-085)

```
release/
├── manifest.json       # Canonical release metadata
├── windows/            # ProjectX-Setup.exe + SHA256SUMS
├── linux/              # ProjectX.deb, ProjectX.AppImage, SHA256SUMS
└── notes/              # Release notes for GitHub / website
```

Public Linux releases contain **only** the three files above under `release/linux/`. Developer tooling under `installer/linux/` is never published.

## Prepare a release

```bash
# 1. Build platform packages (on respective hosts)
scripts\build_windows.bat          # Windows
./scripts/build_linux_release.sh   # Linux

# 2. Prepare release folder, checksums, website sync
./scripts/prepare_release.sh

# 3. Verify everything
./scripts/verify_release.sh
```

See **`RELEASE_PROCESS.md`** for the full public release workflow.
