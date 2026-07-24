# SAVE-221 HOTFIX-001 — CHANGELOG (short)

## Fixed
- MainWindow no longer opens at a hardcoded `1600×900`
- Startup size uses Qt available work area (~90%, centered) on first launch
- Restored `window_geometry` from preferences is validated and clamped to the visible screen

## Unchanged
- `startup_maximized` behaviour
