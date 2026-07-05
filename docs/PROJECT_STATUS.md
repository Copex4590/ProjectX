# Project X — Project Status

**Version:** 0.3.0-alpha  
**Last updated:** 2026-07-05 (SAVE-050)

## Milestone completion: SAVE-001 → SAVE-050

| SAVE | Description | Status |
|------|-------------|--------|
| SAVE-001 | Project initialization | ✓ |
| SAVE-002 | Map communication layer | ✓ |
| SAVE-003 | MapWidget update interface | ✓ |
| SAVE-004 | Ship interpolation foundation | ✓ |
| SAVE-005 | Registry interpolation support | ✓ |
| SAVE-006 | Faster map refresh (5 FPS) | ✓ |
| SAVE-007 | Vessel information popup | ✓ |
| SAVE-008 | Custom ship SVG map marker | ✓ |
| SAVE-009 | Hybrid migration checkpoint | ✓ |
| SAVE-010 | Hybrid Engine integrated startup | ✓ |
| SAVE-011 | Professional Vessel Information Card | ✓ |
| SAVE-012 | Complete Vessel Card data pipeline | ✓ |
| SAVE-013 | Camera Manager framework | ✓ |
| SAVE-014 | Automatic Camera Selection Engine | ✓ |
| SAVE-015 | Camera Preview Panel integration | ✓ |
| SAVE-016 | Camera Provider Framework | ✓ |
| SAVE-017 | Production-ready HLS Provider | ✓ |
| SAVE-018 | Playback Backend Framework | ✓ |
| SAVE-019 | Playback Preferences | ✓ |
| SAVE-020 | MPV launch configuration | ✓ |
| SAVE-021 | First Live Camera workflow | ✓ |
| SAVE-023 | Camera metadata extension | ✓ |
| SAVE-024 | Camera Diagnostics & Health Engine | ✓ |
| SAVE-025 | Project X Inspector | ✓ |
| SAVE-026 | Official Hungary Camera Pack | ✓ |
| SAVE-027 | Camera Pack Manager | ✓ |
| SAVE-028 | Playback Settings page | ✓ |
| SAVE-029 | Camera Diagnostics panel | ✓ |
| SAVE-030 | Project X 0.2 RC1 | ✓ |
| SAVE-031 | Circular import fix | ✓ |
| SAVE-032 | Vessel Database Framework | ✓ |
| SAVE-033 | ShipRegistry Vessel Database sync | ✓ |
| SAVE-034 | Vessel Database Viewer | ✓ |
| SAVE-035 | Advanced Vessel Search & Filters | ✓ |
| SAVE-036 | Vessel Photo Framework | ✓ |
| SAVE-037 | Vessel Photo Provider Framework | ✓ |
| SAVE-038 | Vessel Photo integration | ✓ |
| SAVE-039 | Vessel Flag Framework | ✓ |
| SAVE-040 | Vessel Flag integration | ✓ |
| SAVE-041 | Vessel Timeline Framework | ✓ |
| SAVE-042 | Automatic Timeline Recording | ✓ |
| SAVE-043 | Arrival/Departure Detection Engine | ✓ |
| SAVE-044 | Vessel Timeline Viewer | ✓ |
| SAVE-045 | Vessel Statistics Framework | ✓ |
| SAVE-046 | Statistics Dashboard | ✓ |
| SAVE-047 | Alert Rules Engine | ✓ |
| SAVE-048 | Alert Center | ✓ |
| SAVE-049 | Alert Rules Management Center | ✓ |
| SAVE-050 | Project X 0.3 Alpha Release | ✓ |

## Current module list

### Application shell

| Module | Path | Status |
|--------|------|--------|
| Entry point | `src/main.py` | Production |
| Application | `src/app/application.py` | Production |
| Main window | `src/app/mainwindow.py` | Production |
| Event bridge | `src/gui/eventbridge.py` | Production |

### GUI pages (sidebar)

| Page | Path | Status |
|------|------|--------|
| Dashboard | `src/gui/dashboardpage.py` | Production |
| Live Map | `src/gui/mappage.py` | Production |
| Vessels | `src/gui/vesselspage.py` | Production |
| Cameras | `src/gui/camerapage.py` | Production |
| Vessel Database | `src/gui/vesseldatabasepage.py` | Production |
| Vessel Timeline | `src/gui/vesseltimelinepage.py` | Production |
| Statistics | `src/gui/statisticspage.py` | Production |
| Alert Center | `src/gui/alertcenterpage.py` | Production |
| Alert Rules | `src/gui/rulespage.py` | Production |

### GUI widgets & settings

