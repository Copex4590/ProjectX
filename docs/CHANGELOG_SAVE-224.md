# SAVE-224 — Lazy page loading architecture

## Problem

`MainWindow.build_ui()` constructed all 16 pages during startup (~5.1 s).
Most cost was eager `refresh()` / `populate()` / RTL detection inside page constructors.

## Change

- Added `app/page_registry.py`: placeholders + one-shot materialization on first navigation.
- `DashboardPage` remains the only eagerly created page.
- All other pages are created on first `show_page(index)` / sidebar / menu navigation.
- Host signal wiring runs once in per-page binders after first create.
- EventBus → page updates only reach pages that are already loaded (first open still loads current data via existing `__init__` / `refresh()`).

Per-page `__init__` heavy work is **not** rewritten yet (deferred to later SAVE items).
Architecture only: defer construction until first visit.

## Startup timing (offscreen)

| Metric | Before | After |
|--------|--------|-------|
| `MainWindow()` ctor | ~5121 ms | **~67 ms** |
| First open Vessel Timeline | (in ctor) | ~2257 ms |
| Revisit Vessel Timeline | n/a | ~0.1 ms |
| First open Map | (in ctor) | ~358 ms |

Application is interactive in well under 1 second when startup page is Dashboard.
