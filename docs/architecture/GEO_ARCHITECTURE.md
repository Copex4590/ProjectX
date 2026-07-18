# GEO Architecture — Geographic Single Source of Truth

**Status:** Accepted — Phase 1 may begin  
**Version:** 0.2  
**Project:** Project X  
**Related:** [UI 2.0 Master Architecture](../UI_2_0_MASTER_ARCHITECTURE.md) (Decisions 5–6), geographic audit (2026-07-17)

---

## 1. Purpose

This document defines how Project X handles geography.

The goal is **one geographic truth** from which every coordinate-based behaviour is derived. No hidden origins, no city defaults, no parallel distance models, and no bounding box treated as persisted configuration.

Phase 1 implementation (GeoContext) may begin once §12 Phase 1 blocker decisions are recorded. Decisions D4–D6 remain pending and do not block Phase 1.

---

## 2. Problem statement

Today the codebase partially uses `observation_manager.reference()` and `observation/coords.py`, but geographic logic is still spread across:

- Legacy Duna Monitor paths and semantics in `hybrid_engine.py`
- Duplicate distance helpers (`coords.py` vs `logbook/duna_format.py`)
- A separate camera catalog stack with its own Haversine math
- Hardcoded defaults (e.g. Budapest in rules UI and retired map HTML)
- AIS bounding boxes named and wired as if they were domain objects

First Run QA exposed the symptom: the map focused on one place while ships appeared elsewhere because **different subsystems used different geographic references at the same time**.

This document locks the target model so Phase 1+ refactors converge on one design.

---

## 3. Design principles

1. **Single source of truth** — All runtime geographic behaviour derives from the **Reference Observation Point** and its **Observation Radius**.
2. **User vocabulary is minimal** — In the product, users only configure an **Observation Point** and an **Observation Radius**. The user **never** sees the term “Reference Observation Point”; reference is an internal implementation detail when more than one point exists.
3. **No geographic fallback** — If no reference exists, geographic operations return empty / waiting / disabled. There is no default city, river, or legacy camera position.
4. **Derived, not stored** — Distance, bearing, coverage checks, map viewport focus, registry filters, and AIS bounding boxes are **computed on demand** from the reference. They are not cached as independent configuration.
5. **Bounding box is not domain** — A bounding box exists only as a **technical parameter** for AIS providers. It is always recalculated from reference + radius at subscribe time.
6. **One formula policy** — Exactly one distance implementation exists in the application: **Haversine great-circle distance** (Earth radius 6371 km), exposed only through GeoContext (see D1 in §12).
7. **Explicit invalidation** — When reference coordinates or radius change, every dependent subsystem must refresh or resubscribe. No stale geographic session state.

---

## 4. User model vs internal model

### 4.1 User-facing concepts (exactly two)

| Concept | Meaning |
|---------|---------|
| **Observation Point** | Where the user observes from (latitude, longitude on the map). |
| **Observation Radius** | How far around that point the system cares about traffic (kilometres). |

The user never configures a bounding box, a default map city, or a separate “distance origin.” The user never sees internal labels such as “reference point.”

### 4.2 Internal canonical object (not user-facing)

| Concept | Meaning |
|---------|---------|
| **Reference Observation Point** | Internal: the single observation point used as the geographic origin for all derived behaviour: `(latitude, longitude, coverage_radius_km)`. |

When exactly one observation point is active, it **is** the reference automatically.

When multiple observation points exist (UI 2.0 Decision 6), the system may prompt the user to choose which observation point drives distance and bearing (worded in user language, not “reference”). That choice is persisted internally as `reference_id`.

**D3 (locked):** `set_active()` continues to update the reference as it does today (`_reference_id = target.id`). Separation of active vs reference may be revisited if future multi-reference workflows require it.

### 4.3 Related but non-geographic concepts

| Concept | Role | Geographic truth? |
|---------|------|-------------------|
| **Active observation point** | UI/configuration context (e.g. which point’s cameras are being edited on the Dashboard). | **No** — must not be used for distance, filtering, AIS subscribe, or map viewport unless it is also the reference. |
| **Inactive observation point** | Shown on the map (red marker) but not the reference. | Display only. |
| **Ship position** | Runtime AIS/RTL coordinates. | Measured **relative to** the reference; not an origin. |
| **Camera position** | Where a camera looks from. | Used for camera matching, not as the global origin. |
| **Alert region center** | Optional rule-defined area. | Independent region unless a future rule type explicitly binds to reference coverage (decision pending; see §10). |
| **Timeline / logbook coordinates** | Historical record of where a ship was. | Stored history, not a live origin. |

---

## 5. Reference Observation Point — definition

The Reference Observation Point is the **only** object from which geographic truth flows.

