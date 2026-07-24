# SAVE-228 — Deferred background loading

## Summary

Heavy page data for Timeline, Statistics, Vessel Database, and Analytics now loads on a background `QThread` after the page is visible. `activate()` returns immediately; a loading label is shown until data is applied.

## Architecture

- `gui/deferred_load.py` — `DeferredDataLoader` + `make_loading_label()`
- `initialize()` — language / subscriptions only (no data)
- `activate()` — show page; start load only if cache empty
- `refresh()` — force background reload
- Stale results ignored via generation + `isValid`
- Duplicate in-flight loads prevented (`busy` guard)
- Timeline / Vessel Database table fill is chunked (`QTimer`) to keep the GUI responsive

## Verification (offscreen) — **PASS**

| Metric | Result |
|--------|--------|
| MainWindow ctor | **~69 ms** |
| Timeline `activate()` | **~9 ms** (was multi-second freeze) |
| Statistics `activate()` | **~13 ms** |
| Vessel DB `activate()` | **~12 ms** |
| Analytics `activate()` | **~15 ms** |
| Cached revisit Timeline | **~0–24 ms** |
| EventBus after close | empty |
| Threads after close | none |
| UI pulse during load | continues (event loop alive) |

First background load still takes hundreds of ms–seconds depending on data size; the UI remains navigable.
