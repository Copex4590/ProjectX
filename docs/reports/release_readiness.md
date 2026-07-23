# Project X — Release Readiness Report (SAVE-201)

**Release candidate:** `0.3.1-alpha.1`  
**Branch:** `release/0.3.1-alpha.1`  
**Date:** 2026-07-23  
**Mode:** Stabilization audit only — **no fixes implemented in SAVE-201**.

Companion artifacts:

- `RELEASE_CHECKLIST.md`
- `docs/reports/stabilization_audit.md`

---

## 1. Executive summary

Project X is **not yet ready** for an unsupervised public alpha on arbitrary machines. Core navigation/AIS monitoring works on the developer profile, but release blockers remain around **portability (hardcoded paths)**, **provider recovery quality**, **thread shutdown**, **silent background failures**, and **diagnostic `print()` / dual logging**.

**Go / No-Go recommendation:** **No-Go** for public test until Critical items in §8 are addressed (or explicitly accepted with loud release-note warnings and a developer-only tester pool).

---

## 2. Unsafe exception locations

Locations where an exception can terminate or strand **threads**, **timers**, **provider callbacks**, **EventBus**, **HybridEngine**, or **Qt signal** paths.

### 2.1 Threads (can die or hang)

| Location | Risk | Why unsafe |
|----------|------|------------|
| `engines/rtl/hybrid_engine.py` — `aisstream_worker` outer `except Exception` | **Strand / delayed recovery** | Catches, prints, `sleep(5)`, reconnects. No backoff/jitter. Inner `process_position` / EventBus work **not** wrapped per-message — a bug in publish/logbook can escape to outer handler and drop the connection cycle. |
| `engines/rtl/hybrid_engine.py` — `rtl_worker` inner `except Exception` | **Continues** | Logs via `print`; loop continues. Good survival; poor observability. |
| `engines/rtl/hybrid_engine.py` — `on_stop` | **No join** | Sets `running=False` via `BaseEngine.stop`, closes WS/TCP, but **does not `join`/`wait`** AIS/RTL threads. Daemon threads may still be in `recv`/`process_position` during teardown. |
| `engines/ais/ais_rtl_client.py` — `receive` | **Hang** | Blocking `recv` **without** `settimeout`. Disable/stop can block RTL thread indefinitely until peer closes. |
| `engines/ais/aisstream_engine.py` — `worker` | **Thread death** | `except Exception: logger.exception; break` — worker **exits permanently**; no reconnect. (Alternate engine; not MainWindow production path, but unsafe if enabled.) |
| `engines/ais/aisstream_engine.py` — `on_stop` | **No join** | Disconnects client; does not wait for worker thread. |
| `database/vessel_sync.py` — `_worker_loop` | **Silent data loss** | `except Exception: pass` — SQLite/upsert failures swallowed forever; thread lives but DB diverges. |
| `timeline/timeline_recorder.py` — `_worker_loop` | **Silent data loss** | Same pattern as VesselSync. |
| `engines/timeline/arrival_departure_engine.py` — `_worker_loop` | **Silent logic failure** | `except Exception: pass` around observe/scan — arrivals/departures can stop without signal. |
| Daemon workers generally | **No stop API** | VesselSync / TimelineRecorder / ArrivalDeparture: infinite daemon loops, **no `stop()` / poison-pill / `join`**. Process exit relies on daemon kill. |

### 2.2 Timers (Qt)

| Location | Risk | Why unsafe |
|----------|------|------------|
| `gui/mappage.py` marker/popup `QTimer` | **Unhandled slot exception** | Timer callbacks are plain slots wrapping serialize/publish. Exception in `_publish_ships` / serialize can abort that tick; Qt continues, but user sees freeze/partial update. No local try/except. |
| `gui/eventbridge.py` coalesce timer | **Partial GUI stall** | `_flush_ship_updated` emits to multiple pages; a slot exception may interrupt remaining connections depending on Qt connection type (direct). |
| `gui/notifications/ais_connection_monitor.py` countdown | **Medium** | Timer-driven purge call into HybridEngine; failure could leave countdown state inconsistent. |
| `QTimer.singleShot` sites (`mapwidget`, `mapcontroller`, `application`, `dashboard`, wizards) | **One-shot failure** | Failures are not systematically guarded; typically non-fatal but unlogged. |

