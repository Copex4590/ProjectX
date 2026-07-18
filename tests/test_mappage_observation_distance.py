#!/usr/bin/env python3
"""Regression tests for M-09 observation distance display pipeline."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import importlib

geo_module = importlib.import_module("observation.geo_context")
from gui import mappage
from gui.vesselcard.layouts import monitoring
from models.camera import Camera
from models.ship import Ship
from observation.observation_manager import ObservationManager

HUELVA_LAT = 37.14881
HUELVA_LON = -6.87653
SHIP_LAT = 37.15
SHIP_LON = -6.87


class MappageObservationDistanceTests(unittest.TestCase):

    def setUp(self) -> None:

        self._tmpdir = tempfile.mkdtemp()
        self._path = Path(self._tmpdir) / "observation_points.json"
        self._manager = ObservationManager(path=self._path)
        self._original_geo_manager = geo_module.observation_manager
        geo_module.observation_manager = self._manager

        point = self._manager.create(
            name="Huelva",
            latitude=HUELVA_LAT,
            longitude=HUELVA_LON,
            coverage_radius_km=25.0,
        )
        self._manager.activate_point(point.id)

    def tearDown(self) -> None:

        geo_module.observation_manager = self._original_geo_manager

    def test_display_camera_does_not_fallback_to_nearest_pack_camera(self) -> None:

        ship = Ship(
            mmsi=123,
            name="TEST",
            lat=SHIP_LAT,
            lon=SHIP_LON,
            speed=0,
            course=0,
            heading=0,
            last_seen=datetime.now(),
        )

        camera, distance = mappage._display_camera_for_ship(ship)

        self.assertIsNone(camera)
        self.assertIsNone(distance)

    def test_serialize_ship_uses_reference_distance_not_camera_distance(self) -> None:

        ship = Ship(
            mmsi=456,
            name="NEARBY",
            lat=SHIP_LAT,
            lon=SHIP_LON,
            speed=1.0,
            course=90.0,
            heading=90.0,
            last_seen=datetime.now(),
            distance_km=9999.0,
        )

        payload = mappage._serialize_ship(ship)

        self.assertLess(payload["distance_km"], 5.0)
        self.assertIsNotNone(payload.get("reference_bearing_deg"))
        self.assertIsNone(payload.get("camera_distance_km"))

        html = monitoring.render_monitoring_card(
            payload,
            {"Distance": "Distance", "Direction": "Direction", "North": "North"},
            level="compact",
        )

        self.assertNotIn("9999", html)
        self.assertNotIn("2200", html)

    def test_enrich_camera_fields_only_for_observing_camera(self) -> None:

        ship = Ship(
            mmsi=789,
            name="NEARBY",
            lat=SHIP_LAT,
            lon=SHIP_LON,
            speed=0,
            course=0,
            heading=0,
            last_seen=datetime.now(),
        )

        payload: dict = {}
        mappage._enrich_camera_fields(ship, payload)

        self.assertIsNone(payload.get("camera_distance_km"))
        self.assertIsNone(payload.get("camera_bearing_deg"))


class CameraMatchDistanceTests(unittest.TestCase):

    def test_budapest_camera_distance_to_huelva_ship_is_large(self) -> None:

        camera = Camera(
            id="hu-budapest-duna-north",
            name="Budapest Duna North",
            country="HU",
            lat=47.501539,
            lon=19.039856,
            visibility_radius_km=5.0,
        )

        distance = camera.distance_km_to(SHIP_LAT, SHIP_LON)

        self.assertGreater(distance, 1000.0)


if __name__ == "__main__":
    unittest.main()
