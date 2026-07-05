# Project X — Public release layout (SAVE-078)

```
release/
├── manifest.json       # Canonical release metadata
├── windows/            # Windows installer (ProjectX-Setup.exe)
├── linux/              # Linux AppImage and .deb packages
├── checksums/          # SHA256 checksum files (auto-generated)
└── notes/              # Release notes for GitHub / website
```

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