### 2.3 Provider callbacks / AIS ingest

| Location | Risk | Why unsafe |
|----------|------|------------|
| `engines/ais/hybrid_ais_engine.py` — `publish_ship` | **Blocks / crashes worker** | `registry.add` + sync `eventbus.publish("ship.updated")` on AIS/RTL thread. LogbookRecorder (sync XLSX) can raise or stall; EventBus catches handler exceptions **individually**, but registry side effects before publish are unprotected. |
| `logbook/logbook_recorder.py` — `_on_ship_updated` | **Worker stall** | Sync CSV+XLSX on EventBus; exceptions would be caught by EventBus logger, but long runtime stalls ingest. |
| `ais/providers/aisstream_provider.py` — `test` | **Safe for wizard** | Broad `except Exception` returns `AISTestResult`; `finally: disconnect()`. OK for test path. |

### 2.4 EventBus

| Location | Risk | Why unsafe |
|----------|------|------------|
| `events/eventbus.py` — `publish` | **Partially safe** | Per-handler `except Exception` + `logger.exception` — **one bad listener does not kill others**. However: runs **synchronously on publisher thread** (often AIS/RTL). Handler timeout/stall ≠ exception; can still freeze ingest. |
| Subscribers without their own guards | **Stall** | EventBridge, LogbookRecorder, RTLManager — rely on EventBus catch for exceptions only. |

### 2.5 HybridEngine (production)

| Location | Risk | Why unsafe |
|----------|------|------------|
| `process_position` | **Uncaught per-call** | No try/except around FS + `publish_ship`. Exceptions bubble to worker loop handlers. |
| `save_ship_cache` | **Silent** | `except Exception: pass` — cache loss with no log. |
| `_close_ws` | **Silent** | `except Exception: pass` on close — acceptable for close, but unlogged. |
| Shared dicts AIS+RTL unlocked | **Corruption / rare crash** | Not exception handling per se; concurrent mutation can cause hard-to-reproduce faults. |

### 2.6 Qt signals / slots

| Location | Risk | Why unsafe |
|----------|------|------------|
| `app/mainwindow.py` — `ship_updated` fan-out | **UI exception** | Connected to Vessels / Dashboard / Map. Slot exceptions typically print to stderr via Qt; no app-level recovery beyond `sys.excepthook` for truly uncaught cases. |
| Wizard `QThread.finished` handlers | **Medium** | If worker `run()` raises, QThread emits error path inconsistently; several workers have **no try/except inside `run()`** (`_StreamTestWorker`, `_RTLDetectWorker`, `_RTLReceptionWorker`, `_HealthCheckWorker`). |
| `app/application.py` — main window create | **Startup abort** | `except Exception: logger.exception` then fails startup — appropriate. |

### 2.7 Relatively safe patterns (note)

- EventBus per-listener catch + log.
- AISStream provider test `finally: disconnect()`.
- `AISRtlClient.disconnect` catches `OSError`.
- Application `sys.excepthook` for GUI-thread uncaught errors.

---

## 3. Provider recovery audit

### 3.1 AISStream (production: `HybridEngine.aisstream_worker`)

| Concern | Status | Evidence |
|---------|--------|----------|
| Reconnect logic | **Partial** | Outer `while self.running` + `except Exception` → print → `sleep(5)` → `_close_ws` in `finally`. Fixed delay; **no exponential backoff / jitter**. |
| Timeout handling | **Partial** | `settimeout(1.0)` + `WebSocketTimeoutException: continue`. Good keepalive loop. Connect path uses library defaults aside from that. |
| Websocket close | **Present** | `_close_ws()` on stop, disable, observation change, loop `finally`. |
| Duplicate reconnect protection | **Weak** | Single worker thread (good). `_resubscribe_requested` breaks inner loop to resubscribe. **No** connect mutex beyond `_ws_lock`; rapid enable/disable can flap. `on_start` avoids second thread if alive. |
| Offline status events | **Present** | `eventbus.publish("ais.status", ...)`. |
| Coverage / observation gate | **Present** | Waits for reference bbox before subscribe. |

