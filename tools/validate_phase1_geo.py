#!/usr/bin/env python3
# ============================================================================
# Project X — Phase 1 GeoContext validation (automated)
# ============================================================================
#
# Complements manual QA in docs/qa/PHASE1-GEO-VALIDATION.md
#
# Usage (from repository root):
#   PYTHONPATH=src .venv/bin/python3 tools/validate_phase1_geo.py
#   PYTHONPATH=src .venv/bin/python3 tools/validate_phase1_geo.py --json
#

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
QA_HOME = REPO_ROOT / "data" / ".qa-home"

sys.path.insert(0, str(SRC_DIR))

QA_HOME.mkdir(parents=True, exist_ok=True)
os.environ["HOME"] = str(QA_HOME)

HUELVA_LAT = 37.14881
HUELVA_LON = -6.87653
BUDAPEST_LAT = 47.501539
BUDAPEST_LON = 19.039856

# Runtime fallback patterns that must not exist in active code paths.
FORBIDDEN_RUNTIME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "AIS Budapest default bbox",
        re.compile(r"_DEFAULT_BOUNDING_BOXES|\[\[45\.00,\s*17\.50\]"),
    ),
    (
        "Hardcoded CAMERA_LAT origin",
        re.compile(r"CAMERA_LAT\s*="),
    ),
    (
        "Legacy developer path (/home/zoli)",
        re.compile(r"/home/zoli"),
    ),
    (
        "Legacy Dunamonitor path",
        re.compile(r"Dunamonitor"),
    ),
    (
        "Legacy rtl-monitor path",
        re.compile(r"rtl-monitor"),
    ),
    (
        "Legacy duna-monitor path",
        re.compile(r"duna-monitor"),
    ),
)

# Files excluded from fallback scan (examples, static catalog data).
FALLBACK_SCAN_SKIP_PARTS = (
    "observation_points.json.example",
    "config/cameras/",
    "config/camera_packs/",
    "resources/map/camera_map.html",
    "resources/map/map.html.save",
    "resources/translations/",
    "gui/rulespage.py",  # D4 pending — not Phase 1 blocker
    "ais/providers/aisstream_provider.py",  # test-only minimal bbox
)


class CheckResult:

    def __init__(self, check_id: str, title: str, passed: bool, detail: str = ""):

        self.check_id = check_id
        self.title = title
        self.passed = passed
        self.detail = detail

    def to_dict(self) -> dict:

        return {
            "id": self.check_id,
            "title": self.title,
            "passed": self.passed,
            "detail": self.detail,
        }


def _should_scan(path: Path) -> bool:

    relative = path.relative_to(SRC_DIR).as_posix()

    for skip in FALLBACK_SCAN_SKIP_PARTS:
        if skip in relative:
            return False

    return path.suffix in {".py", ".html", ".json"}


def check_no_hidden_runtime_fallbacks() -> CheckResult:

    hits: list[str] = []

    for path in SRC_DIR.rglob("*"):
        if not path.is_file() or not _should_scan(path):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        relative = path.relative_to(REPO_ROOT).as_posix()

        for label, pattern in FORBIDDEN_RUNTIME_PATTERNS:
            if pattern.search(text):
                hits.append(f"{relative}: {label}")

    if hits:
        return CheckResult(
            "A-11",
            "No hidden runtime fallback coordinates",
            False,
            "; ".join(hits),
        )

    return CheckResult(
        "A-11",
        "No hidden runtime fallback coordinates",
        True,
        "No forbidden patterns in active runtime paths",
    )


def check_geocontext_module_importable() -> CheckResult:

    try:
        geo_module = importlib.import_module("observation.geo_context")
        context = geo_module.geo_context
        assert geo_module.GeoContext is not None
        assert context is not None
        assert geo_module.EARTH_RADIUS_KM == 6371.0
    except Exception as error:
        return CheckResult(
            "A-05",
            "GeoContext initialization",
            False,
            str(error),
        )

    module_type = type(importlib.import_module("observation.geo_context"))
    if module_type.__name__ != "module":
        return CheckResult(
            "A-05",
            "GeoContext initialization",
            False,
            "observation.geo_context is not importable as a module",
        )

    return CheckResult(
        "A-05",
        "GeoContext initialization",
        True,
        "observation.geo_context module and singleton load correctly",
    )


