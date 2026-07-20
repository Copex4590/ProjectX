#!/usr/bin/env python3
"""SAVE-108 Phase E — renderer diagnostics and performance polish verification."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.paths import resource_path
from gui.map_engine import RendererDiagnostics, parse_renderer_diagnostics


class Save108PhaseETests(unittest.TestCase):

    def test_renderer_diagnostics_module_exists(self) -> None:

        source = resource_path(
            "map",
            "engine",
            "cesium",
            "renderer_diagnostics.js",
        ).read_text(encoding="utf-8")

        self.assertIn("createRendererDiagnostics", source)
        self.assertIn("fps", source)
        self.assertIn("frame_time_ms", source)
        self.assertIn("bridge_latency_ms", source)
        self.assertIn("entity_counts", source)
        self.assertIn("memory_estimate", source)
        self.assertIn("camera_state", source)
        self.assertIn("transaction_queue_depth", source)

    def test_diagnostics_separate_from_scene_graph_and_transaction(self) -> None:

        diagnostics = resource_path(
            "map",
            "engine",
            "cesium",
            "renderer_diagnostics.js",
        ).read_text(encoding="utf-8")
        scene_graph = resource_path(
            "map",
            "engine",
            "cesium",
            "scene_graph.js",
        ).read_text(encoding="utf-8")
        transaction = resource_path(
            "map",
            "engine",
            "cesium",
            "render_transaction.js",
        ).read_text(encoding="utf-8")

        self.assertNotIn("createSceneGraph", diagnostics)
        self.assertNotIn("createRenderTransaction", diagnostics)
        self.assertNotIn("createRendererDiagnostics", scene_graph)
        self.assertNotIn("createRendererDiagnostics", transaction)

    def test_contract_exposes_get_renderer_diagnostics(self) -> None:

        source = resource_path("map", "engine", "contract.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("getRendererDiagnostics", source)
        self.assertNotIn('"getRendererDiagnostics"', source)

    def test_entity_pool_module_exists(self) -> None:

        source = resource_path(
            "map",
            "engine",
            "cesium",
            "entity_pool.js",
        ).read_text(encoding="utf-8")

        self.assertIn("createEntityPool", source)

    def test_ship_layer_uses_pool_and_large_fleet_optimization(self) -> None:

        source = resource_path("map", "engine", "cesium", "ship_layer.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("createEntityPool", source)
        self.assertIn("LARGE_FLEET_THRESHOLD", source)
        self.assertIn("CesiumViewport.isPointInView", source)
        self.assertIn("distanceDisplayCondition", source)

    def test_render_transaction_exposes_queue_depth(self) -> None:

        source = resource_path(
            "map",
            "engine",
            "cesium",
            "render_transaction.js",
        ).read_text(encoding="utf-8")

        self.assertIn("queueDepth", source)

    def test_camera_layer_uses_smoothing(self) -> None:

        source = resource_path(
            "map",
            "engine",
            "cesium",
            "camera_layer.js",
        ).read_text(encoding="utf-8")

        self.assertIn("EasingFunction.QUADRATIC_IN_OUT", source)

    def test_popup_layer_throttles_position_updates(self) -> None:

        source = resource_path(
            "map",
            "engine",
            "cesium",
            "popup_layer.js",
        ).read_text(encoding="utf-8")

        self.assertIn("POSITION_INTERVAL_FRAMES", source)
        self.assertIn("cachedHtml", source)

    def test_scene_graph_entity_counts(self) -> None:

        source = resource_path("map", "engine", "cesium", "scene_graph.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("entityCounts", source)
        self.assertIn("cleanup", source)

    def test_parse_renderer_diagnostics(self) -> None:

        payload = {
            "fps": 59.5,
            "frame_time_ms": 16.7,
            "bridge_latency_ms": 1.2,
            "entity_counts": {"ships": 42, "ship_pool": 3},
            "memory_estimate": 12345678,
            "camera_state": {"height_m": 2500.0},
            "transaction_queue_depth": 2,
        }

        diagnostics = parse_renderer_diagnostics(payload)

        self.assertIsInstance(diagnostics, RendererDiagnostics)
        self.assertEqual(diagnostics.fps, 59.5)
        self.assertEqual(diagnostics.entity_counts["ships"], 42)
        self.assertEqual(diagnostics.memory_estimate, 12345678)
        self.assertEqual(diagnostics.transaction_queue_depth, 2)

    def test_mapwidget_exposes_renderer_diagnostics(self) -> None:

        source = Path(__file__).resolve().parents[1].joinpath(
            "src",
            "gui",
            "widgets",
            "mapwidget.py",
        ).read_text(encoding="utf-8")

        self.assertIn("renderer_diagnostics", source)
        self.assertIn("fetch_renderer_diagnostics", source)


if __name__ == "__main__":
    unittest.main()