### 3.2 AISStream (alternate: `AISStreamEngine` + `AISClient`)

| Concern | Status | Evidence |
|---------|--------|----------|
| Reconnect | **Missing** | Worker breaks on first exception; no retry loop. |
| Timeout | **Missing** | `AISClient.connect` / `recv` — no `settimeout`. |
| Close | **Partial** | `disconnect()` closes WS; no guarded close; no thread join. |
| Used by MainWindow? | **No** | Production uses HybridEngine. Treat as latent hazard. |

### 3.3 AISStream (wizard test: `AISStreamProvider.test`)

| Concern | Status | Evidence |
|---------|--------|----------|
| Reconnect | N/A (one-shot test) | |
| Timeout | **Present** | connect `timeout=10`, `settimeout(8)`. |
| Close | **Present** | `finally: client.disconnect()`. |
| Duplicate | N/A | |

### 3.4 RTL / Local AIS-catcher (production: `HybridEngine.rtl_worker` + `AISRtlClient`)

| Concern | Status | Evidence |
|---------|--------|----------|
| Reconnect logic | **Partial** | On error: print, loop continues; reconnect attempts after disconnect. Port-down: sleep/retry. |
| Timeout handling | **Missing** | `AISRtlClient` socket has **no** timeout — primary stop/hang risk. |
| Socket close | **Present** | `disconnect()` closes socket; `_disconnect_rtl_client` on disable/stop. |
| Duplicate reconnect | **Weak** | Single RTL thread; `_rtl_client` replaced after disconnect. No explicit “connecting” state machine. |
| AIS-catcher process | **External** | Launcher may start subprocess; not supervised for crash restart beyond next connect attempt. |

### 3.5 Future providers (MarineTraffic / AISHub)

| Concern | Status | Evidence |
|---------|--------|----------|
| Runtime ingest | **Not implemented** | Wizard allows select then `pass` on configure (`gui/aiswizard.py`). |
| Provider ABC | `NotImplementedError` on base `AISProvider` / `AISRuntimeProvider` methods. |
| Windows | `ProviderWindow` abstract methods raise `NotImplementedError`. |
| Recovery | N/A — must remain disabled in alpha release notes. |

---

## 4. Thread / Timer shutdown audit

### 4.1 `threading.Thread`

| Component | Start | stop/quit/wait | Gap |
|-----------|-------|----------------|-----|
| `HybridEngine` AIS + RTL | `daemon=True` | `BaseEngine.stop` → `on_stop` closes IO; **no `join`/`wait`** | Missing clean join; rely on daemon + close side effects |
| `AISStreamEngine.worker` | `daemon=True` | `on_stop` disconnect only | Missing join; worker may exit on error without restart |
| `VesselSync` | daemon worker | **None** | No stop; lives until process exit |
| `TimelineRecorder` | daemon worker | **None** | No stop |
| `ArrivalDepartureEngine` | daemon worker | **None** | No stop |
| `hybrid_engine_v2` | daemon | same class of gaps | Not production-wired |

### 4.2 `QThread`

| Component | Start | stop/quit/wait | Gap |
|-----------|-------|----------------|-----|
| `gui/aiswizard.py` `_AISTestWorker` | yes | `on_leave`: `wait(1000)` only — **no `quit`/`requestInterruption`** | If test >1s after leave, thread may still run |
| `gui/camerawizard.py` `_StreamTestWorker` | yes | **No wait/quit on dialog close** found | Orphan risk if dialog closed mid-test |
| `gui/rtlsdrwizard.py` detect/reception workers | yes | Guards `isRunning` before restart; **no wait on reject/close** | Mid-test close unsafe |
| `gui/systemhealthpage.py` `_HealthCheckWorker` | yes | Prevents double start; **no wait on page destroy** | Mostly OK if parented; long live-tests can outlive navigation |

