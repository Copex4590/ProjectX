#!/usr/bin/env python3
"""Unit tests for observation.geo_context (Phase 1)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models.ship import Ship
import importlib
import observation.observation_manager as observation_manager_module
from observation.observation_manager import ObservationManager
from observation.geo_context import (
    GeoContext,
    geo_context,
    haversine_distance_km,
    initial_bearing_deg,
)

_GEO_CONTEXT_MODULE = importlib.import_module("observation.geo_context")


class HaversineMathTests(unittest.TestCase):

    def test_same_point_is_zero(self) -> None:

        self.assertAlmostEqual(
            haversine_distance_km(47.5, 19.0, 47.5, 19.0),
            0.0,
            places=6,
        )

    def test_known_short_distance_order_of_magnitude(self) -> None:

        # ~250 m apart near Huelva
        distance = haversine_distance_km(37.14881, -6.87653, 37.149, -6.876)
        self.assertGreater(distance, 0.01)
        self.assertLess(distance, 1.0)

    def test_bearing_is_normalized(self) -> None:

        bearing = initial_bearing_deg(0.0, 0.0, 1.0, 0.0)
        self.assertGreaterEqual(bearing, 0.0)
        self.assertLess(bearing, 360.0)


class GeoContextReferenceTests(unittest.TestCase):

    def setUp(self) -> None:

        self._tmpdir = tempfile.mkdtemp()
        self._path = Path(self._tmpdir) / "observation_points.json"
        self._manager = ObservationManager(path=self._path)
        self._original_manager = _GEO_CONTEXT_MODULE.observation_manager
        _GEO_CONTEXT_MODULE.observation_manager = self._manager
        observation_manager_module.observation_manager = self._manager

    def tearDown(self) -> None:

        _GEO_CONTEXT_MODULE.observation_manager = self._original_manager
        observation_manager_module.observation_manager = self._original_manager

    def test_no_reference_returns_none_distance(self) -> None:

        context = GeoContext()
        self.assertFalse(context.has_reference())
        self.assertIsNone(context.distance_km(47.5, 19.0))
        self.assertIsNone(context.ais_bounding_box())

    def test_reference_distance_and_coverage(self) -> None:

        point = self._manager.create(
            name="Huelva",
            latitude=37.14881,
            longitude=-6.87653,
            coverage_radius_km=25.0,
        )
        self._manager.activate_point(point.id)

        context = GeoContext()
        self.assertTrue(context.has_reference())
        self.assertAlmostEqual(context.coordinates()[0], 37.14881, places=5)

        near = context.distance_km(37.149, -6.876)
        far = context.distance_km(47.5, 19.04)

        self.assertIsNotNone(near)
        self.assertIsNotNone(far)
        self.assertLess(near, 1.0)
        self.assertGreater(far, 1000.0)
        self.assertTrue(context.is_within_coverage(37.149, -6.876))
        self.assertFalse(context.is_within_coverage(47.5, 19.04))

    def test_ais_bounding_box_wraps_reference(self) -> None:

        point = self._manager.create(
            name="Test",
            latitude=37.14881,
            longitude=-6.87653,
            coverage_radius_km=25.0,
        )
        self._manager.activate_point(point.id)

        box = geo_context.ais_bounding_box()
        self.assertIsNotNone(box)
        lat_min, lon_min = box[0]
        lat_max, lon_max = box[1]
        self.assertLess(lat_min, 37.14881)
        self.assertGreater(lat_max, 37.14881)
        self.assertLess(lon_min, -6.87653)
        self.assertGreater(lon_max, -6.87653)

    def test_coverage_bounding_box_on_geo_context_instance(self) -> None:

        box = geo_context.coverage_bounding_box(37.14881, -6.87653, 25.0)
        self.assertEqual(len(box), 2)
        self.assertEqual(len(box[0]), 2)
        self.assertEqual(len(box[1]), 2)

    def test_observation_package_exports_geo_context_singleton(self) -> None:

        import observation
        from observation import geo_context as package_geo_context

        self.assertIs(package_geo_context, geo_context)
        self.assertIsInstance(package_geo_context, GeoContext)
        self.assertTrue(callable(package_geo_context.coverage_bounding_box))

    def test_registry_distance_uses_haversine_via_geo_context(self) -> None:

        from database.ship_registry import registry

        point = self._manager.create(
            name="Huelva",
            latitude=37.14881,
            longitude=-6.87653,
            coverage_radius_km=25.0,
        )
        self._manager.activate_point(point.id)

        registry.clear()
        registry.add(
            Ship(
                mmsi=1,
                name="near",
                lat=37.149,
                lon=-6.876,
                speed=0,
                course=0,
                heading=0,
                last_seen=datetime.now(),
            )
        )

        ship = registry.get(1)
        self.assertIsNotNone(ship)
        self.assertLess(ship.distance_km, 1.0)


if __name__ == "__main__":
    unittest.main()
