# SAVE-218 — Audit Report (Stabilization & Code Quality)

**Scope:** quality/stability only — no new user features.  
**Smoke:** `APP_OK` (15 pages, MainWindow close path).

## Summary

| Metric | Value |
|--------|------:|
| Fixed issues | **18** |
| Removed files | **7** (+ empty `src/engines/hybrid/` package) |
| Net line delta (working tree vs HEAD before docs) | **+139 / −1 594** |
| New automated unit tests | **0** (full app smoke only) |
| Remaining `TODO`/`FIXME` in `src/` | **0** |

## Fixed issues (18)

1. `AISManager.stop()` + EventBus unsubscribe  
2. `RTLManager.stop()` + EventBus unsubscribe  
3. MainWindow `closeEvent` stops AIS/RTL managers  
4. Alerts GUI bridge `shutdown()` + unsubscribe  
5. Alert Center timer stop + unsubscribe on shutdown  
6. Analytics Dashboard timer stop + unsubscribe on shutdown  
7. Silent `except` → logged (`mappage` camera load)  
8. Silent `except` → logged (`alerts/gui_bridge` sinks)  
9. Silent `except` → debug-logged (`notify_hooks` prefs)  
10. Silent `except` → debug-logged (`notification_manager` prefs)  
11. Silent `except` → debug-logged (`link_manager` camera_visible)  
12. Broke `timeline` package cycle (`vessel_playback` → `timeline_recorder`)  
13. Shared camera scoring weights (`camera_match` ↔ `scoring_engine`)  
14. Named `AUTO_SWITCH_SCORE_DELTA` / `CANDIDATE_SCORE_FLOOR`  
15. Named RTL signal-quality message thresholds  
16. Alerts distance uses `geo_context.haversine_distance_km`  
17. Coverage model uses `EARTH_RADIUS_KM`  
18. Camera Preview styles migrated to `ThemeColors`

## Removed files

- `src/engines/rtl/hybrid_engine_v2.py`
- `src/engines/hybrid/helpers.py` (and empty `hybrid` package)
- `src/gui/settingspage.py` (orphaned; Dashboard hosts `PlaybackSettingsPage`)
- `src/gui/widgets/observationmapwidget.py`
- `src/gui/widgets/cameramapwidget.py`
- `src/resources/map/observation_map.html`
- `src/resources/map/camera_map.html`

## Remaining TODOs

- **Inline `TODO`/`FIXME` in `src/`:** none  
- **Planning backlog:** `docs/TODO.md` (Beta roadmap — not code debt markers)  
- **Deferred (behavior risk):** unify `camera` vs `cameras` managers; broad ThemeColors migration of wizards; defer HybridEngine import side-effects

## Notes

- Application behavior intentionally unchanged.  
- Expected sandbox AISStream / OpenGL warnings during offscreen smoke are environmental, not regressions.
