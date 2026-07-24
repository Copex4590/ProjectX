# SAVE-226 — Full Startup Stabilization Report

**Date:** 2026-07-24  
**Verdict: PASS** (production-ready for startup/shutdown stability under tested scenarios)

## Method

- 10 isolated process cycles (`QT_QPA_PLATFORM=offscreen`)
- Each cycle: `MainWindow` ctor → visit Dashboard / Map / Settings / Timeline / Analytics / Alert Center / Statistics (with revisits) → ObservationWizard open/close → language emit → `close()` → EventBus / thread / Qt-message checks

## Results (10/10)

| Metric | Result |
|--------|--------|
| Cycles passed | **10 / 10** |
| Ctor time | **67–91 ms** (median ~69 ms) |
| Uncaught exceptions | **None** |
| Deleted-object / RuntimeError | **None** |
| `QObject::connect` warnings | **None** |
| WebEngine shutdown errors (captured) | **None** |
| Threads alive after close | **[]** |
| EventBus listeners after close | **{}** (cleared) |
| Lazy create counts | **Exactly 1** per visited page |
| Binder counts | **Exactly 1** per page with a binder |

## Lazy page lifecycle

| Check | Status |
|-------|--------|
| Created exactly once | **PASS** |
| Binders once | **PASS** |
| `initialize()` once | **N/A** — pages do not implement `initialize()` yet; registry calls it only on first materialize when present |
| `activate()` every visit | **PASS (registry)** — `PageRegistry.ensure()` now invokes `activate()` on every visit when implemented; no page defines it yet |

## Defects fixed in this pass

1. **PageRegistry** — `activate()` was only run at first create; now runs on every `ensure()` / navigation.
2. **EventBridge** — no EventBus unsubscribe on shutdown → added `shutdown()`.
3. **MainWindow.closeEvent** — now shuts down EventBridge, Map, Statistics (not only Alert/Analytics).
4. **MapPage / VesselDetailsPanel / StatisticsPage** — stop timers and unsubscribe EventBus handlers on shutdown.

## Remaining (non-blocking)

| Item | Severity | Notes |
|------|----------|-------|
| Pages lack `initialize()` / `activate()` bodies | Low | Architecture hooks ready; per-page data-load split is a later SAVE |
| `AIS-Catcher unavailable on localhost:10110` | Env | Expected when AIS-Catcher is not running |
| SAVE-223 responsive layout files still uncommitted | Process | Unrelated to stability |
| Full on-screen / packaging soak | Out of scope | Offscreen harness only |

## Production readiness

**PASS** — Startup stays under ~100 ms with Dashboard-only eager load; exercised lazy pages, wizard, and shutdown show no deleted-object faults, no EventBus/thread leaks after close, and clean 10-cycle repeatability.