def check_reference_and_geocontext_behavior() -> CheckResult:

    import observation.geo_context as geo_module
    import observation.observation_manager as om_module
    from models.ship import Ship
    from observation.observation_manager import ObservationManager

    original = geo_module.observation_manager
    tmpdir = tempfile.mkdtemp()
    path = Path(tmpdir) / "observation_points.json"
    manager = ObservationManager(path=path)

    try:
        geo_module.observation_manager = manager
        om_module.observation_manager = manager
        context = geo_module.geo_context

        if context.has_reference():
            return CheckResult(
                "A-04",
                "Reference observation point creation",
                False,
                "Expected no reference on empty manager",
            )

        if context.distance_km(HUELVA_LAT, HUELVA_LON) is not None:
            return CheckResult(
                "A-05b",
                "GeoContext empty-state distance",
                False,
                "distance_km should be None without reference",
            )

        point = manager.create(
            name="Huelva QA",
            latitude=HUELVA_LAT,
            longitude=HUELVA_LON,
            coverage_radius_km=25.0,
        )
        manager.activate_point(point.id)

        reference = manager.reference()
        if reference is None:
            return CheckResult(
                "A-04",
                "Reference observation point creation",
                False,
                "reference() is None after create+activate",
            )

        if reference.id != point.id:
            return CheckResult(
                "A-04",
                "Reference observation point creation",
                False,
                "reference id does not match created point",
            )

        coords = context.coordinates()
        if coords is None or abs(coords[0] - HUELVA_LAT) > 1e-4:
            return CheckResult(
                "A-05c",
                "GeoContext coordinates",
                False,
                f"unexpected coordinates: {coords}",
            )

        boxes = geo_module.geo_context.ais_bounding_boxes()
        if boxes is None:
            return CheckResult(
                "A-06",
                "AIS subscription bounding boxes",
                False,
                "ais_bounding_boxes() returned None",
            )

        lat_min, lon_min = boxes[0][0]
        lat_max, lon_max = boxes[0][1]

        if not (lat_min < HUELVA_LAT < lat_max and lon_min < HUELVA_LON < lon_max):
            return CheckResult(
                "A-06",
                "AIS subscription bounding boxes",
                False,
                f"bbox does not wrap Huelva: {boxes}",
            )

        if lat_min > 45.0 and lat_max < 49.0 and lon_min > 17.0 and lon_max < 23.0:
            return CheckResult(
                "A-06",
                "AIS subscription bounding boxes",
                False,
                "bbox matches Budapest default region",
            )

        near = context.distance_km(HUELVA_LAT + 0.001, HUELVA_LON)
        far = context.distance_km(BUDAPEST_LAT, BUDAPEST_LON)

        if near is None or far is None:
            return CheckResult(
                "A-09",
                "Displayed distance calculation",
                False,
                "distance_km returned None with active reference",
            )

        if near >= 1.0 or far < 500.0:
            return CheckResult(
                "A-09",
                "Displayed distance calculation",
                False,
                f"unexpected near/far km: near={near}, far={far}",
            )

        if not context.is_within_coverage(HUELVA_LAT + 0.001, HUELVA_LON):
            return CheckResult(
                "A-08",
                "Ship filtering (coverage)",
                False,
                "near ship should be within coverage",
            )

        if context.is_within_coverage(BUDAPEST_LAT, BUDAPEST_LON):
            return CheckResult(
                "A-08",
                "Ship filtering (coverage)",
                False,
                "Budapest ship should be outside Huelva coverage",
            )

        from database.ship_registry import registry

        registry.clear()
        registry.add(
            Ship(
                mmsi=101,
                name="near",
                lat=HUELVA_LAT + 0.001,
                lon=HUELVA_LON,
                speed=0,
                course=0,
                heading=0,
                last_seen=datetime.now(),
            )
        )
        registry.add(
            Ship(
                mmsi=102,
                name="far",
                lat=BUDAPEST_LAT,
                lon=BUDAPEST_LON,
                speed=0,
                course=0,
                heading=0,
                last_seen=datetime.now(),
            )
        )

        if len(registry.all()) != 2:
            return CheckResult(
                "A-10",
                "Registry cleanup",
                False,
                "expected two ships before purge",
            )

        removed = registry.purge_outside_reference_coverage()
        remaining = registry.all()

        if removed != 1 or len(remaining) != 1 or remaining[0].mmsi != 101:
            return CheckResult(
                "A-10",
                "Registry cleanup",
                False,
                f"removed={removed}, remaining={[s.mmsi for s in remaining]}",
            )

        if remaining[0].distance_km >= 1.0:
            return CheckResult(
                "A-09",
                "Displayed distance calculation",
                False,
                f"registry distance_km={remaining[0].distance_km}",
            )

        from engines.ais.ais_protocol import reference_observation_bounding_boxes

        protocol_boxes = reference_observation_bounding_boxes()
        if protocol_boxes != boxes:
            return CheckResult(
                "A-06b",
                "AIS protocol uses GeoContext bbox",
                False,
                "ais_protocol bbox differs from GeoContext",
            )

        return CheckResult(
            "A-04",
            "Reference observation point + GeoContext behaviour",
            True,
            (
                f"reference={reference.name}; near={round(near, 3)} km; "
                f"far={round(far, 1)} km; purge_removed={removed}"
            ),
        )

    except Exception as error:
        return CheckResult(
            "A-04",
            "Reference observation point + GeoContext behaviour",
            False,
            str(error),
        )

    finally:
        geo_module.observation_manager = original
        om_module.observation_manager = original