| Module | Path | Status |
|--------|------|--------|
| Map widget | `src/gui/widgets/mapwidget.py` | Production |
| Camera preview | `src/gui/widgets/camerapreviewpanel.py` | Production |
| Playback settings | `src/gui/settings/playbacksettings.py` | Module-ready |
| Camera diagnostics | `src/gui/settings/cameradiagnosticspanel.py` | Module-ready |
| Connection panel | `src/gui/connectionpanel.py` | Production |
| Sidebar | `src/gui/sidebar.py` | Production |

### Monitoring engines

| Module | Path | Status |
|--------|------|--------|
| Hybrid engine | `src/engines/rtl/hybrid_engine.py` | Production |
| AIS catcher launcher | `src/engines/ais/ais_catcher_launcher.py` | Production |
| Ship registry | `src/database/ship_registry.py` | Production |
| Event bus | `src/events/eventbus.py` | Production |

### Camera & playback

| Module | Path | Status |
|--------|------|--------|
| Camera manager | `src/cameras/manager.py` | Production |
| Camera loader | `src/cameras/loader.py` | Production |
| Pack manager | `src/cameras/pack_manager.py` | Production |
| Selection engine | `src/engines/camera/camera_selection_engine.py` | Production |
| Providers | `src/engines/camera/providers/` | Production (HLS), stubs |
| Playback backends | `src/engines/playback/backends/` | MPV production, stubs |
| Live workflow | `src/playback/live_camera_workflow.py` | Production |
| Diagnostics engine | `src/engines/camera/diagnostics/` | Production |

### Vessel data

| Module | Path | Status |
|--------|------|--------|
| Vessel database | `src/database/vessel_database.py` | Production |
| Vessel sync | `src/database/vessel_sync.py` | Production |
| Photo manager | `src/vessels/photo_manager.py` | Production |
| Flag manager | `src/vessels/flags/flag_manager.py` | Production |
| Photo providers | `src/vessels/providers/` | Local production, stubs |

### Timeline

| Module | Path | Status |
|--------|------|--------|
| Timeline manager | `src/timeline/timeline_manager.py` | Production |
| Timeline recorder | `src/timeline/timeline_recorder.py` | Production |
| Arrival/departure | `src/engines/timeline/arrival_departure_engine.py` | Production |

### Statistics

| Module | Path | Status |
|--------|------|--------|
| Statistics manager | `src/statistics/statistics_manager.py` | Production |

### Alerts

| Module | Path | Status |
|--------|------|--------|
| Alert manager | `src/alerts/alert_manager.py` | Production (API only) |
| Alert registry | `src/alerts/alert_registry.py` | Production |

### Inspector

| Module | Path | Status |
|--------|------|--------|
| Inspector | `src/inspector/inspector.py` | Headless API |

## Subsystem status summary

| Subsystem | Maturity | Notes |
|-----------|----------|-------|
| AIS / Hybrid monitoring | Alpha | Hardcoded paths; production on target host |
| Live map | Alpha | Leaflet + WebEngine; 5 FPS updates |
| Vessel database | Alpha | SQLite sync from registry |
| Timeline | Alpha | Auto-recording + arrival/departure |
| Statistics | Alpha | Cached read-only aggregates |
| Alert engine | Alpha | Evaluation API; no auto-hooks |
| Camera selection | Alpha | Legacy loader active |
| Camera packs | Alpha | Managed, not yet loaded |
| Playback | Alpha | MPV production; others stubs |
| Diagnostics | Alpha | Engine complete; panel not in sidebar |
| Inspector | Alpha | Programmatic only |

## Remaining work before Beta

1. **Camera packs integration** — load pack cameras into active registry
2. **Real streams** — replace Hungary placeholder URLs
3. **Alert automation** — hook evaluation to timeline and monitoring events
4. **Notifications** — desktop alerts, sound, tray icon
5. **Settings navigation** — Playback Settings and Camera Diagnostics in sidebar
6. **Inspector UI** — GUI page or CLI tool
7. **Playback backends** — VLC, Qt, Browser production implementations
8. **Deployment** — configurable paths, environment profiles
9. **Testing** — automated unit and integration test suite
10. **Packaging** — Linux AppImage, Windows installer, macOS bundle

## Known limitations

- Alert rules do not auto-evaluate from live monitoring (manual test and API only)
- No notification delivery system
- Camera packs not wired to CameraLoader
- Playback Settings and Camera Diagnostics not in main navigation
- Inspector has no GUI entry point
- Menu bar actions are placeholders
- Hybrid Engine deployment paths are environment-specific
- MPV is the only fully functional playback backend
- Windows and macOS are supported but not primary test targets

## Release verification (SAVE-050)

| Check | Result |
|-------|--------|
| `python3 -m compileall src` | ✓ Pass |
| Application startup (offscreen) | ✓ Pass (9 pages) |
| Circular imports | ✓ None detected |
| Missing resources | ✓ None (map, icons, config) |
| Lint (F401/F841) | ✓ Resolved |
