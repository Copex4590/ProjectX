# Release checksums (legacy location)

Per-platform checksum files moved in **SAVE-085**:

| Platform | Path |
|----------|------|
| Linux | `release/linux/SHA256SUMS` |
| Windows | `release/windows/SHA256SUMS` |

Generate with:

```bash
./scripts/generate_release_checksums.sh
```

Or as part of:

```bash
./scripts/prepare_release.sh
```

Verify:

```bash
./scripts/verify_release.sh
./scripts/verify_linux_release.sh
```

This directory is no longer used for new releases.
