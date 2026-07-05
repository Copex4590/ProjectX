# Project X — Release downloads

Installers are organized by platform:

| Directory | Platform | Config key |
|-----------|----------|------------|
| `windows/` | Windows installer | `releases.json` → `windows.file` |
| `linux/` | Linux AppImage | `releases.json` → `linux.file` |

## Publish a new release

1. Copy installers into `windows/` and/or `linux/`.
2. Update `website/releases.json` (`latest`, platform versions, filenames, sizes).
3. Add `website/releases/<version>.md` release notes.
4. Run `website/verify_releases.sh` locally.

No HTML editing is required.
