# Project X — Release Readiness v2 (SAVE-202)

**Branch:** `release/0.3.1-alpha.1`  
**Commit target:** `SAVE-202 Critical Release Stabilization`  
**Date:** 2026-07-23  
**Previous:** `docs/reports/release_readiness.md` (SAVE-201)

---

## 1. Executive summary

SAVE-202 implemented the **Critical** stabilization items from SAVE-201. Application source now resolves runtime files via `app.paths`, unblocks RTL/WebSocket I/O with timeouts, joins HybridEngine workers on stop, defers logbook XLSX off the AIS EventBus path, applies AISStream exponential backoff with single-flight connect, centralizes logging, removes hot-path `print()`, logs formerly silent exceptions, and adds stop hooks for background workers / wizard QThreads.

**GO / NO-GO recommendation:** **Conditional GO** for a **closed alpha** (known-hardware testers), provided release notes call out remaining High items. **Not yet GO** for unsupervised public distribution until High items below are accepted or fixed (especially dual HybridEngine CSV side-effects and Performance Initiative load under dense AIS).

---

## 2. Resolved Critical items

| # | SAVE-201 Critical | Resolution |
|---|-------------------|------------|
| 1 | Hardcoded `/home/zoli/...` paths | HybridEngine (+ v2) use `hybrid_runtime_dir()` / logbook `HAJOK_DIR` under `runtime_data_dir()`. AIS-catcher Windows candidate uses `%ProgramFiles%`. Post-audit: **0** absolute home/C: hits in `src/**/*.py`. |
| 2 | RTL blocking `recv` | `AISRtlClient` sets socket timeout (default 1s); timeout returns `None`; shutdown uses `shutdown`+`close`. `AISClient` connect/recv timeouts added. |
| 3 | HybridEngine stop without join | `on_stop` disables providers, closes WS/TCP, **`join`s AIS+RTL threads** (5s timeout + warning). |
| 4 | Sync XLSX on EventBus | `LogbookRecorder` only enqueues on `ship.updated`; CSV append + **background XLSX worker**; `open_logbook` regenerates synchronously on demand. |
| 5 | AISStream reconnect storms | Exponential backoff 1→60s; `_ais_connect_lock` single-flight; connect `timeout=10`, recv timeout 1s. Alternate `AISStreamEngine` also reconnects with backoff + join on stop. |

Additional SAVE-202 mandate items completed:

| Task | Status |
|------|--------|
| 6 Silent `except`/`pass` → logging | Cleared in workers + remaining close/format handlers (debug/exception). Post-audit: **0** bare silent `except → pass` in `src/`. |
| 7 `print()` → logging | **0** remaining `print(` in `src/**/*.py`. |
| 8 Central logging | `app.logging_config.configure_logging()` — console + rotating file; `core.logger` delegates. Levels via `PROJECTX_LOG_LEVEL` / `PROJECTX_DEBUG`. |
| 9 Wizard QThread cleanup | `gui/thread_utils.stop_qthread`; AIS/Camera/RTL wizards + System Health page stop/wait on leave/reject/close/hide. |
| 10 Daemon worker stop hooks | `stop()` on VesselSync, TimelineRecorder, ArrivalDepartureEngine, LogbookRecorder, LogbookManager XLSX worker; MainWindow `closeEvent` stops them before HybridEngine. |
| 11 Full re-audit | Hardcoded paths **0**, `print` **0**, silent except-pass **0**, syntax OK; smoke import paths resolve under `data/hybrid`. |

---

## 3. Remaining High issues

1. **HybridEngine still writes CSV / deli / radar / hajo on AIS thread** (Performance Initiative SAVE-P3) — XLSX is off hot path; other FS remains.
2. **Unlocked shared HybridEngine dicts** (AIS+RTL) — race risk under dual providers.
3. **No registry idle TTL** — long-run memory growth.
4. **Map full serialize / radar 1 Hz rewrite** — GUI/disk load under dense fleets (SAVE-P1/P6).
5. **SQLite connect-per-op without WAL** — VesselSync/Timeline still chatty (SAVE-P5).
6. **Future providers** (MarineTraffic/AISHub) still selectable with empty configure — must stay documented as not-ready.
7. **`.bak` files** under `src/` may still mention legacy paths — not imported; consider deleting in a later cleanup SAVE.
8. **Log directory fallback** — prefers `~/.local/share/projectx/logs`, falls back to `runtime_data_dir()/logs` if home is unwritable.

---

## 4. Regression risks

| Area | Risk | Mitigation / test |
|------|------|-------------------|
| Logbook paths | Existing user data under legacy `/home/zoli/Asztal/.../Hajók` not auto-migrated | Document manual copy or env `PROJECTX_LOGBOOK_DIR` |
| Radar/cache location | Files now under `data/hybrid/` | Update any external OBS tooling paths |
| XLSX freshness | Sheet lags CSV until background worker / open | Open logbook forces sync regenerate |
| AIS reconnect timing | Backoff may delay recovery up to 60s after repeated failures | Expected; resets to 1s after success |
| App exit | Join timeouts 5s per worker family | Watch for warnings in log if a worker sticks |
| QThread `terminate()` | Last-resort after wait timeout | Only if quit/wait fails |
| Logging init | `core.logger` import calls `configure_logging()` | Ensure Application still calls configure early (idempotent) |

---

## 5. Verification performed (SAVE-202)

- AST parse of all `src/**/*.py` — OK  
- Grep: `/home/zoli`, `C:/Program Files`, `/Users/<name>` — **0** in `.py`  
- Grep: `print(` — **0**  
- Grep: `except …: pass` silent pairs — **0**  
- Smoke (venv): HybridEngine paths → `…/data/hybrid`, `…/data/Hajók`; RTL timeout default 1.0; stop hooks present  

Manual tester checklist still required (network kill, RTL unplug, wizard cancel mid-test, clean user account).

---

## 6. GO / NO-GO

| Audience | Decision |
|----------|----------|
| Closed alpha (developers / known PCs) | **GO** after filling `RELEASE_CHECKLIST.md` on a clean profile |
| Public unsupervised download | **NO-GO** until High FS/map/SQLite items are scheduled or explicitly waived |

---

## 7. Suggested next SAVE

**SAVE-203** — Release Stabilization Phase 3 (High): portable migration notes, disable future providers in wizard UI, delete unused `.bak` / quarantine `hybrid_engine_v2`, optional HybridEngine FS writer queue (align with Performance SAVE-P3), checklist dry-run sign-off.