### 4.3 `QTimer`

| Component | Start/stop | Gap |
|-----------|------------|-----|
| Map marker/popup timers | started on show; **stopped on hide** | Good |
| EventBridge coalesce | single-shot | Parent `QObject` lifetime OK |
| AIS connection countdown | stop on reconnect/complete | Good |
| Notification hide timer | stop on replace/hide | Good |
| Statistics / Alert auto-refresh | start/stop with checkbox | Good |
| Assorted `singleShot` | fire-and-forget | Acceptable if callbacks are cheap/safe |

---

## 5. Logging vs `print()` — recommendations (no code changes)

### 5.1 Current logging stack

| System | Path | Default level | Role |
|--------|------|---------------|------|
| `app.logging_config.configure_logging` | stderr via `basicConfig` | `WARNING` (or env) | App startup |
| `core.logger.logger` | rotating file under `~/.local/share/Project X/logs/` | `DEBUG` | Some GUI/provider modules |
| Module `logging.getLogger(__name__)` | inherits root | mixed | HybridEngine warnings, EventBus, MainWindow |
| `print()` | stdout | always | **48** calls — mostly HybridEngine |

**Problem:** Dual systems + stdout prints → alpha testers cannot collect one coherent log; console spam under AIS load; emoji/UTF-8 prints hurt packaging logs.

### 5.2 Replacement recommendations (for SAVE-202+)

| Current | Recommended |
|---------|-------------|
| HybridEngine connection banners (`📡`, `✅`, `❌`) | `logger.info` / `logger.warning` on `engines.rtl.hybrid_engine` |
| Per-ship movement `print` blocks in `process_position` | Remove for release **or** `logger.debug` behind `PROJECTX_DEBUG` (high volume) |
| Folder-created prints | `logger.info` once |
| `camera_engine` start/stop prints | `logger.info` |
| `hybrid_engine_v2` prints | Ignore until deleted or unwired; do not ship as active |
| Silent `except Exception: pass` in VesselSync/Timeline/ArrivalDeparture | `logger.exception` at minimum |
| `save_ship_cache` silent fail | `logger.warning` |
| Unify `core.logger` + `configure_logging` | Single config: console level + rotating file; DEBUG file only when opted in |

### 5.3 Keep as-is for now

- EventBus `logger.exception` on handler failure — good pattern.
- AIS-catcher launcher warnings — already on module logger.
- SAVE-P0 freeze trace — correctly gated off by default.

---

## 6. Pattern audit cross-reference

See `docs/reports/stabilization_audit.md` for full per-file tables.

| Pattern | Count in `src/` |
|---------|----------------:|
| `TODO` | 0 |
| `FIXME` | 0 |
| bare `except:` | 0 |
| `except Exception` | 35 |
| `pass` | 19 |
| `print(` | 48 |
| `NotImplemented` | 10 |

---

## 7. Issues by severity

### Critical

1. **Hardcoded absolute data paths** in production `HybridEngine` (`/home/zoli/rtl-monitor`, `/home/zoli/Asztal/...`) — breaks public machines; wrong data root vs `app.paths`.
2. **RTL socket without timeout** — provider disable / app shutdown can hang on `recv`.
3. **HybridEngine stop without thread join** — teardown races with `process_position` / WS close.
4. **Sync logbook XLSX on `ship.updated`** (EventBus on AIS thread) — freeze / ingest stall under movers (Performance Initiative; release risk).

### High

5. **AISStream reconnect** — fixed 5s sleep; no backoff/jitter; weak flap protection.
6. **Silent `except Exception: pass`** in VesselSync / TimelineRecorder / ArrivalDeparture — invisible data/integrity loss.
7. **48× `print` diagnostics** on hot paths — unsuitable for packaged alpha logs.
8. **Dual logging configuration** — inconsistent levels (file DEBUG vs console WARNING).
9. **QThread wizards** missing systematic `quit`/`wait` on dialog close (Camera / RTL / Health).
10. **Background workers** (VesselSync / Timeline / ArrivalDeparture) have **no shutdown API**.
11. **Alternate `AISStreamEngine`** exits worker permanently on error (latent).

