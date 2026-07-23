# SAVE-217 — CHANGELOG (short)

## Added
- **Intelligent Camera ↔ AIS Link**: auto-assign best camera by distance, FOV, and direction
- Auto camera switch when the vessel leaves coverage; Manual Override with alternatives
- Camera states: Online / Offline / Busy / Preferred
- Map coverage zones (toggle) and ship↔camera link visualization
- Camera Link panel: active camera, alternatives, score explanation, Auto/Manual

## Technical
- `CameraScoringEngine`, `CameraCoverageModel`, `IntelligentCameraLinkManager`
- EventBus: `camera.link.changed`, `camera.link.mode`, `camera.coverage.toggled`
- ThemeColors on Camera Link panel; Camera Preview auto path unchanged
