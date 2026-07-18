# Phase 1 Geo QA — Run 001

**Date:** 2026-07-17  
**Scope:** GeoContext / Phase 1 validation  
**Architecture:** [GEO_ARCHITECTURE.md](../architecture/GEO_ARCHITECTURE.md)  
**Checklist:** [PHASE1-GEO-VALIDATION.md](../PHASE1-GEO-VALIDATION.md)

---

## Automated validation

**Command:**

```bash
PYTHONPATH=src .venv/bin/python3 tools/validate_phase1_geo.py
PYTHONPATH=src .venv/bin/python3 tests/test_geo_context.py -v
```

| ID | Check | Result |
|----|-------|--------|
| A-05 | GeoContext initialization | PASS |
| A-04 | Reference OP + GeoContext behaviour | PASS |
| A-06 | AIS bbox from reference (Huelva, not Budapest) | PASS |
| A-08 | Ship filtering (coverage) | PASS |
| A-09 | Distance (Haversine via GeoContext) | PASS |
| A-10 | Registry cleanup | PASS |
| A-11 | No hidden runtime fallback coordinates | PASS |
| A-05d | coords/duna_format delegate to GeoContext | PASS |
| UT | `tests/test_geo_context.py` (7 tests) | PASS |

**Automated overall:** PASS

**Sample metrics (Huelva OP, automated run):**

- Near ship distance: ~0.11 km  
- Budapest distance: ~2405 km  
- Registry purge removed: 1 distant ship  

**JSON artifact:** [phase1-geo-automated-20260717.json](phase1-geo-automated-20260717.json)

---

## Manual QA (required before Phase 2)

| ID | Step | Result | Notes |
|----|------|--------|-------|
| M-01 | Factory Reset | ☐ PASS ☐ FAIL | Close app before reset if running |
| M-02 | First Run Wizard | ☐ PASS ☐ FAIL | |
| M-03 | Create Observation Point | ☐ PASS ☐ FAIL | |
| M-04 | Reference OP in config | ☐ PASS ☐ FAIL | Inspect `observation_points.json` |
| M-05 | GeoContext live (no crash) | ☐ PASS ☐ FAIL | |
| M-06 | AIS subscription | ☐ PASS ☐ FAIL | Connects after OP; local traffic only |
| M-07 | Map viewport | ☐ PASS ☐ FAIL | Centres on OP, not Budapest |
| M-08 | Ship filtering on map | ☐ PASS ☐ FAIL | |
| M-09 | Displayed distances | ☐ PASS ☐ FAIL | Adjacent ship ≪ 1 km |
| M-10 | Registry cleanup on OP change | ☐ PASS ☐ FAIL | |
| M-11 | No hidden fallback coordinates | ☐ PASS ☐ FAIL | |

**Manual overall:** PENDING — **M-09 fix applied, re-test required**

---

## M-09 root cause (2026-07-17)

**Symptom:** Map correct (OP centre, ships nearby), but vessel card Distance ≈ 2200 km.

**Cause:** Display pipeline split — GeoContext/registry computed correct `distance_km`, but the vessel card **Location** section preferred `camera_distance_km` and `camera_bearing_deg`. Those were filled by `_display_camera_for_ship()` fallback: **nearest enabled pack camera** (Budapest catalog at 47.50°N, 19.04°E) even when that camera cannot observe the ship. Distance shown = camera→ship (~2200 km from Huelva), not reference OP→ship.

**Fix (architectural):**

- `GeoContext.ship_observation_fields()` — single source for reference distance + bearing
- Vessel card Location uses `distance_km` + `reference_bearing_deg` only
- `camera_distance_km` reserved for actual observing camera metadata (Camera section)
- Removed pack-camera nearest-neighbour fallback from `_display_camera_for_ship()`

**Re-test:** M-09 after app restart.

---

## Decision

| Status | Condition |
|--------|-----------|
| **BLOCKED — Phase 2** | Manual M-01…M-11 not yet signed off |
| **PROCEED — Phase 2** | All manual steps PASS |

**Current decision:** BLOCKED — awaiting manual QA sign-off

---

## Tester sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | | | |
| Review | | | |
