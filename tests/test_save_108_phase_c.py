#!/usr/bin/env python3
"""SAVE-108 Phase C — geodesic coverage verification."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.paths import resource_path
from gui.map_engine import MapEngineKind, default_capabilities


def _haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    earth_radius_km = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )

    return earth_radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class Save108PhaseCTests(unittest.TestCase):

    def test_cesium_capabilities_include_geodesic_coverage(self) -> None:

        caps = default_capabilities(MapEngineKind.CESIUM)

        self.assertTrue(caps.supports_geodesic)
        self.assertFalse(caps.supports_terrain)

    def test_scene_graph_layers_exist(self) -> None:

        for name in (
            "scene_graph.js",
            "ship_layer.js",
            "observation_layer.js",
            "coverage_layer.js",
            "bearing_layer.js",
            "camera_frustum_layer.js",
            "popup_layer.js",
            "camera_layer.js",
            "geodesic.js",
            "render_transaction.js",
        ):
            path = resource_path("map", "engine", "cesium", name)
            self.assertTrue(path.is_file(), msg=f"missing layer: {name}")

    def test_cesium_engine_delegates_to_scene_graph(self) -> None:

        source = resource_path("map", "engine", "cesium_engine.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("createSceneGraph", source)
        self.assertIn("scene.coverageLayer", source)
        self.assertNotIn("function addShip", source)

    def test_coverage_layer_uses_geodesic_ellipse(self) -> None:

        source = resource_path("map", "engine", "cesium", "coverage_layer.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("EllipseGraphics", source)
        self.assertIn("CLAMP_TO_GROUND", source)
        self.assertIn("setVisible", source)
        self.assertIn("sync", source)

    def test_geodesic_helpers_gate_reference_coverage(self) -> None:

        source = resource_path("map", "engine", "cesium", "geodesic.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("shouldRenderCoverage", source)
        self.assertIn("coverage_visible", source)
        self.assertIn("coverage_radius_km", source)

    def test_haversine_boundary_matches_geo_context_radius(self) -> None:

        origin_lat = 47.5
        origin_lon = 19.0
        radius_km = 25.0

        north_lat = origin_lat + (radius_km / 111.0)
        distance = _haversine_distance_km(origin_lat, origin_lon, north_lat, origin_lon)

        self.assertAlmostEqual(distance, radius_km, delta=0.5)

    def test_mapcontroller_serializes_geo_context_fields(self) -> None:

        source = Path(__file__).resolve().parents[1].joinpath(
            "src", "gui", "mapcontroller.py"
        ).read_text(encoding="utf-8")

        self.assertIn("geo_context.coverage_bounding_box", source)
        self.assertIn("coverage_visible", source)
        self.assertIn("coverage_bbox", source)

    def test_map_html_loads_scene_graph_layers(self) -> None:

        html = resource_path("map", "map.html").read_text(encoding="utf-8")

        self.assertIn('src="engine/cesium/scene_graph.js"', html)
        self.assertIn('src="engine/cesium/coverage_layer.js"', html)


if __name__ == "__main__":
    unittest.main()
