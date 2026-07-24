# SAVE-222 — CHANGELOG (short)

## Startup flow (mandatory)
1. Detect current monitor (`QScreen` via cursor → widget → primary)
2. Read `QScreen.availableGeometry()` every startup (including maximized)
3. Read stored window geometry
4. Validate against the detected work area
5. Apply Window Management options
6. Show / showMaximized

## Settings UI
- **Window Management** section under General with all five behaviour checkboxes
- Hint: monitor detection is automatic; options only control behaviour on that screen
- Removed obsolete “Restore previous session layout” control

## Files
- `src/app/window_geometry.py` — WindowGeometryManager
- `src/app/mainwindow.py` / `application.py` — apply before show
- `src/gui/applicationsettingsmanagerpage.py` — Settings UI
