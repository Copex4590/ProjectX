# SAVE-216 — CHANGELOG (short)

## Added
- **Analytics Dashboard** (sidebar): active vessels, ship-type mix, speed distribution, hourly traffic, common routes, provider / camera / alert statistics
- Line, Bar, and Pie charts (ThemeColors)
- Live refresh via EventBus + timer; time-interval selector (1h / 6h / 24h / 7d / 30d)
- Export CSV, PNG, and PDF

## Notes
- Existing Statistics Dashboard (SAVE-046) preserved
- Aggregation lives in `src/analytics/`; UI in `src/gui/analyticsdashboardpage.py`
