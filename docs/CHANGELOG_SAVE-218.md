# SAVE-218 — CHANGELOG (short)

## Stabilization
- EventBus lifecycle: AIS/RTL manager `stop()`, Alerts GUI bridge shutdown, Alert Center / Analytics unsubscribe + timer stop on close
- Dead code removed: `hybrid_engine_v2`, orphaned Settings page, unused map widgets/HTML, empty hybrid helpers
- Silent exception sinks replaced with logging; timeline package import cycle broken
- Shared camera scoring weights / named hysteresis constants; haversine via `geo_context`
- Camera Preview ThemeColors alignment

## Audit
- See `docs/reports/SAVE-218_audit.md` (18 fixes, 7 files removed, 0 remaining `TODO`/`FIXME` in `src/`)
