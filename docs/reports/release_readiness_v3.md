# Project X — Release Readiness v3 (SAVE-203)

**Branch:** `release/0.3.1-alpha.1`  
**Commit target:** `SAVE-203 High Priority Release Stabilization`  
**Date:** 2026-07-22  
**Previous:** `docs/reports/release_readiness_v2.md` (SAVE-202)

---

## 1. Executive summary

SAVE-203 resolved the remaining **High** items from v2: HybridEngine filesystem IO is off the AIS/RTL threads via a dedicated writer queue; SQLite uses WAL + persistent connections + batched commits; map/radar pipelines send incremental updates; future AIS providers cannot be activated (zero timers/threads/network); registry idle TTL is enforced; legacy `.bak` files removed; headless memory/stress harnesses PASS.

**GO / NO-GO recommendation:** **GO** for closed alpha and **Conditional GO** for limited public alpha, provided Medium items below remain documented. Full unsupervised public distribution can proceed after Medium checklist dry-run on clean profiles.

---

## 2. Resolved HIGH items (from v2 §3)

| # | High item (v2) | Resolution |
|---|----------------|------------|
| 1 | HybridEngine CSV / deli / radar / hajo on AIS thread | `hybrid_file_writer.HybridFileWriter` background queue; AIS/RTL only enqueue. |
| 2 | Unlocked shared HybridEngine dicts | `_state_lock` (RLock) around shared mutation / radar purge. |
| 3 | No registry idle TTL | `ShipRegistry.purge_idle` + HybridEngine radar stale purge (`REGISTRY_TTL_SECONDS=1800`). |
| 4 | Map full serialize / radar 1 Hz rewrite | Map: fingerprint + `{mode:patch\|full}` payloads; JS incremental upsert/remove. Radar: dirty-set + `radar_delta.json`; full KML ≤30s. |
| 5 | SQLite connect-per-op without WAL | `VesselDatabase` + `TimelineRegistry`: persistent conn, `journal_mode=WAL`, `synchronous=NORMAL`, batched `upsert_many` / `append_many`, VesselSync/TimelineRecorder periodic flush. |
| 6 | Future providers selectable | Filtered from `get_enabled_provider_ids` / `set_enabled_providers`; wizard checkboxes disabled; stub `start()` is no-op (never running). |
| 7 | `.bak` files under `src/` | Deleted `hybrid_engine.py.bak`, `aiscatcher.py.bak`. |
| 8 | Log directory fallback | Unchanged (Medium/ops); not a functional High blocker for SAVE-203 scope. |

---

## 3. Remaining MEDIUM items

1. **Log directory fallback** — prefers `~/.local/share/projectx/logs`, falls back to `runtime_data_dir()/logs`.
2. **Legacy path migration** — users with data under old absolute Hybrid/logbook paths need manual copy or env overrides (`PROJECTX_LOGBOOK_DIR`, etc.).
3. **XLSX lag** — logbook sheet still lags CSV until background worker / open (by design since SAVE-202).
4. **AIS reconnect backoff** — recovery may take up to 60s after repeated failures (expected).
5. **Full GUI soak** — multi-hour GUI session (map visible, dual providers) not automated; headless harness covers workers/queues/DB only.
6. **Preferences hygiene** — historically stored future-provider IDs are ignored at runtime but may still appear in raw preference JSON until next save.

---

## 4. Performance measurements

### 4.1 Memory validation (`tools/save203_memory_validation.py`)

Artifact: `docs/reports/save203_memory_validation.json`

| Metric | Result |
|--------|--------|
| Duration | 12 s @ 150 obs/s |
| Observations | 1697 |
| Registry final | 500 (bounded) |
| Vessel DB / timeline counts | 500 / 500 |
| RSS start → end | 32.35 → 33.13 MB (Δ +0.78) |
| Max queue depths | vessel=1, timeline=1, writer=2 |
| Workers alive | vessel / timeline / writer = true |
| Verdict | **PASS** |

### 4.2 Stress validation (`tools/save203_stress_validation.py`)

Artifact: `docs/reports/save203_stress_validation.json`

| Metric | Result |
|--------|--------|
| Duration | 12 s @ 250 updates/s, 300 vessels |
| Updates sent | 2798 |
| Active vessels max/final | 300 / 300 |
| CPU % avg / max | 10.37 / 13.14 |
| RSS start → end | 32.62 → 32.77 MB |
| EventBus latency p50 / p95 / p99 | 0.061 / 0.102 / 0.113 ms |
| Verdict | **PASS** |

GUI responsiveness: map incremental patch mode avoids full-fleet JSON rebuilds; marker path skips popup rewrite unless `popup_html` present. Manual GUI soak remains recommended on release hardware.

---

## 5. Regression audit (SAVE-202 → SAVE-203)

| Area | Result | Notes |
|------|--------|-------|
| Startup | OK (code) | Writer starts with HybridEngine; WAL DBs open lazily/persistently. |
| Shutdown | OK (code) | Writer flush + stop; VesselSync/TimelineRecorder join unchanged. |
| Reconnect | OK (code) | AIS backoff paths untouched. |
| Provider switching | OK (code) | Only AISStream/Local activatable; future IDs stripped. |
| Logbook | OK (code) | Still async CSV/XLSX from SAVE-202; Hybrid CSV via writer. |
| Vessel database | OK (harness) | Batched WAL upserts; counts match load. |
| Radar | OK (code) | Incremental delta + throttled compact/full exports. |
| Map | OK (code + unit) | Patch/full payloads; unit gate test updated for SAVE-106 dirty coalesce. |

Unit: `tests.test_mappage_ship_rendering` — **PASS** (6 tests).

---

## 6. GO / NO-GO

| Audience | Decision |
|----------|----------|
| Closed alpha (developers / known PCs) | **GO** |
| Limited public alpha | **Conditional GO** — document Medium items; run `RELEASE_CHECKLIST.md` on clean profile |
| Wide unsupervised public download | **GO** after Medium soak + checklist sign-off (no remaining High blockers) |

---

## 7. Suggested next SAVE

**SAVE-204** — Medium polish: preference scrub of future providers, longer GUI soak automation, optional legacy data migration helper, release checklist dry-run sign-off.
