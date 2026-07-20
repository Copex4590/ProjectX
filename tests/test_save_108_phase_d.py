#!/usr/bin/env python3
"""SAVE-108 Phase D — heading visualization and render transaction verification."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.paths import resource_path
from gui.map_core import PickMode
from gui.map_engine import BRIDGE_ENTRY_POINTS, MapEngineKind, default_capabilities


class Save108PhaseDTests(unittest.TestCase):

    def test_pick_mode_includes_heading(self) -> None:

        self.assertEqual(PickMode.HEADING.value, "heading")

    def test_bridge_includes_phase_d_entry_points(self) -> None:

        required = {
            "updateCameras",
            "clearCameras",
            "beginHeadingPick",
            "endHeadingPick",
            "setCameraPreview",
        }

        self.assertTrue(required.issubset(BRIDGE_ENTRY_POINTS))

    def test_cesium_capabilities_include_heading(self) -> None:

        caps = default_capabilities(MapEngineKind.CESIUM)

        self.assertTrue(caps.supports_heading)

    def test_render_transaction_module_exists(self) -> None:

        source = resource_path(
            "map",
            "engine",
            "cesium",
            "render_transaction.js",
        ).read_text(encoding="utf-8")

        self.assertIn("createRenderTransaction", source)
        self.assertIn("queueShips", source)
        self.assertIn("queueMicrotask", source)

    def test_scene_graph_includes_phase_d_layers(self) -> None:

        source = resource_path("map", "engine", "cesium", "scene_graph.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("bearingLayer", source)
        self.assertIn("cameraFrustumLayer", source)
        self.assertIn("navigationLayer", source)

    def test_camera_frustum_layer_renders_fov_wedge(self) -> None:

        source = resource_path(
            "map",
            "engine",
            "cesium",
            "camera_frustum_layer.js",
        ).read_text(encoding="utf-8")

        self.assertIn("fov_deg", source)
        self.assertIn("heading_deg", source)
        self.assertIn("setVisible", source)

    def test_ship_layer_renders_heading_vectors(self) -> None:

        source = resource_path("map", "engine", "cesium", "ship_layer.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("updateHeadingVector", source)
        self.assertIn("HEADING_VECTOR_KM", source)

    def test_mapcontroller_serializes_cameras(self) -> None:

        source = Path(__file__).resolve().parents[1].joinpath(
            "src", "gui", "mapcontroller.py"
        ).read_text(encoding="utf-8")

        self.assertIn("def refresh_cameras", source)
        self.assertIn("heading_deg", source)
        self.assertIn("begin_heading_pick", source)


if __name__ == "__main__":
    unittest.main()
