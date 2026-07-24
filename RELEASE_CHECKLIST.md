# Project X — Release Checklist

**Release target:** `0.3.1-beta`  
**Branch:** `release/0.3.1-alpha.1` (beta prep on current release branch)  
**Phase:** SAVE-201 Release Stabilization Phase 1 (audit only)  
**Rule:** No new features. Stabilization evidence only.

Use this checklist before any public test build. Mark items only after manual verification on a clean machine.

---

## Crash Safety

- [ ] Application survives AISStream disconnect / 503 / network drop without exiting
- [ ] Application survives AIS-catcher TCP drop without exiting
- [ ] Closing main window stops HybridEngine without hang or zombie process
- [ ] Unhandled exception dialog appears for GUI-thread failures (`sys.excepthook`)
- [ ] Daemon worker exceptions do not kill the Qt process (EventBus / background queues)
- [ ] Map WebEngine crash / reload does not take down the process (document if unrecoverable)

## Exception Handling

- [ ] No bare `except:` in `src/` (verified in SAVE-201 audit)
- [ ] Silent `except Exception: pass` on hot paths reviewed and ticketed (VesselSync, TimelineRecorder, ArrivalDeparture)
- [ ] EventBus handler failures are logged and do not stop other listeners
- [ ] HybridEngine AIS/RTL outer loops catch errors and continue or reconnect
- [ ] Logbook / XLSX failures cannot crash AIS ingest (known risk — see readiness report)

## Provider Recovery

- [ ] AISStream: reconnect after disconnect with bounded backoff
- [ ] AISStream: websocket closed on stop / provider disable / observation change
- [ ] AISStream: no duplicate concurrent reconnect storms
- [ ] RTL / AIS-catcher: reconnect after TCP loss
- [ ] RTL: socket timeout so stop/disable cannot block forever
- [ ] Future providers (MarineTraffic / AISHub): clearly marked not-ready; wizard cannot enable them silently
- [ ] Provider disable purges AIS-only / RTL-only vessels as designed

## Logging

- [ ] Dual logging systems documented (`app.logging_config` + `core.logger`)
- [ ] Hot-path `print()` replaced or deferred (SAVE-202)
- [ ] Default log level suitable for public alpha (`WARNING` unless `PROJECTX_DEBUG` / `PROJECTX_LOG_LEVEL`)
- [ ] Rotating file log path known to testers (`~/.local/share/Project X/logs/projectx.log`)
- [ ] `PROJECTX_OBS_FREEZE_TRACE` remains **off** by default (SAVE-P0)

## GUI Stability

- [ ] Map page: no multi-second freeze under normal Duna-scale traffic
- [ ] Switching pages (Map / Dashboard / Vessels / Settings) does not deadlock
- [ ] Wizards (First Run, AIS, RTL, Camera, Observation) cancel cleanly
- [ ] QThread workers in wizards do not outlive dialog without wait/quit policy
- [ ] Notification banner / AIS connection countdown behaves after reconnect
- [ ] Language switch does not leave stale strings on critical pages

## Memory

- [ ] Long run (2–4 h): ShipRegistry / radar_data growth bounded or documented
- [ ] No unbounded `obs_freeze.trace` growth when trace disabled
- [ ] Timeline DB / vessel DB growth acceptable for alpha (document retention gap)
- [ ] WebEngine map + optional wizard maps do not exhaust RAM on low-end hardware

## CPU

- [ ] Idle with AIS connected: CPU acceptable on reference laptop
- [ ] Map visible: marker/full refresh rates match SAVE-106 expectations
- [ ] Radar export interval does not saturate disk/CPU (known Performance Initiative item)
- [ ] Statistics auto-refresh off by default or safe when enabled

## Packaging

- [ ] Version string matches `0.3.1-beta` in About / metadata
- [ ] Runtime data dirs created without writing into source tree unexpectedly
- [ ] Hardcoded absolute paths (`/home/zoli/rtl-monitor`, etc.) documented as **blocker for public machines**
- [ ] Dependencies pinned / install instructions for alpha testers
- [ ] No secrets (API keys) shipped in repo or default config

## First Run

- [ ] Language welcome → First Run wizard path works on empty observation set
- [ ] Observation reference required before AISStream subscribe
- [ ] AIS provider configure + test connection works
- [ ] RTL wizard can complete without crashing if no dongle present
- [ ] Splash timing does not hide fatal startup errors
- [ ] Factory reset / clean profile path documented for testers

## Known Issues

Track explicitly in release notes (see `docs/reports/release_readiness.md`):

- [ ] Hardcoded HybridEngine data paths (non-portable)
- [ ] Sync logbook XLSX on AIS EventBus path
- [ ] HybridEngine threads: daemon, no `join`/`wait` on stop
- [ ] RTL socket: no timeout
- [ ] AISStream reconnect: fixed `sleep(5)`, no exponential backoff / jitter
- [ ] Dual logging + widespread `print()` diagnostics
- [ ] Silent exception swallow in background DB workers
- [ ] Performance Initiative items deferred (SAVE-P1+)

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Engineering | | | Pass / Fail |
| Test lead | | | Pass / Fail |
| Release owner | | | Go / No-Go |

**Related reports**

- `docs/reports/stabilization_audit.md`
- `docs/reports/release_readiness.md`
