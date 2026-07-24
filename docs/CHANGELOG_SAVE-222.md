# SAVE-222 — CHANGELOG (short)

## Added
- **Window Management** settings section (General area): Start maximized, Restore last size/position, Auto-fit, Always center, Limit to monitor work area
- Preference keys with sensible defaults for existing users (restore/fit/limit ON, center OFF)

## Changed
- Startup geometry resolved only via `WindowGeometryManager` (monitor work area, multi-monitor aware)
- MainWindow applies the configured priority: maximized → restore/fit → 90% fallback → center
