# SAVE-108 — Global Globe Architecture

**Status:** Draft — awaiting architectural review  
**Version:** 1.0  
**Project:** Project X  
**Prerequisite:** SAVE-107 (Storage) — COMPLETE  
**Related:** [GEO Architecture](GEO_ARCHITECTURE.md), [UI 2.0 Master Architecture](../UI_2_0_MASTER_ARCHITECTURE.md)

---

## 1. Purpose

Replace Project X’s **flat 2D map** with a **true global visualization architecture** suitable for worldwide AIS monitoring.

The globe is not a cosmetic upgrade. It is a new **Map Engine layer** that:

- Preserves the existing Python orchestration model (`MapController` → `MapWidget` → bridge).
- Replaces only the rendering engine inside the WebEngine surface.
- Aligns visual geography with the existing **GeoContext** great-circle model.
- Supports observation coverage, ship tracking, and wizard pick flows at planetary scale.

**No implementation begins until this document is approved.**

---

## 2. Problem statement

### 2.1 Current state

| Aspect | Today |
|--------|--------|
| Engine | Leaflet 1.9.4 in `src/resources/map/map.html` |
| Host | Qt WebEngine (`MapWidget`) |
| Tiles | OpenStreetMap raster CDN (network required) |
| Projection | Web Mercator flat map |
| Coverage | `L.circle` (planar; inaccurate at scale/high latitude) |
| Viewport | Clamped lat −60…75; `worldCopyJump` |
| 3D / globe | None |

Python owns data and orchestration. JavaScript owns rendering. This separation works and must be preserved.

### 2.2 Why flat map is insufficient

1. **Global monitoring** — AIS traffic spans oceans and hemispheres; a flat map distorts scale and continuity at world view.
2. **Coverage accuracy** — Observation radius is defined in kilometres on a sphere (`GeoContext` Haversine). Leaflet `L.circle` is planar.
3. **User mental model** — “Worldwide AIS monitoring” implies a globe, not a stretched Mercator sheet.
4. **Future features** — Great-circle routes, long-range bearing lines, multi-hemisphere operations, and satellite-style overviews fit naturally on a globe.

### 2.3 What must not break

- Single map surface (UI 2.0 Phase 2 — no return to multiple map widgets).
- `GeoContext` as geographic authority (see GEO Architecture).
- Ship update pipeline: registry → EventBridge → `MapPage` → `MapController` → JS.
- Observation point markers and reference coverage semantics.
- Location pick mode for observation and camera wizards.
- Theme (`colors.css`) and Python-side i18n for overlays/popups.
- Offline Leaflet bundle policy (engine assets bundled; imagery strategy TBD).

---

## 3. Design principles

1. **Thin Python, thick engine** — Python serializes domain objects; the Map Engine renders them. No rendering logic in Python.
2. **Stable bridge contract** — `MapWidget` calls a fixed set of JS entry points. The engine behind `map.html` is swappable.
3. **GeoContext remains authoritative** — Distance, bearing, coverage checks, and AIS bounding boxes stay in Python. The globe **displays** what GeoContext already computes.
4. **Geodesic visualization** — Coverage circles, trails, and pick geometry use geodesic math in the engine, consistent with Haversine in Python.
5. **One map controller** — `MapController` remains the sole owner of map UX (navigation, pick mode, observation refresh).
6. **Progressive delivery** — Phased rollout behind the same contract; no big-bang rewrite.
7. **Offline-first assets** — Engine JavaScript/CSS bundled like Leaflet today; imagery policy decided explicitly (§8).
8. **No duplicate map stacks** — Legacy `observation_map.html`, `camera_map.html`, and unused widgets are retired after globe pick modes exist.

---

## 4. Target architecture

```
Application (MainWindow / MapPage)
        │
        ▼
MapController          ← orchestration, pick sessions, observation refresh
        │
        ▼
MapWidget              ← QWebEngineView + QWebChannel bridge (unchanged role)
        │
        ▼
Map Engine (JS)        ← NEW: Globe renderer (replaces Leaflet internals)
        │
        ├── Imagery layer
        ├── Ship layer (billboards / paths)
        ├── Observation layer (markers + geodesic coverage)
        ├── Pick overlay layer
        └── Popup / HTML overlay host
```

