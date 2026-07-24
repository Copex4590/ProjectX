# SAVE-219 — CHANGELOG (short)

## Added
- **Session Recording & Replay**: one-click Record/Stop of AIS sessions into compressed `.pxsession` files
- Captures AIS/ship positions, camera link changes, alerts, playback events, timeline arrival/departure (timestamped)
- Session Manager page: list, info (size/duration/created), delete, import, export
- Replay: Play / Pause / Seek / 1×–10×; map, Vessel Details, Timeline, Alert Center, Camera Link update together

## Technical
- `SessionRecorder`, `SessionPlayer`, `SessionStorage` (`src/session/`)
- EventBus: `session.state`, `session.replay.frame`, `session.replay.alerts`
- ThemeColors on Session Manager; live AIS map updates pause during replay