### 5.1 Fields

| Field | Source | Persisted? |
|-------|--------|------------|
| `latitude` | User map placement | Yes (`observation_points.json`) |
| `longitude` | User map placement | Yes |
| `coverage_radius_km` | User “Observation Radius” | Yes |
| `id`, `name`, `active`, timestamps | Observation management | Yes |

Nothing else is persisted as geographic configuration (no bbox, no fallback origin, no cached distance grid).

### 5.2 Resolution rules

Order of resolution (current `ObservationManager._find_reference_unlocked` intent, formalised here):

1. If `reference_id` points to an **active** observation point → use it.
2. Else if exactly one active observation point exists → that point becomes reference (auto-assign `reference_id`).
3. Else if multiple active points and `_active_id` is active → use `_active_id` as reference (interim until user chooses).
4. Else → **no reference** (`None`).

When the result is `None`:

- AIS subscribe **waits** (does not connect with a default region).
- Map shows **world view** if no observation points exist (UI 2.0 Decision 5).
- Distance, bearing, and coverage checks return **no value** / skip processing.
- Ship registry may hold data but **display and ingest filters** treat out-of-coverage ships as excluded.

### 5.3 Empty state

Zero observation points:

- World map, zoomed out, centre `[20, 0]` (or equivalent world view) — **not** a city.
- No markers, no AIS geographic subscription, no distance display.

This matches UI 2.0 Decision 5: **No Budapest. No Victoria. No default coordinates.**

---

## 6. GeoContext — planned single API (Phase 1)

Phase 1 introduces **GeoContext** in **`observation/geo_context.py`** (D7) as the **only supported entry point** for geographic derivation.

Other modules **must not** call `observation_manager.reference()` directly for math after Phase 1 is complete (manager remains for CRUD and persistence).

### 6.1 Read API (normative)

| Method | Returns | Behaviour |
|--------|---------|-----------|
| `reference()` | `ObservationPoint \| None` | Current reference, or `None`. |
| `coordinates()` | `(lat, lon) \| None` | Reference position. |
| `radius_km()` | `float \| None` | Observation Radius of the reference. |
| `has_reference()` | `bool` | Convenience. |
| `distance_km(lat, lon)` | `float \| None` | Haversine distance from reference (km); `None` if no reference. |
| `bearing_deg(lat, lon)` | `float \| None` | Initial bearing from reference (degrees). |
| `is_within_coverage(lat, lon)` | `bool` | `False` if no reference or invalid coords. |
| `ais_bounding_box()` | `list[list[float]] \| None` | Derived rectangle for AIS providers only; `None` if no reference. |

### 6.2 Distance and bearing implementation (D1)

GeoContext owns the **only** distance and bearing math in the application:

- **Distance:** Haversine formula, Earth radius **6371 km** (same constant as `models/camera.py` and `alerts/alert_manager.py` today).
- **Bearing:** Standard initial-bearing formula from reference to target.

All modules — including `logbook/duna_format.py`, `ship_registry`, `hybrid_engine`, map enrichment, and camera matching — must call `GeoContext.distance_km()` (or thin delegates to it). No duplicate flat-earth or inline Haversine implementations elsewhere after Phase 1.

**Rationale:** Haversine is accurate at any latitude (required for non-Danube deployments), matches existing camera/alert code, and keeps one formula for coverage circles and displayed distances.

### 6.3 Direction semantics (logbook compatibility)

`get_direction(lat)` (“északra” / “délre”) is **relative to reference latitude**, not a fixed river or city. It remains a presentation helper for logbook format, not a geographic origin. It does not define coverage or AIS subscribe regions.

### 6.4 Invalidation

GeoContext exposes or forwards a **`changed`** signal when any of the following occur:

- Reference point created, moved, deleted, or radius changed
- `reference_id` changed (user selection or auto-resolution)
- Active set changed in a way that alters reference resolution

Subscribers (minimum set):

| Subscriber | Action on change |
|------------|------------------|
| AIS worker (`HybridEngine`) | Close WebSocket, purge out-of-coverage ships, resubscribe with new `ais_bounding_box()` |
| Map page | Refresh observation markers, refocus viewport on reference, republish filtered ships |
| Ship registry | `purge_outside_reference_coverage()` |
| Dashboard / distance displays | Refresh labels |

---

## 7. Bounding box rules

### 7.1 What a bounding box is

An AIS **bounding box** is a pair of corners `[[lat_min, lon_min], [lat_max, lon_max]]` required by AISStream (and similar providers) to limit the WebSocket feed.

It is:

- **Derived** from `reference.latitude`, `reference.longitude`, `reference.coverage_radius_km`
- **Recalculated** on every subscribe and resubscribe
- **Never persisted** to disk or user config
- **Never shown** in the UI as a user-editable concept

