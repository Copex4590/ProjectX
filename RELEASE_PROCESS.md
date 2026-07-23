# Project X — Public Release Process (SAVE-078 / SAVE-085)

End-to-end workflow for the first public **Alpha** release and subsequent updates.

```
Build  →  Verify  →  Generate checksums  →  Update website  →  GitHub Release  →  Public release
```

Canonical metadata: **`release/manifest.json`**  
Website config: **`website/releases.json`** (must stay in sync)

Public Linux releases contain **only** `ProjectX.AppImage`, `ProjectX.deb`, and `SHA256SUMS`. The `installer/linux/` tree is for **developers only** and must never be published to end users.

---

## Release directory layout

```
release/
├── manifest.json          # Version, packages, checksum paths, OS requirements
├── windows/               # ProjectX-Setup.exe + SHA256SUMS
├── linux/                 # ProjectX.AppImage, ProjectX.deb, SHA256SUMS
└── notes/                 # Release notes for GitHub / distribution
```

---

## Phase 1 — Build platform packages

### Linux (Linux Mint / Ubuntu)

```bash
./scripts/build_linux_release.sh
```

Output:

- `release/linux/ProjectX.deb` (recommended)
- `release/linux/ProjectX.AppImage` (portable / advanced)
- `release/linux/SHA256SUMS`

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
- `release/windows/SHA256SUMS` (after checksum generation)

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
3. Generates per-platform `SHA256SUMS` in `release/linux/` and `release/windows/`
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
| Folder structure | `release/windows`, `linux`, `notes`, `manifest.json` |
| Manifest validity | Required JSON keys present |
| Config sync | `manifest.json` matches `website/releases.json` |
| Artifacts | Packages exist under `release/` |
| Checksums | Platform `SHA256SUMS` files match artifacts |
| Website paths | Download files present under `website/downloads/` |
| Website HTTP | `releases.json`, download page, release notes load |

Expected **WARN** before first build: missing `.exe` / AppImage artifacts.

---

## Phase 4 — Update website (if filenames changed)

For a new version, update only:

1. `release/manifest.json` — version, dates (filenames are stable across releases)
2. `website/releases.json` — `latest`, platform versions (must match manifest)
3. `website/releases/<website_version>.md` — user-facing notes
4. `release/notes/` — run `prepare_release.sh` to refresh copies

No HTML editing required — download links load from `website/releases.json`.

---

## Phase 5 — GitHub Release

1. Tag the repository:

```bash
git tag -a v0.3.1-alpha.1 -m "Project X 0.3.1-alpha.1 First Public Test"
git push origin v0.3.1-alpha.1
```

2. Create a GitHub Release from the tag.

3. Attach **Linux** artifacts from `release/linux/`:

| File | Description |
|------|-------------|
| `ProjectX.deb` | **Recommended** Linux download (Linux Mint / Debian) |
| `ProjectX.AppImage` | Portable / advanced (no system install) |
| `SHA256SUMS` | Checksums for both Linux files |

4. Attach **Windows** artifacts from `release/windows/`:

| File | Description |
|------|-------------|
| `ProjectX-Setup.exe` | Windows installer |
| `SHA256SUMS` | Checksum for the installer |

5. Paste release notes from `release/notes/0.3.1-alpha.1.md` or `docs/RELEASE_NOTES_0.3.1_ALPHA.1.md`.

Do **not** attach `installer/linux/` or any source-tree installer scripts to public releases.

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

| Field | Value (First Public Test) |
|-------|----------------|
| Application | `0.3.1-alpha.1` (`src/version.py`) |
| Manifest | `0.3.1-alpha.1` |
| Website `latest` | `0.3.1-alpha.1` |
| Windows package | `ProjectX-Setup.exe` |
| Linux primary | `ProjectX.deb` |
| Linux portable | `ProjectX.AppImage` |

Artifact filenames are **stable**; version information lives in metadata, tags, and in-app display.

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `scripts/build_linux_release.sh` | Linux AppImage + .deb + SHA256SUMS |
| `scripts/build_windows.bat` | Windows PyInstaller + installer |
| `scripts/prepare_release.sh` | Sync notes, website, checksums |
| `scripts/generate_release_checksums.sh` | Per-platform SHA256SUMS |
| `scripts/verify_release.sh` | Full public release verification |
| `scripts/verify_linux_release.sh` | Linux package contents |
| `scripts/verify_windows_installer.bat` | Windows silent install test |
| `website/verify_releases.sh` | Website release portal checks |

---

## Pre-public Alpha checklist

See **`docs/qa/RELEASE-APPROVAL-CHECKLIST.md`** for the full reusable QA gate.

Quick summary:

- [ ] Linux packages built and verified
- [ ] Windows installer built and verified on clean VM
- [ ] `./scripts/prepare_release.sh` completed
- [ ] `./scripts/verify_release.sh` passes (no FAIL)
- [ ] RC test reports filed under `docs/qa/reports/`
- [ ] GitHub Release created with binary artifacts + per-platform SHA256SUMS
- [ ] Website download links tested
- [ ] No public links to `installer/linux/install.sh`

---

## Related documentation

- **`docs/qa/README.md`** — Release Candidate QA framework (SAVE-086)

- `docs/WINDOWS_INSTALLER.md` — Windows installer details
- `docs/LINUX_INSTALLER.md` — Linux package details
- `BUILD_WINDOWS.md` — Windows build pipeline
- `installer/README.md` — developer-only source-tree install (not for end users)
