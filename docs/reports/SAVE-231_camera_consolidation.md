# SAVE-231 — Camera Framework Consolidation

**Verdict: PASS**

## Goal

Unify the duplicate `camera` (user/OP) and `cameras` (catalog/packs) stacks into one architecture.

## Old vs new architecture

```mermaid
flowchart TB
  subgraph old [Before SAVE-231]
    A1[camera.Camera]
    A2[camera.CameraManager Qt CRUD]
    A3[camera.CameraRegistry OP index]
    A4[cameras.json user]
    B1[models.camera.Camera]
    B2[cameras.CameraManager catalog]
    B3[database.camera_registry]
    B4[config/cameras + packs]
    E1[engines/camera selection scoring link providers]
    A2 --> A3 --> A1
    A2 --> A4
    B2 --> B3 --> B1
    B2 --> B4
    E1 --> B2
    UI1[Dashboard Wizard] --> A2
    UI2[Map Preview Link] --> E1
  end

  subgraph new [After SAVE-231]
    C1[models.camera.Camera unified]
    C2[cameras.CameraManager Qt + catalog + packs + user]
    C3[database.camera_registry country + OP indexes]
    C4[cameras.json user]
    C5[config/cameras catalog]
    C6[config/camera_packs enabled packs]
    C7[engines/camera unchanged consumers]
    C8[engines/camera/providers one registry]
    C2 --> C3 --> C1
    C2 --> C4
    C2 --> C5
    C2 --> C6
    C7 --> C2
    C8 --> C1
    U1[Dashboard Wizard Health] --> C2
    U2[Map Preview Link Analytics] --> C2
  end
```

## Exactly one of each (confirmed)

| Component | Location |
|-----------|----------|
| CameraManager | `cameras.manager.CameraManager` / `camera_manager` |
| CameraProvider | `engines.camera.providers.base_provider.CameraProvider` |
| Provider registry | `engines.camera.providers.provider_registry` |
| Camera model | `models.camera.Camera` |
| Discovery | `cameras.loader` + `cameras.pack_manager.load_enabled_cameras` |
| Selection | `engines.camera.camera_selection_engine` |
| Preview | `playback.live_camera_workflow` + `gui.widgets.camerapreviewpanel` |

## Removed files

- `src/camera/__init__.py`
- `src/camera/camera.py`
- `src/camera/camera_manager.py`
- `src/camera/camera_registry.py`
- `src/camera/stream_test.py`
- `src/engines/camera/camera_engine.py` (dead BaseEngine stub)

## Updated module tree

```
src/models/camera.py              # unified model + aliases + user serde
src/database/camera_registry.py   # country + observation indexes
src/cameras/
  __init__.py                     # public exports
  manager.py                      # single CameraManager
  loader.py                       # catalog discovery
  pack_manager.py                 # pack enable + payload load
  stream_test.py                  # wizard connectivity (moved)
src/engines/camera/
  providers/                      # HLS/RTSP/YouTube/Snapshot
  camera_selection_engine.py
  scoring_engine.py
  link_manager.py
  …
```

## Import dependency report

```
gui.camerawizard / dashboardpage / system_health
  → cameras (Camera, camera_manager, stream_test)

gui.mappage / camerapreviewpanel / analytics / inspector
  → cameras.camera_manager

engines.camera.{selection,scoring,link}
  → cameras.manager.CameraManager
  → models.camera.Camera

engines.camera.providers
  → models.camera.Camera
  → provider_registry (idempotent register_default_providers)

cameras.manager
  → cameras.loader
  → cameras.pack_manager
  → database.camera_registry
  → models.camera
  → observation.observation_manager (user CRUD only)

Legacy package `camera` — deleted (ModuleNotFoundError confirmed)
```

No circular import crashes on the camera import set (verified).

## Verification

| Check | Result |
|-------|--------|
| Camera Wizard imports + CRUD API | PASS |
| Dashboard `by_observation` | PASS |
| Automatic selection engine | PASS (shared manager) |
| HLS provider supports/open | PASS |
| Provider registration (no duplicates) | PASS |
| Pack discovery → registry | PASS (9 pack cameras when enabled) |
| Catalog load | PASS (HU/AT) |
| Settings diagnostics import | PASS |
| EventBus link event symbols | PASS |
| Unit tests (19, excl. pytest-only gate) | PASS |
| No duplicate Camera model | PASS |
| No dead `src/camera` package | PASS |
| No circular import failure | PASS |

**Overall: PASS**

## Notes

- User cameras keep legacy JSON keys (`type`, `latitude`, …) plus canonical keys for one-file compatibility.
- Wizard aliases (`camera.type`, `.latitude`, …) are properties on the unified model.
- Enabled packs now feed the same registry as the country catalog (previously discover-only).
