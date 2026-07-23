# SAVE-214 — CHANGELOG (short)

## Added
- **Vessel Timeline & Playback** for the selected vessel
- Timeline panel on the map right column: Play / Pause, 1×–10×, scrubber, Live
- Chronological trail from timeline DB + live crumbs
- Map playback trail + cursor (separate from live AIS trails)
- EventBus: `vessel.playback.mode`, `vessel.playback.position`

## Notes
- Uses ThemeColors / Design System
- Live AIS updates for other vessels unchanged; selected vessel freezes only while not Live
- Existing Vessel Timeline page (arrivals/departures table) unchanged
