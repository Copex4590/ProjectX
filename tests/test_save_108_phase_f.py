#!/usr/bin/env python3
"""SAVE-108 Phase F — lifecycle, Leaflet retirement, and final transition."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.paths import resource_path
from gui.map_engine import (
    MapEngineKind,
    RendererLifecycleState,
    parse_renderer_lifecycle,
    resolve_map_engine_kind,
)


class Save108PhaseFTests(unittest.TestCase):

    def test_renderer_lifecycle_module_exists(self) -> None:

        source = resource_path(
            "map",
            "engine",
            "cesium",
            "renderer_lifecycle.js",
        ).read_text(encoding="utf-8")

        for method in (
            "initialize",
            "activate",
            "suspend",
            "resume",
            "shutdown",
        ):
            self.assertIn(method, source)

        self.assertIn("createRendererLifecycle", source)

    def test_lifecycle_separate_from_scene_graph_diagnostics_bridge(self) -> None:

        lifecycle = resource_path(
            "map",
            "engine",
            "cesium",
            "renderer_lifecycle.js",
        ).read_text(encoding="utf-8")
        scene_graph = resource_path(
            "map",
            "engine",
            "cesium",
            "scene_graph.js",
        ).read_text(encoding="utf-8")
        diagnostics = resource_path(
            "map",
            "engine",
            "cesium",
            "renderer_diagnostics.js",
        ).read_text(encoding="utf-8")
        contract = resource_path("map", "engine", "contract.js").read_text(
            encoding="utf-8",
        )

        self.assertNotIn("createSceneGraph", lifecycle)
        self.assertNotIn("createRendererDiagnostics", lifecycle)
        self.assertNotIn("createRendererLifecycle", scene_graph)
        self.assertNotIn("createRendererLifecycle", diagnostics)
        self.assertNotIn('"initialize"', contract)

    def test_contract_exposes_get_renderer_lifecycle(self) -> None:

        source = resource_path("map", "engine", "contract.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("getRendererLifecycle", source)

    def test_scene_graph_forwards_lifecycle_to_layers(self) -> None:

        source = resource_path("map", "engine", "cesium", "scene_graph.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("createLifecycleParticipant", source)
        self.assertIn("shutdown", source)

    def test_factory_defaults_to_cesium_only(self) -> None:

        source = resource_path("map", "engine", "factory.js").read_text(
            encoding="utf-8",
        )

        self.assertIn('return "cesium"', source)
        self.assertNotIn("leaflet", source)
        self.assertNotIn("createLeafletEngine", source)

    def test_cesium_engine_wires_lifecycle(self) -> None:

        source = resource_path("map", "engine", "cesium_engine.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("createRendererLifecycle", source)
        self.assertIn("__rendererLifecycle", source)
        self.assertIn("getLifecycle", source)

    def test_leaflet_retired(self) -> None:

        map_root = resource_path("map")

        self.assertFalse((map_root / "engine" / "leaflet_engine.js").exists())
        self.assertFalse((map_root / "leaflet").exists())
        self.assertFalse((map_root / "camera_map.html").exists())
        self.assertFalse((map_root / "observation_map.html").exists())

    def test_legacy_map_widgets_removed(self) -> None:

        widgets = Path(__file__).resolve().parents[1] / "src" / "gui" / "widgets"

        self.assertFalse((widgets / "cameramapwidget.py").exists())
        self.assertFalse((widgets / "observationmapwidget.py").exists())

    def test_resolve_map_engine_kind_is_cesium(self) -> None:

        self.assertEqual(resolve_map_engine_kind(), MapEngineKind.CESIUM)

    def test_parse_renderer_lifecycle(self) -> None:

        state = parse_renderer_lifecycle({"state": "active"})

        self.assertIsInstance(state, RendererLifecycleState)
        self.assertEqual(state.state, "active")

    def test_build_scripts_require_cesium_not_leaflet(self) -> None:

        root = Path(__file__).resolve().parents[1]

        for script in (
            "scripts/build_linux.sh",
            "scripts/build_windows.sh",
            "scripts/build_linux_release.sh",
        ):
            source = (root / script).read_text(encoding="utf-8")
            self.assertIn("cesium", source)
            self.assertNotIn("fetch_leaflet", source)


if __name__ == "__main__":
    unittest.main()
