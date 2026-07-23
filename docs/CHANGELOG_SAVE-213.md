# SAVE-213 — CHANGELOG (short)

## Added
- **Vessel Details Panel 2.0** (`src/gui/widgets/vessel_details_panel.py`)
- Sections: Overview, Position, Voyage, Vessel, Live Status, Camera, Database
- Map side panel with ScrollArea + ThemeColors
- Auto-refresh from ShipRegistry / EventBus (`ship.updated`) and vessel DB sync events
- Photo / camera preview placeholders; missing fields show "—"

## Notes
- Existing Vessel Card (HTML popup) system unchanged
- Live camera playback remains in CameraPreviewPanel
- No remote web lookups in this ticket