### 4.1 Layer responsibilities

| Layer | Responsibility | Changes in SAVE-108 |
|-------|----------------|---------------------|
| **MapPage** | Ship serialization, update timers, coverage filter | Minimal; optional globe-specific fields later |
| **MapController** | Pick mode, page navigation, observation payload | Extend `PickMode` (heading); no engine knowledge |
| **MapWidget** | Load HTML, run JS, bridge signals | Load globe engine; same public methods |
| **Map Engine (JS)** | All rendering | **New implementation** |
| **GeoContext** | Distance, bearing, coverage, AIS bbox | Unchanged |
| **observation_manager** | Points, reference, radius | Unchanged |

### 4.2 Map Engine abstraction

Introduce a logical **Map Engine** module (implemented in JS, specified here):

```
resources/map/
    map.html              ← entry shell (loads engine + theme)
    engine/
        contract.js       ← documents/enforces entry-point API
        globe/            ← globe implementation (Phase B+)
    leaflet/              ← retired after migration (Phase F)
    theme link            ← ../theme/colors.css (unchanged)
```

Python continues to load `map.html`. The HTML shell delegates to the active engine.

---

## 5. Bridge contract (frozen interface)

These JS functions are called from `MapWidget` today and **must remain stable** across the Leaflet → Globe migration.

| Entry point | Input | Purpose |
|-------------|-------|---------|
| `updateShips(list)` | Serialized ships (light/full) | Markers, trails, popups |
| `updateObservationPoints(points)` | OP list with `coverage_radius_km`, `reference` | Markers + reference coverage |
| `clearObservationPoints(message)` | Empty-state message | Clear OP layers |
| `beginLocationPick(message)` | Translated overlay text | Enable click-to-pick |
| `endLocationPick()` | — | Disable pick |
| `setPickMarker(lat, lon)` | WGS84 | Show pick preview |
| `focusShip(mmsi)` | — | Fly-to vessel + open popup |
| `resetMapToWorldView()` | — | Default planetary view |

**QWebChannel bridge (Python ← JS):**

| Slot | Purpose |
|------|---------|
| `bridge.reportLocation(lat, lon)` | Location pick result |
| `bridge.openLogbook(mmsi)` | Vessel popup action |

No globe-specific types cross the bridge in Phase A–C. Latitude/longitude remain WGS84 degrees.

---

## 6. Globe engine selection (decision required before Phase B)

Architecture recommends **evaluating three candidates** in a spike (Phase A2 — design only, no production code):

| Candidate | Pros | Cons |
|-----------|------|------|
| **CesiumJS** | Mature globe, geodesic primitives, entity API, OSS (Apache 2) | Large bundle; ion imagery licensing if used |
| **MapLibre GL JS + globe projection** | Lighter; vector tiles; modern | Globe support newer; less maritime tooling |
| **Three.js custom globe** | Full control; smallest dependency choice | Highest implementation cost |

**Recommendation for review:** CesiumJS as primary candidate — best fit for geodesic coverage, camera fly-to, and entity-based AIS markers at global scale.

Final selection is a **Phase A gate**, not this document’s assumption.

---

## 7. Rendering model

### 7.1 Ships (AIS)

| Element | Flat (today) | Globe (target) |
|---------|--------------|----------------|
| Position | `L.marker` + divIcon | Entity/billboard at lat/lon/alt=0 |
| Heading | CSS rotate on ▲ | Billboard rotation or model-aligned |
| Trail | `L.polyline` (max 50 pts) | Geodesic path / polyline on ellipsoid |
| Popup | Leaflet popup + server HTML | Screen-space HTML overlay anchored to entity |
| Stationary | 10 px circle | Scaled point/billboard |

Serialization from `MapPage` (`_serialize_ship_marker`, `_serialize_ship`) remains unchanged in early phases.

### 7.2 Observation points

