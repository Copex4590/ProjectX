# Project X — Roadmap

**Current version:** 0.3.1-beta  
**Last updated:** 2026-07-24 (SAVE-220)

## Completed — Beta track (SAVE-208 … SAVE-220)

| SAVE | Description | Status |
|------|-------------|--------|
| SAVE-208 | Vessel Database Manager page | ✅ Completed |
| SAVE-209 | Automatic vessel database synchronization | ✅ Completed |
| SAVE-210 | Backup & Restore Manager | ✅ Completed |
| SAVE-211 | Application Settings Manager | ✅ Completed |
| SAVE-212 | Plugin Framework + Installed Plugins page | ✅ Completed |
| SAVE-213 | Vessel Details Panel 2.0 | ✅ Completed |
| SAVE-214 | Vessel Timeline & Playback | ✅ Completed |
| SAVE-215 | Professional Alerts Engine | ✅ Completed |
| SAVE-216 | Analytics Dashboard | ✅ Completed |
| SAVE-217 | Intelligent Camera & AIS Link | ✅ Completed |
| SAVE-218 | Stabilization & Code Quality | ✅ Completed |
| SAVE-219 | Session Recording & Replay | ✅ Completed |
| SAVE-220 | Beta Release Preparation | ✅ Completed |

Earlier milestones (SAVE-001…SAVE-050, SAVE-200…SAVE-205 alpha release engineering) are complete; see `docs/PROJECT_STATUS.md` and `docs/CHANGELOG.md`.

## Next goals (post-beta)

1. Publish Windows `ProjectX-Setup.exe` from a native Windows build
2. Rebuild and publish Linux `.deb` / AppImage with `0.3.1-beta` metadata
3. Wire remaining camera packs into the active CameraLoader
4. Broader automated UI / packaging CI
5. Production playback backends beyond MPV (VLC / Qt / Browser)
6. Notification delivery (desktop, sound, tray)
7. Activate or replace Coming Soon AIS providers (MarineTraffic / AISHub) when ready
8. File → New Profile (multi-profile) when designed

## Beta exit criteria (draft)

- Dual-platform installers published with matching version identity
- Smoke + release audit green on Linux and Windows
- Known issues documented and accepted for beta
- No critical EventBus / thread / timer leaks on normal close path
