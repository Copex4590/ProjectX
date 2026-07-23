# SAVE-208 — CHANGELOG (short)

## Added
- **Vessel Database Manager** page (sidebar → Database Manager)
- Sections: Local Vessel Database, Synchronization, Statistics, Diagnostics, Actions
- Backend service `database/vessel_database_manager.py` with real local metrics + sync/verify/open-folder hooks

## Notes
- UI + hooks only; full remote sync arrives in a later SAVE
- Uses `ThemeColors` / Project X Design System cards and buttons
- Existing Vessel Database viewer page unchanged