| Element | Flat (today) | Globe (target) |
|---------|--------------|----------------|
| Markers | Green/red divIcons | Color-coded billboards |
| Coverage | `L.circle` on reference OP only | **Geodesic circle** (ellipsoid), reference OP only |
| Viewport | `fitBounds` on circle | `flyTo` bounding sphere / entity set |

Non-reference OPs: markers only (same rule as today).

### 7.3 Pick modes

| Mode | Status | Globe behaviour |
|------|--------|-----------------|
| `PickMode.NONE` | Implemented | Normal tracking |
| `PickMode.LOCATION` | Implemented | Globe click → `reportLocation` |
| `PickMode.HEADING` | Planned (UI 2.0 Phase 4) | Click origin + target → bearing; extend enum + JS |
| Camera position | Via LOCATION today | Unchanged |

Pick mode pauses ship updates (existing rule preserved).

### 7.4 Default view

- **World view** on empty state and location pick entry.
- Camera altitude and orientation defined in engine config (not hardcoded in Python).
- Optional: restore last view per session (future; not Phase A–C).

---

## 8. Imagery and offline strategy (decision required)

Today: Leaflet JS offline; OSM tiles from CDN.

Globe requires an **explicit imagery policy**:

| Option | Description |
|--------|-------------|
| **A — CDN imagery** | Natural Earth / OSM / Cesium ion (token); network required |
| **B — Bundled low-res** | Single global texture in resources; always offline; limited zoom |
| **C — Hybrid** | Bundled low-res default + optional CDN high-res |

Architecture recommends **Option C** for Project X (matches current “bundled engine, remote tiles” pattern).

Decision required before Phase B implementation.

---

## 9. Python modules — change summary

| Module | Phase A | Phase B+ |
|--------|---------|----------|
| `gui/map_core.py` | Document contract; optional `MapEngineKind` enum | Add `PickMode.HEADING` |
| `gui/widgets/mapwidget.py` | No behaviour change | Optional engine diagnostics |
| `gui/mapcontroller.py` | No change | Heading pick API |
| `gui/mappage.py` | No change | Optional globe-specific tuning |
| `resources/map/map.html` | Contract shell | Globe engine load |
| `observation/geo_context.py` | **No change** | **No change** |
| Legacy map widgets/HTML | Mark deprecated | Delete (Phase F) |

**Forbidden:** AIS math, coverage filtering, or distance calculation inside JS. JS may compute geodesic **visual** geometry only.

---

## 10. Phased delivery plan

Implementation proceeds **one phase at a time**, each gated by architectural review (same discipline as SAVE-107).

### Phase A — Map Engine contract & abstraction

**Goal:** Formalize and test the JS bridge contract without changing visuals.

Deliverables:

- `engine/contract.js` — entry-point registry + version id
- Contract documentation in this file (§5) mirrored in code comments
- `map.html` refactored to load contract + Leaflet adapter (adapter implements contract)
- Automated tests: Python calls each entry point (smoke via Qt offscreen if feasible)
- Engine selection spike report (Cesium vs alternatives)

**Not in scope:** Visible globe, imagery change.

---

### Phase B — Globe renderer (core)

**Goal:** Replace Leaflet adapter with globe engine behind the same contract.

Deliverables:

- Globe engine loads in `map.html`
- World imagery (per §8 decision)
- Ship markers + trails on globe
- Observation markers
- Default world view + `focusShip`
- Location pick on globe

**Not in scope:** Geodesic coverage circles, heading pick, legacy deletion.

---

### Phase C — Geodesic coverage & global operations

**Goal:** Visual parity+ for observation coverage at planetary scale.

Deliverables:

- Geodesic coverage circle for reference OP
- Viewport fly-to reference coverage
- Validate alignment with `GeoContext.is_within_coverage()` (QA scenarios)
- Performance budget: ship update rates (500 ms / 2 s) maintained

---

### Phase D — Extended pick modes

**Goal:** Complete UI 2.0 Phase 4 camera/heading pick on main map.

Deliverables:

- `PickMode.HEADING` in Python
- Globe heading pick UX
- Camera wizard wired to main map (remove dependency on legacy `camera_map.html`)

