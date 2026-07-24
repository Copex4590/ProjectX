# SAVE-222 — CHANGELOG (short)

## Added
- **Window Management** settings section (directly under General) with:
  - Start maximized
  - Restore last window size and position
  - Automatically fit window to current monitor
  - Always center window on startup
  - Limit window size to current monitor work area
- Preference keys with sensible defaults (restore/fit/limit ON, center OFF)
- Visual verification: `docs/reports/SAVE-222_settings_ui.png`

## Changed
- Startup geometry resolved only via `WindowGeometryManager`
- Removed unused **Restore previous session layout** checkbox from Settings (preference key retained for compatibility)

## Binding
- All five Window Management checkboxes load/save through Preferences