### 7.2 What a bounding box is not

A bounding box must **not** be:

- A saved state or cache key
- A fallback when no observation point exists
- A hardcoded region (e.g. Danube / Budapest defaults)
- A standalone domain type or database entity
- Named in user-facing strings

### 7.3 Derivation

```
ais_bounding_box = coverage_bounding_box(
    reference.latitude,
    reference.longitude,
    reference.coverage_radius_km,
)
```

Implementation today lives in `observation/coords.coverage_bounding_box()`. Phase 1 moves call sites to `GeoContext.ais_bounding_box()` only.

### 7.4 Coverage shape vs bbox shape

| Mechanism | Shape | Used for |
|-----------|-------|----------|
| **Observation coverage** | Circle (radius km) | Ship ingest filter, map display, registry purge, distance threshold |
| **AIS bounding box** | Axis-aligned rectangle approximating the circle | Provider subscription only |

The circle is the **authoritative** coverage model. The rectangle may be slightly larger at corners; ingest and display filters still use `is_within_coverage()` (circle).

Phase 1 must not widen this gap. Optional tightening (e.g. inset circle) is a §10 decision.

### 7.5 Connection tests without a reference

AIS **connection test** (wizard “Test connection”) may use a **fixed minimal test rectangle** that is explicitly documented as non-geographic and never used for live subscription. Live subscription **requires** a reference observation point.

---

## 8. Derived behaviour catalogue

Everything in this table **must** originate from GeoContext / reference + radius after refactor completion.

| Behaviour | Derivation | Must not use |
|-----------|------------|--------------|
| AIS subscribe region | `ais_bounding_box()` | Hardcoded bbox, `active()` alone, legacy camera coords |
| Ship ingest filter | `is_within_coverage(lat, lon)` | Direction-only filter, fixed city |
| Map ship layer | Same coverage filter | Unfiltered `registry.all()` |
| Map viewport (normal mode) | Centre on reference coordinates | First point in list, Budapest default |
| Distance on vessel cards / logbook | `distance_km(lat, lon)` | `CAMERA_LAT/LON`, duplicate flat-earth in `duna_format` |
| Bearing (where shown) | `bearing_deg(lat, lon)` | Camera pack as global origin |
| Registry cleanup on OP change | Purge ships where `not is_within_coverage` | Manual city-based cleanup |
| Empty map state | No reference / no points → world view | Any default city |
| Camera preview selection | Camera geometry vs **ship position**; global “where am I observing from” remains reference | Pack catalog as implicit world origin |

### 8.1 Explicitly out of scope for reference (unless decided otherwise)

| Data | Treatment |
|------|-----------|
| Camera pack JSON (`config/cameras/`, `camera_packs/`) | Static catalog data; camera lat/lon is **camera location**, not application origin |
| Timeline historical lat/lon | Immutable event fields |
| Alert rule custom region | Rule-defined centre until “reference coverage” rule type is approved (§10) |
| Example config (`observation_points.json.example`) | Documentation sample only |

---

## 9. Module access rules

After Phase 1 completion:

| Layer | May read reference | May compute distance/coverage/bbox |
|-------|-------------------|-------------------------------------|
| `observation/geo_context.py` | Yes (implements) | Yes (only implementation) |
| `observation/observation_manager.py` | Yes (persistence) | **No** (CRUD only) |
| `engines/ais/ais_protocol.py` | Via GeoContext | `ais_bounding_box()` only |
| `engines/rtl/hybrid_engine.py` | Via GeoContext | Via GeoContext |
| `database/ship_registry.py` | Via GeoContext | Via GeoContext |
| `gui/mappage.py`, `vesselspage.py` | Via GeoContext | Via GeoContext |
| `logbook/duna_format.py` | Via GeoContext | Delegate to GeoContext |
| `gui/mapcontroller.py` | Via GeoContext / manager for markers | Viewport from reference flag + coords |

### 9.1 Forbidden patterns (post-refactor)

- Hardcoded latitude/longitude used as runtime origin
- `_DEFAULT_BOUNDING_BOXES` or equivalent city/region fallback
- `fallback_coordinates()` as a name implying a non-reference fallback (deprecate → `reference_coordinates()`)
- `active_observation_bounding_boxes()` misnomer (rename to `reference_observation_bounding_boxes()` or remove in favour of GeoContext)
- Geographic math inside `hybrid_engine` without GeoContext
- Dual-write/read of AIS keys or log paths under `~/duna-monitor/` or `~/rtl-monitor/` as authoritative config

---

## 10. Decisions

### 10.1 Locked for Phase 1 (see §12)

