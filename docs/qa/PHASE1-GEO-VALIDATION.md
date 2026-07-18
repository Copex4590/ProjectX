# Phase 1 — GeoContext Validation Checklist

**Scope:** Geographic single source of truth (Phase 1)  
**Blocks:** Phase 2 (AIS provider decoupling)  
**Architecture:** [GEO_ARCHITECTURE.md](../architecture/GEO_ARCHITECTURE.md)

---

## Prerequisites

- Repository root: `/home/zoli/ProjectX`
- Virtualenv: `.venv/bin/python3`
- Development launch (not frozen build required for this checklist)

```bash
cd /home/zoli/ProjectX
python3 tools/factory_reset.py --yes
PYTHONPATH=src .venv/bin/python3 tools/validate_phase1_geo.py
PYTHONPATH=src .venv/bin/python3 tests/test_geo_context.py -v
```

---

## Automated checks (run before manual QA)

| ID | Check | Command / tool | Pass criteria |
|----|-------|----------------|---------------|
| A-05 | GeoContext initialization | `tools/validate_phase1_geo.py` | Module loads; singleton exists; `EARTH_RADIUS_KM == 6371` |
| A-04 | Reference OP + GeoContext behaviour | same | Create Huelva OP → `reference()` set; coords/bbox/distance/coverage correct |
| A-06 | AIS bbox from reference | same | Bbox wraps Huelva; **not** Budapest default |
| A-08 | Ship filtering (coverage) | same | Near ship in coverage; Budapest ship out |
| A-09 | Distance (Haversine via GeoContext) | same | Near ≪ 1 km; far ≫ 500 km from Huelva |
| A-10 | Registry cleanup | same | `purge_outside_reference_coverage()` removes distant ship |
| A-11 | No hidden runtime fallbacks | same | No `_DEFAULT_BOUNDING_BOXES` / `CAMERA_LAT` in active paths |
| A-* | Unit tests | `tests/test_geo_context.py` | All tests PASS |

Record automated result:

```bash
PYTHONPATH=src .venv/bin/python3 tools/validate_phase1_geo.py --json \
  > docs/qa/reports/phase1-geo-automated-$(date +%Y%m%d).json
```

---

## Manual QA checklist

Perform steps **in order** after factory reset.

| ID | Step | Pass criteria | Result |
|----|------|---------------|--------|
| M-01 | **Factory Reset** | `python3 tools/factory_reset.py --yes` completes; no `observation_points.json` in `src/config/`; app data cleared | ☐ PASS ☐ FAIL |
| M-02 | **First Run Wizard** | Wizard opens on launch; completes without freeze; map visible during setup | ☐ PASS ☐ FAIL |
| M-03 | **Create Observation Point** | Place OP (e.g. Huelva `37.14881, -6.87653`); set radius (e.g. 25 km); save succeeds | ☐ PASS ☐ FAIL |
| M-04 | **Reference OP created** | `src/config/observation_points.json` has one active point; internal `reference_id` matches that point (file inspection) | ☐ PASS ☐ FAIL |
| M-05 | **GeoContext live** | Dashboard/map show OP location; no crash on ship update | ☐ PASS ☐ FAIL |
| M-06 | **AIS subscription** | After OP + AISStream key configured: status connects (not stuck on Budapest traffic only); terminal/log shows subscribe **after** OP exists | ☐ PASS ☐ FAIL |
| M-07 | **Map viewport** | Map centres on **your** OP (Huelva), not Budapest/world-only after OP exists | ☐ PASS ☐ FAIL |
| M-08 | **Ship filtering** | Ships on map appear near OP coverage only; no cluster at Budapest when OP is elsewhere | ☐ PASS ☐ FAIL |
| M-09 | **Displayed distances** | Vessel card/popup distance plausible (adjacent ship ≪ 1 km, not thousands of km) | ☐ PASS ☐ FAIL |
| M-10 | **Registry cleanup on OP change** | Move OP or change radius: distant ships disappear from map/list after refresh | ☐ PASS ☐ FAIL |
| M-11 | **No hidden fallback coordinates** | Visual + code audit: no ships/map focus at Budapest unless OP is there; automated A-11 PASS | ☐ PASS ☐ FAIL |

---

## Detailed manual notes

### M-01 Factory Reset

```bash
python3 tools/factory_reset.py --yes
```

Verify:

- `src/config/observation_points.json` absent (or empty state after next launch)
- `data/*.db` cleared per tool output

### M-04 Reference OP (file inspection)

After First Run:

```bash
cat src/config/observation_points.json
```

Expect:

- One point with your lat/lon and `coverage_radius_km`
- `"active": true` for that point
- `"reference_id"` equal to that point's `"id"`

### M-06 AIS subscription

Expected sequence:

1. App starts → **no OP** → AIS worker waits (no Budapest bbox subscribe)
2. First Run creates OP → AIS reconnects with Huelva-area bbox
3. Ships arrive near OP, not Danube/Budapest unless physically there

### M-09 Distances (Haversine)

Phase 1 switched from flat-earth to Haversine. Values near the OP should remain small (metres–hundreds of metres for adjacent traffic). If you still see ~2251 km for a nearby ship, **FAIL**.

### M-10 Registry cleanup

1. Note MMSI/count of ships on map
2. Move OP far away **or** shrink radius below nearest ship
3. Confirm stale ships removed after a few seconds / map refresh

---

## Known exclusions (not Phase 1 failures)

| Item | Status |
|------|--------|
| `gui/rulespage.py` Budapest defaults | D4 pending |
| `hybrid_engine` legacy paths (`~/duna-monitor`, `rtl-monitor`) | D5 pending — Phase 3 |
| Dual camera stack (pack vs OP-attached) | D6 pending — Phase 5 |
| Dead files (`hybrid_engine_v2.py`, `camera_map.html`) | Cleanup Phase 6 |

---

## Phase 1 gate

| Gate | Requirement |
|------|-------------|
| **Proceed to Phase 2** | All automated checks PASS **and** all manual M-01…M-11 PASS |
| **Block Phase 2** | Any FAIL on M-01, M-03, M-06, M-07, M-08, M-09, M-11 |

When complete, save a short report:

`docs/qa/reports/PX-QA-PHASE1-GEO-001.md`

Template:

```markdown
# Phase 1 Geo QA — Run 001
Date:
Tester:
Automated: PASS / FAIL (attach JSON)
Manual M-01…M-11: PASS / FAIL
Notes:
Decision: PROCEED TO PHASE 2 / BLOCKED
```

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Tester | | | |
| Review | | | |