---

### Phase E — Performance & polish

**Goal:** Production-quality globe for alpha release.

Deliverables:

- Entity clustering or LOD at low zoom (if needed)
- Trail/memory limits unchanged or tuned
- Theme polish for popups on globe
- System health check update (`check_map_engine()`)

---

### Phase F — Legacy retirement

**Goal:** Single map stack only.

Delete:

- `gui/widgets/observationmapwidget.py`
- `gui/widgets/cameramapwidget.py`
- `resources/map/observation_map.html`
- `resources/map/camera_map.html`
- `resources/map/leaflet/` (after globe stable)
- `map.html.save`

---

## 11. Testing strategy

| Layer | Approach |
|-------|----------|
| Bridge contract | Python unit tests invoke JS entry points (Qt offscreen WebEngine) |
| Geo alignment | Existing `GeoContext` tests + manual QA grid (lat/lon/radius) |
| Ship pipeline | Existing `test_mappage_ship_rendering.py` — must pass unchanged |
| Coverage visual | Golden-scenario QA: reference OP at equator, high latitude, large radius |
| Pick mode | Wizard integration tests (observation + camera) |
| Performance | FPS / CPU budget with N ships (document threshold in Phase E) |
| Release | `verify_linux_release.sh` — globe assets in bundle |

No Leaflet-specific tests exist today; SAVE-108 adds contract-level tests in Phase A.

---

## 12. Non-goals (SAVE-108)

- Weather layers, ocean currents, bathymetry
- 3D terrain elevation / buildings
- Satellite NORAD tracks (future milestone)
- AR / VR
- Replacing GeoContext or observation_manager
- Changing AIS provider subscription model (bbox remains Python-derived)
- Mobile / web standalone map (desktop Qt only)

---

## 13. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Large engine bundle size | Tree-shake; optional ion; measure in PyInstaller spec early |
| WebEngine WebGL limits | Phase A spike on target Linux/Windows GPUs |
| Popup HTML on 3D canvas | Screen-space overlay div (Cesium pattern) |
| Planar vs geodesic mismatch | Phase C explicit QA against GeoContext |
| Offline imagery quality | Hybrid policy (§8) |
| Regression in pick/wizard flows | Phase D gated; keep Leaflet adapter until globe pick proven |

---

## 14. Open decisions (require approval)

| ID | Decision | Options | Blocking |
|----|----------|---------|----------|
| D1 | Globe engine | CesiumJS / MapLibre globe / Three.js custom | Phase B |
| D2 | Imagery policy | CDN only / bundled / hybrid | Phase B |
| D3 | Default world camera | Fixed altitude vs fit-to-coverage | Phase B |
| D4 | Leaflet coexistence | Parallel adapter vs hard cutover | Phase B |
| D5 | Heading pick UX | Two-click bearing vs drag handle | Phase D |
| D6 | Ship clustering | None / zoom-threshold cluster | Phase E |

---

## 15. Success criteria (SAVE-108 complete)

SAVE-108 is complete when:

1. Globe is the sole production Map Engine (Leaflet retired).
2. All §5 bridge entry points work on the globe.
3. Reference observation coverage renders as a geodesic circle.
4. Ship pipeline and pick modes behave as today (or better at world scale).
5. Engine assets bundled; imagery policy documented and implemented.
6. Legacy map HTML/widgets removed.
7. Verification suite passes including release bundle checks.

---

## 16. Relationship to other milestones

| Milestone | Relationship |
|-----------|--------------|
| **SAVE-107** | Complete — storage paths stable for map asset bundling |
| **GEO Architecture** | Globe displays GeoContext truth; does not replace it |
| **UI 2.0 Phase 4** | Heading/camera pick completed by SAVE-108 Phase D |
| **Future SAVE-109+** | May add layers (EEZ, zones) as Map Engine plugins |

---

## 17. Approval gate

```
[ ] Architecture reviewed
[ ] D1–D6 decisions recorded
[ ] Phase A authorized
```

**No code implementation until this document is approved.**

---

*End of SAVE-108 Architecture Specification v1.0*
