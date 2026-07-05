# Project X — Public Release Process (SAVE-078)

End-to-end workflow for the first public **Alpha** release and subsequent updates.

```
Build  →  Verify  →  Generate checksums  →  Update website  →  GitHub Release  →  Public release
```

Canonical metadata: **`release/manifest.json`**  
Website config: **`website/releases.json`** (must stay in sync)

---

## Release directory layout

```
release/
├── manifest.json          # Version, packages, checksum paths, OS requirements
├── windows/               # ProjectX-Setup.exe
├── linux/                 # AppImage + .deb
├── checksums/             # SHA256SUMS + per-file .sha256
└── notes/                 # Release notes for GitHub / distribution
```

---

## Phase 1 — Build platform packages

### Linux (Linux Mint / Ubuntu)

```bash
./scripts/build_linux_release.sh
```

Output:

- `release/linux/ProjectX-0.3.0-alpha-x86_64.AppImage`
- `release/linux/projectx_0.3.0-alpha_amd64.deb`

Verify:

```bash
./scripts/verify_linux_release.sh
```

### Windows (dual-boot native Windows)

```bat
scripts\build_windows.bat
scripts\verify_windows_installer.bat
```

Output:

- `release/windows/ProjectX-Setup.exe`

---

## Phase 2 — Prepare release folder

Run on Linux after both platform builds are copied into `release/` (or after Linux build + manual Windows artifact copy):

```bash
chmod +x scripts/prepare_release.sh scripts/generate_release_checksums.sh scripts/verify_release.sh
./scripts/prepare_release.sh
```

This script:

1. Refreshes `release/notes/` from current release notes
2. Copies artifacts to `website/downloads/windows/` and `website/downloads/linux/`
3. Generates SHA256 checksums in `release/checksums/`
4. Updates `release/manifest.json` build Python version

Generate checksums alone:

```bash
./scripts/generate_release_checksums.sh
```

---

## Phase 3 — Verify release

```bash
./scripts/verify_release.sh
./website/verify_releases.sh
```

`verify_release.sh` checks:

| Check | Description |
|-------|-------------|
| Folder structure | `release/windows`, `linux`, `checksums`, `notes`, `manifest.json` |
| Manifest validity | Required JSON keys present |
| Config sync | `manifest.json` matches `website/releases.json` |
| Artifacts | Packages exist under `release/` |
| Checksums | `.sha256` files match artifacts |
| Website paths | Download files present under `website/downloads/` |
| Website HTTP | `releases.json`, download page, release notes load |

Expected **WARN** before first build: missing `.exe` / AppImage artifacts.

---

## Phase 4 — Update website (if filenames changed)

For a new version, update only:

1. `release/manifest.json` — version, filenames, dates
2. `website/releases.json` — `latest`, platform files (must match manifest)
3. `website/releases/<website_version>.md` — user-facing notes
4. `release/notes/` — run `prepare_release.sh` to refresh copies

No HTML editing required — download links load from `website/releases.json`.

---

## Phase 5 — GitHub Release

1. Tag the repository:

```bash
git tag -a v0.3.0-alpha -m "Project X 0.3.0-alpha"
git push origin v0.3.0-alpha
```

2. Create a GitHub Release from the tag.

3. Attach artifacts:

| File | Source |
|------|--------|
| `ProjectX-Setup.exe` | `release/windows/` |
| `ProjectX-0.3.0-alpha-x86_64.AppImage` | `release/linux/` |
| `projectx_0.3.0-alpha_amd64.deb` | `release/linux/` |
| `SHA256SUMS` | `release/checksums/` |

4. Paste release notes from `release/notes/0.3.0-alpha.md` or `0.3.0-alpha-full.md`.

---

## Phase 6 — Public release

1. Upload `website/downloads/` artifacts to the web host (if not served from GitHub Releases only).
2. Publish the static website (`website/` directory).
3. Confirm download page shows correct version and links.
4. Smoke-test on clean systems:
   - **Windows:** install → First Run Wizard → map
   - **Linux Mint:** AppImage or `.deb` → menu icon → First Run Wizard

---

## Version alignment

| Field | Value (Alpha) |
|-------|----------------|
| Application | `0.3.0-alpha` (`src/version.py`) |
| Manifest | `0.3.0-alpha` |
| Website `latest` | `0.3-alpha` |
| Windows package | `ProjectX-Setup.exe` |
| Linux primary | `ProjectX-0.3.0-alpha-x86_64.AppImage` |
| Linux secondary | `projectx_0.3.0-alpha_amd64.deb` |

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `scripts/build_linux_release.sh` | Linux AppImage + .deb |
| `scripts/build_windows.bat` | Windows PyInstaller + installer |
| `scripts/prepare_release.sh` | Sync notes, website, checksums |
| `scripts/generate_release_checksums.sh` | SHA256 files only |
| `scripts/verify_release.sh` | Full public release verification |
| `scripts/verify_linux_release.sh` | Linux package contents |
| `scripts/verify_windows_installer.bat` | Windows silent install test |
| `website/verify_releases.sh` | Website release portal checks |

---

## Pre-public Alpha checklist

- [ ] Linux packages built and verified
- [ ] Windows installer built and verified on clean VM
- [ ] `./scripts/prepare_release.sh` completed
- [ ] `./scripts/verify_release.sh` passes (no FAIL)
- [ ] GitHub Release created with artifacts + SHA256SUMS
- [ ] Website download links tested
- [ ] `RELEASE_CHECKLIST.md` blockers resolved

---

## Related documentation

- `RELEASE_CHECKLIST.md` — readiness audit
- `docs/WINDOWS_INSTALLER.md` — Windows installer details
- `docs/LINUX_INSTALLER.md` — Linux package details
- `BUILD_WINDOWS.md` — Windows build pipeline
