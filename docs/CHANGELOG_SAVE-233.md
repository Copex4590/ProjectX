# CHANGELOG — SAVE-233

## Packaging / release

- Bake `PROJECTX_BUILD` into packaged binaries via `resources/build_stamp` (About no longer stuck on `dev`).
- Rebuild Linux `.deb` + AppImage for `0.3.1-beta` with stamp `0.3.1-beta-20260724`.
- Tighten Linux verify: stamp, version, AppStream MIT, themes, map HTML, camera packs.
- Refresh AppStream metadata (reverse-DNS component id, modern `<developer>`).
- Wire the same stamp into Windows `build_windows.bat` / `build_windows.sh` (Setup.exe still requires native Windows).
- Add `scripts/save233_verify_packaging.sh` for inventory, extract install tests, and Windows ISS static checks.