### Medium

12. Unlocked shared HybridEngine dicts across AIS+RTL threads.
13. `save_ship_cache` / `_close_ws` swallow errors without log.
14. Map/EventBridge timer slots lack local exception guards / metrics.
15. Future providers selectable in wizard with empty configure (`pass`).
16. Unbounded registry / radar growth (no idle TTL) — long-run memory.
17. Import-time `makedirs` / side effects in HybridEngine.

### Low

18. `NotImplementedError` on abstract provider/window APIs — expected, document only.
19. Empty `pass` on intentional narrow excepts (formatting, stream probe).
20. `hybrid_engine_v2` dead code still in tree — confusion risk.
21. Splash minimum display time may mask fast-fail perception (not a crash).

---

## 8. Prioritized stabilization roadmap — **SAVE-202**

Goal of SAVE-202: make `0.3.1-alpha.1` **safe to hand to external testers** on non-developer machines. Still **no new features**. Prefer small isolated commits.

| Order | SAVE-202 item | Addresses | Difficulty | Risk |
|------:|---------------|-----------|----------|------|
| 1 | **Portable runtime paths** — HybridEngine uses `app.paths.runtime_data_path` (or documented override); remove hardcoded `/home/zoli/...` | Critical #1 | Med | Med |
| 2 | **RTL socket timeout** + interruptible receive; ensure stop/disable unblocks | Critical #2 | Low–Med | Low |
| 3 | **HybridEngine shutdown** — signal stop, close sockets, `join` with timeout, log leftovers | Critical #3 | Med | Med |
| 4 | **Guard / defer logbook on EventBus** — minimum: catch+log and skip XLSX on hot path for alpha; full async can follow Performance P2 | Critical #4 | Med | Med |
| 5 | **AISStream reconnect policy** — exponential backoff + jitter; single-flight connect | High #5 | Med | Low–Med |
| 6 | **Replace silent worker `pass`** with `logger.exception`; optional fail counters in System Health | High #6 | Low | Low |
| 7 | **Print → logging** for HybridEngine (+ camera_engine); rate-limit ship banners | High #7 | Low–Med | Low |
| 8 | **Unify logging config** — one console+file policy for alpha | High #8 | Med | Low |
| 9 | **Wizard QThread lifecycle** — `requestInterruption`/`quit`/`wait` on reject/close for Camera/RTL/AIS/Health | High #9 | Med | Med |
| 10 | **Daemon worker stop hooks** — VesselSync / Timeline / ArrivalDeparture poison-pill + join on app exit | High #10 | Med | Med |
| 11 | Disable or quarantine **AISStreamEngine** / **hybrid_engine_v2** from accidental use; release notes for future providers | High #11 / Low #20 | Low | Low |
| 12 | Checklist dry-run on **clean Linux user account** + fill `RELEASE_CHECKLIST.md` | All | — | — |

**Explicitly deferred to Performance Initiative (not SAVE-202 blockers unless they crash):** radar 1 Hz rewrite, map HTML serialize, WAL batching (SAVE-P1+).

**Exit criteria for public alpha after SAVE-202:**

- Runs on a clean profile without `/home/zoli` paths.
- AISStream and RTL recover from kill -9 of network/catcher within ~30s without UI deadlock.
- App exit returns to shell within a few seconds (no hung join > timeout).
- Single log file captures provider errors (no reliance on stdout emoji).
- Release notes list Known Issues with workarounds.

---

## 9. Suggested SAVE-201 commit contents

Documentation only:

- branch `release/0.3.1-alpha.1`
- `RELEASE_CHECKLIST.md`
- `docs/reports/stabilization_audit.md`
- `docs/reports/release_readiness.md`

No application source changes in SAVE-201.
