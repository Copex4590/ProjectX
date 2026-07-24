# Project X v0.3.1-beta — Release Notes

**Release:** 0.3.1-beta  
**Date:** 2026-07-24  
**Track:** SAVE-208 … SAVE-220  
**Scope of SAVE-220:** Beta preparation only (audit, docs, versioning, packaging metadata). No new user features.

---

## Újdonságok (since 0.3.0-alpha / through beta track)

- **Vessel Database Manager** — local DB info, sync controls, session statistics, diagnostics, maintenance
- **Automatic vessel DB sync** — scheduler, persisted last/next sync, EventBus, provider hook
- **Backup & Restore** — full / database / settings backup, list, restore, delete
- **Application Settings Manager** — General, AIS, Cameras, Database, Notifications, Advanced
- **Plugin Framework** — load/enable/disable plugins; Installed Plugins page
- **Vessel Details Panel 2.0** — overview, position, voyage, live status, camera, database
- **Vessel Timeline & Playback** — play/pause, speed, scrubber, trail, live mode
- **Professional Alerts Engine** — active/history, ack, clear, export, live detectors
- **Analytics Dashboard** — live charts, interval filter, CSV / PNG / PDF export
- **Intelligent Camera & AIS Link** — scoring, auto-switch, coverage zones, Camera Link panel
- **Session Recording & Replay** — `.pxsession` files, Session Manager, synchronized replay

## Javítások

- File → Exit wired; File → New Profile marked Coming Soon (not activatable)
- HybridEngine async filesystem writer; SQLite WAL + batched writes; incremental map/radar (SAVE-203)
- Critical runtime hardening (SAVE-202)
- Version identity unified to **0.3.1-beta** across app, About, installer script, manifests

## Stabilitás

- **SAVE-218** — EventBus unsubscribe on AIS/RTL stop, alerts bridge / Alert Center / Analytics shutdown, dead code removal, ThemeColors on key panels
- MainWindow `closeEvent` stops hybrid engine, AIS/RTL managers, alerts, plugins, session replay, sync/timeline workers
- Offscreen release smoke (2026-07-24): **16/16** sidebar pages load; menus navigate; **0** active QTimers after close; worker threads stop; **no** QObject destroy warnings in smoke log

## Ismert hibák

| Issue | Notes |
|-------|--------|
| Windows installer binary | `ProjectX-Setup.exe` not built on Linux hosts; build on Windows with Inno Setup |
| Linux packages on tag | Existing `.deb` / AppImage may still embed prior alpha version until rebuild |
| Coming Soon providers | MarineTraffic / AISHub not activatable |
| Coming Soon profile | File → New Profile disabled |
| Camera packs | Managed in UI; legacy loader still primary for active registry |
| Playback backends | MPV production-ready; VLC/Qt/Browser stubs |
| Residual EventBus listeners | A few process-lifetime listeners may remain until MainWindow GC after close (threads/timers clean) |
| Sandbox / headless noise | AISStream / OpenGL / dbus warnings in offscreen CI are environmental |

## Következő célok

1. Native Windows installer build + publish  
2. Rebuild Linux `.deb` + AppImage for `0.3.1-beta`  
3. Camera pack loader wiring  
4. Broader automated tests / CI packaging  
5. Notifications and additional playback backends  
6. Multi-profile (New Profile) when designed  

See also: [ROADMAP](ROADMAP.md), [BETA_READY](reports/BETA_READY.md).
