#!/usr/bin/env python3
"""Regression tests for Observation Radius through GeoContext and AIS bbox."""

from __future__ import annotations

import importlib
import math
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import observation.observation_manager as observation_manager_module
from database.ship_registry import registry
from models.ship import Ship
from observation.geo_context import geo_context
from observation.observation_manager import ObservationManager

_GEO_CONTEXT_MODULE = importlib.import_module("observation.geo_context")


def _reference_observation_bounding_boxes():
    return _GEO_CONTEXT_MODULE.geo_context.ais_bounding_boxes()

GIB_LAT = 35.87690206261954
GIB_LON = -5.51897974414811
RADIUS_KM = 500.0


def _bbox_half_span_km(box: list[list[float]], latitude: float) -> tuple[float, float]:
    lat_min, lon_min = box[0]
    lat_max, lon_max = box[1]
    lat_span = (lat_max - lat_min) * 111.0 / 2.0
    cos_lat = math.cos(math.radians(latitude))
    lon_span = (lon_max - lon_min) * 111.0 * abs(cos_lat) / 2.0
    return lat_span, lon_span


class ObservationRadiusPipelineTests(unittest.TestCase):

    def setUp(self) -> None:

        self._tmpdir = tempfile.mkdtemp()
        self._path = Path(self._tmpdir) / "observation_points.json"
        self._manager = ObservationManager(path=self._path)
        self._original_manager = _GEO_CONTEXT_MODULE.observation_manager
        _GEO_CONTEXT_MODULE.observation_manager = self._manager
        observation_manager_module.observation_manager = self._manager
        registry.clear()

    def tearDown(self) -> None:

        registry.clear()
        _GEO_CONTEXT_MODULE.observation_manager = self._original_manager
        observation_manager_module.observation_manager = self._original_manager

    def test_500km_radius_flows_through_geocontext_ais_and_filters(self) -> None:

        point = self._manager.create(
            name="Gibraltar",
            latitude=GIB_LAT,
            longitude=GIB_LON,
            coverage_radius_km=RADIUS_KM,
        )
        self._manager.activate_point(point.id)

        self.assertEqual(geo_context.radius_km(), RADIUS_KM)

        box = geo_context.ais_bounding_box()
        self.assertIsNotNone(box)
        lat_span, lon_span = _bbox_half_span_km(box, GIB_LAT)
        self.assertAlmostEqual(lat_span, RADIUS_KM, delta=1.0)
        self.assertAlmostEqual(lon_span, RADIUS_KM, delta=1.0)

        protocol_boxes = _reference_observation_bounding_boxes()
        self.assertEqual(protocol_boxes, [box])

        near_lat = GIB_LAT + (200.0 / 111.0)
        far_lat = GIB_LAT + (600.0 / 111.0)
        self.assertTrue(geo_context.is_within_coverage(near_lat, GIB_LON))
        self.assertFalse(geo_context.is_within_coverage(far_lat, GIB_LON))

        registry.add(
            Ship(
                mmsi=1,
                name="near",
                lat=near_lat,
                lon=GIB_LON,
                speed=0,
                course=0,
                heading=0,
                last_seen=datetime.now(),
            )
        )
        registry.add(
            Ship(
                mmsi=2,
                name="far",
                lat=far_lat,
                lon=GIB_LON,
                speed=0,
                course=0,
                heading=0,
                last_seen=datetime.now(),
            )
        )

        visible = [
            ship
            for ship in registry.all()
            if geo_context.is_within_coverage(ship.lat, ship.lon)
        ]
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].mmsi, 1)

    def test_set_coverage_radius_updates_pipeline(self) -> None:

        point = self._manager.create(
            name="Test",
            latitude=GIB_LAT,
            longitude=GIB_LON,
            coverage_radius_km=25.0,
        )
        self._manager.activate_point(point.id)

        self.assertAlmostEqual(geo_context.radius_km(), 25.0)

        self._manager.set_coverage_radius(point.id, RADIUS_KM)

        self.assertAlmostEqual(geo_context.radius_km(), RADIUS_KM)
        box = geo_context.ais_bounding_box()
        lat_span, _ = _bbox_half_span_km(box, GIB_LAT)
        self.assertAlmostEqual(lat_span, RADIUS_KM, delta=1.0)


if __name__ == "__main__":
    unittest.main()