def check_coords_delegates_to_geocontext() -> CheckResult:

    import observation.coords as coords
    import observation.geo_context as geo_module

    if coords.geo_context is not geo_module.geo_context:
        return CheckResult(
            "A-05d",
            "coords.py delegates to GeoContext",
            False,
            "coords.geo_context is not the shared singleton",
        )

    source = Path(SRC_DIR / "observation/coords.py").read_text(encoding="utf-8")
    if "math.sqrt" in source and "111.0" in source:
        return CheckResult(
            "A-05d",
            "coords.py delegates to GeoContext",
            False,
            "flat-earth math still present in coords.py",
        )

    duna_source = Path(SRC_DIR / "logbook/duna_format.py").read_text(encoding="utf-8")
    if "math.sqrt" in duna_source and "* 111.0" in duna_source:
        return CheckResult(
            "A-09b",
            "duna_format delegates distance to GeoContext",
            False,
            "flat-earth math still present in duna_format.py",
        )

    return CheckResult(
        "A-05d",
        "coords.py and duna_format delegate to GeoContext",
        True,
        "no duplicate flat-earth implementation in active helpers",
    )


def check_large_observation_radius_pipeline() -> CheckResult:

    import observation.geo_context as geo_module
    import observation.observation_manager as om_module
    from observation.observation_manager import ObservationManager

    original = geo_module.observation_manager
    tmpdir = tempfile.mkdtemp()
    path = Path(tmpdir) / "observation_points.json"
    manager = ObservationManager(path=path)

    gib_lat = 35.87690206261954
    gib_lon = -5.51897974414811
    radius_km = 500.0

    try:
        geo_module.observation_manager = manager
        om_module.observation_manager = manager
        context = geo_module.geo_context

        point = manager.create(
            name="Gibraltar",
            latitude=gib_lat,
            longitude=gib_lon,
            coverage_radius_km=radius_km,
        )
        manager.activate_point(point.id)

        if context.radius_km() != radius_km:
            return CheckResult(
                "A-12",
                "500 km observation radius pipeline",
                False,
                f"GeoContext.radius_km={context.radius_km()}",
            )

        box = context.ais_bounding_box()
        if box is None:
            return CheckResult(
                "A-12",
                "500 km observation radius pipeline",
                False,
                "ais_bounding_box() returned None",
            )

        lat_min, lon_min = box[0]
        lat_max, lon_max = box[1]
        lat_span = (lat_max - lat_min) * 111.0 / 2.0
        cos_lat = math.cos(math.radians(gib_lat))
        lon_span = (lon_max - lon_min) * 111.0 * abs(cos_lat) / 2.0

        if abs(lat_span - radius_km) > 1.0 or abs(lon_span - radius_km) > 1.0:
            return CheckResult(
                "A-12",
                "500 km observation radius pipeline",
                False,
                f"bbox half-span lat={lat_span:.1f} lon={lon_span:.1f}",
            )

        near_lat = gib_lat + (200.0 / 111.0)
        far_lat = gib_lat + (600.0 / 111.0)

        if not context.is_within_coverage(near_lat, gib_lon):
            return CheckResult(
                "A-12",
                "500 km observation radius pipeline",
                False,
                "200 km ship should be within 500 km coverage",
            )

        if context.is_within_coverage(far_lat, gib_lon):
            return CheckResult(
                "A-12",
                "500 km observation radius pipeline",
                False,
                "600 km ship should be outside 500 km coverage",
            )

        return CheckResult(
            "A-12",
            "500 km observation radius pipeline",
            True,
            f"radius={radius_km}; bbox_half_span={lat_span:.1f} km",
        )

    except Exception as error:
        return CheckResult(
            "A-12",
            "500 km observation radius pipeline",
            False,
            str(error),
        )

    finally:
        geo_module.observation_manager = original
        om_module.observation_manager = original


def run_checks() -> list[CheckResult]:

    return [
        check_geocontext_module_importable(),
        check_reference_and_geocontext_behavior(),
        check_large_observation_radius_pipeline(),
        check_coords_delegates_to_geocontext(),
        check_no_hidden_runtime_fallbacks(),
    ]


def main() -> int:

    parser = argparse.ArgumentParser(description="Phase 1 GeoContext automated validation")
    parser.add_argument("--json", action="store_true", help="Print JSON results")
    args = parser.parse_args()

    results = run_checks()
    passed = all(item.passed for item in results)

    if args.json:
        print(
            json.dumps(
                {
                    "phase": "1-geo",
                    "passed": passed,
                    "checks": [item.to_dict() for item in results],
                },
                indent=2,
            )
        )
    else:
        print("Phase 1 GeoContext — automated validation")
        print("=" * 60)

        for item in results:
            status = "PASS" if item.passed else "FAIL"
            print(f"[{status}] {item.check_id} {item.title}")

            if item.detail:
                print(f"       {item.detail}")

        print("=" * 60)
        print("OVERALL:", "PASS" if passed else "FAIL")
        print()
        print("Manual QA: docs/qa/PHASE1-GEO-VALIDATION.md")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