| ID | Topic | Status |
|----|-------|--------|
| D1 | Single distance implementation via GeoContext | **Accepted** — Haversine (6371 km) |
| D2 | Multi-OP; reference internal only | **Accepted** |
| D3 | `set_active()` updates reference (current behaviour) | **Accepted** |
| D7 | GeoContext module: `observation/geo_context.py` | **Accepted** |

### 10.2 Pending (not Phase 1 blockers)

| ID | Topic | Options |
|----|-------|---------|
| D4 | **Alert region defaults** | A) Empty / force map pick · B) Default to reference centre + radius |
| D5 | **HybridEngine legacy outputs** | A) Remove · B) Move under `data/` · C) Dev flag |
| D6 | **Camera stack** | A) Map preview = OP-attached cameras · B) Keep pack catalog for preview |

Decide D4–D6 before Phases 5–6 (cameras, rules/alerts, hybrid cleanup). They do not block Phase 1 GeoContext work.

---

## 11. Migration phases (reference only)

This document is Phase 0. Implementation order after approval:

| Phase | Scope |
|-------|-------|
| **0** | This document + decision log |
| **1** | GeoContext API, single distance/coverage, deprecate direct coord calls |
| **2** | AIS provider decoupling; bbox only via GeoContext |
| **3** | `hybrid_engine` legacy removal; Project X paths |
| **4** | UI filtering parity (map, vessels, registry) |
| **5** | Camera stack unification |
| **6** | Rules/alerts defaults; delete retired map HTML/widgets |
| **7** | Observation manager active/reference cleanup |
| **8** | QA matrix (First Run, Huelva, factory reset) |

Phase 1 may begin when §12 Phase 1 blocker decisions are recorded (D1, D2, D3, D7).

---

## 12. Decision log

| Date | ID | Decision | Notes |
|------|-----|----------|-------|
| 2026-07-17 | **D1** | **Accepted** — Exactly one distance implementation application-wide, via GeoContext only. | **Engineering choice:** Haversine great-circle distance, Earth radius 6371 km. All modules delegate to `GeoContext.distance_km()`; remove duplicate flat-earth paths in Phase 1. |
| 2026-07-17 | **D2** | **Accepted** — Multi Observation Point support remains. | User never sees “Reference Observation Point”; reference is internal. UI may ask which observation point drives distance/bearing using user-facing wording. |
| 2026-07-17 | **D3** | **Accepted** — `set_active()` may continue to update reference as today. | `_reference_id` set with active switch. Decouple later if multi-reference workflows require it. |
| 2026-07-17 | D4 | *Pending* | Not a Phase 1 blocker. Alert region defaults. |
| 2026-07-17 | D5 | *Pending* | Not a Phase 1 blocker. HybridEngine legacy file outputs and paths. |
| 2026-07-17 | D6 | *Pending* | Not a Phase 1 blocker. Camera stack unification (pack vs OP-attached). |
| 2026-07-17 | **D7** | **Accepted** — GeoContext lives in `observation/geo_context.py`. | Dedicated module; `coords.py` becomes implementation detail or thin helpers called by GeoContext. |

---

## 13. Acceptance criteria (Phase 0 complete)

Phase 0 is complete when:

- [x] `GEO_ARCHITECTURE.md` exists and defines reference OP, radius, GeoContext plan, and bbox rules
- [x] Stakeholder review completed
- [x] Phase 1 blocker decisions recorded in §12 (D1, D2, D3, D7)
- [x] Document status updated to **Accepted — Phase 1 may begin**

**Phase 1 is cleared to start.** D4, D5, and D6 remain pending for later phases.

---

## 14. Glossary

| Term | Definition |
|------|------------|
| **Reference Observation Point** | Internal: the single persisted observation point used as geographic origin. Not shown to users. |
| **Observation Radius** | `coverage_radius_km` on the reference point; user-facing “Observation Radius”. |
| **GeoContext** | Module `observation/geo_context.py`; sole API for derived geographic values. |
| **Coverage** | Circular region: distance from reference ≤ Observation Radius. |
| **AIS bounding box** | Provider-specific axis-aligned rectangle derived from coverage; not user-facing. |
| **Empty geographic state** | No observation points → world map, no AIS geo subscribe, no distances. |

---

## 15. References

- `docs/UI_2_0_MASTER_ARCHITECTURE.md` — Decisions 5 (empty state), 6 (multi-OP reference), 7 (single map)
- `docs/architecture/PX-001-Storage-Architecture.md` — Path single-source pattern (analogous discipline)
- `src/observation/observation_manager.py` — Persistence and reference resolution
- `src/observation/coords.py` — Current helper implementations (to be wrapped by GeoContext)
