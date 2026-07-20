#!/usr/bin/env python3
"""SAVE-108 Phase A — map engine abstraction verification."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.paths import resource_path
from gui.map_engine import (
    BRIDGE_ENTRY_POINTS,
    MapEngineKind,
    RenderCapabilities,
    default_capabilities,
    parse_render_capabilities,
    resolve_map_engine_kind,
)


class Save108PhaseATests(unittest.TestCase):

    def test_resolve_map_engine_kind_defaults_to_cesium(self) -> None:

        self.assertEqual(resolve_map_engine_kind(), MapEngineKind.CESIUM)

    def test_default_capabilities_cesium(self) -> None:

        caps = default_capabilities()

        self.assertTrue(caps.supports_globe)
        self.assertTrue(caps.supports_pitch)
        self.assertTrue(caps.supports_heading)
        self.assertTrue(caps.supports_geodesic)
        self.assertFalse(caps.supports_terrain)
        self.assertEqual(caps.engine_id, MapEngineKind.CESIUM)

    def test_parse_render_capabilities(self) -> None:

        caps = parse_render_capabilities({
            "supports_globe": True,
            "supports_pitch": False,
            "supports_heading": True,
            "supports_geodesic": True,
            "supports_terrain": False,
            "engine_id": "cesium",
        })

        self.assertEqual(
            caps,
            RenderCapabilities(
                supports_globe=True,
                supports_pitch=False,
                supports_heading=True,
                supports_geodesic=True,
                supports_terrain=False,
                engine_id="cesium",
            ),
        )

    def test_bridge_entry_points_include_frozen_contract(self) -> None:

        required = {
            "updateShips",
            "removeShip",
            "clearShips",
            "updateObservationPoints",
            "clearObservationPoints",
            "focusShip",
            "setPickMode",
            "resetMapToWorldView",
        }

        self.assertTrue(required.issubset(BRIDGE_ENTRY_POINTS))

    def test_map_engine_resources_exist(self) -> None:

        map_html = resource_path("map", "map.html")
        self.assertTrue(map_html.is_file())

        for name in (
            "contract.js",
            "factory.js",
            "cesium_engine.js",
        ):
            path = resource_path("map", "engine", name)
            self.assertTrue(path.is_file(), msg=f"missing engine resource: {name}")

        self.assertFalse(
            resource_path("map", "engine", "leaflet_engine.js").exists()
        )

    def test_map_html_bootstraps_engine_layer(self) -> None:

        html = resource_path("map", "map.html").read_text(encoding="utf-8")

        self.assertIn('src="engine/contract.js"', html)
        self.assertIn('src="engine/cesium_engine.js"', html)
        self.assertIn('src="engine/factory.js"', html)
        self.assertIn("bootstrapMapEngine().catch", html)
        self.assertNotIn("leaflet.js", html)
        self.assertNotIn("function updateShips(", html)


if __name__ == "__main__":
    unittest.main()
