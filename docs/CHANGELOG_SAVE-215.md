# SAVE-215 — CHANGELOG (short)

## Added
- **Professional Alerts Engine** with live edge detection (area, arrival/departure, speed, anchored, AIS lost, camera offline, DB sync failed)
- Enable/disable system rules, priority, timestamp, acknowledge, history
- Alerts panel: Active / History tabs, search & filters, Clear, Export (CSV)
- EventBus: `alerts.fired`, `alerts.acknowledged`, `alerts.cleared`, timeline arrival/departure bridge
- Notification API preparation (`DesktopBannerSink` + future sink hooks)

## Notes
- Uses ThemeColors / Design System on Alert Center
- Existing Alert Rules page CRUD preserved
- Live AIS path unchanged (queue + worker)
