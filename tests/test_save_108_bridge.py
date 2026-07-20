#!/usr/bin/env python3
"""SAVE-108 bridge handshake and Phase B verification."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.paths import resource_path
from gui.map_engine import (
    BRIDGE_ENTRY_POINTS,
    SUPPORTED_BRIDGE_VERSION,
    BridgeVersionError,
    MapEngineKind,
    default_capabilities,
    parse_bridge_info,
    verify_bridge_info,
)


def _bridge_payload(
    *,
    version: int = SUPPORTED_BRIDGE_VERSION,
    engine: str = "cesium",
    entry_points: list[str] | None = None,
) -> dict:
    caps = default_capabilities()
    return {
        "version": version,
        "engine": engine,
        "capabilities": {
            "supports_globe": caps.supports_globe,
            "supports_pitch": caps.supports_pitch,
            "supports_heading": caps.supports_heading,
            "supports_geodesic": caps.supports_geodesic,
            "supports_terrain": caps.supports_terrain,
            "engine_id": caps.engine_id,
        },
        "entry_points": entry_points or sorted(BRIDGE_ENTRY_POINTS),
    }


class Save108BridgeHandshakeTests(unittest.TestCase):

    def test_supported_bridge_version_is_one(self) -> None:

        self.assertEqual(SUPPORTED_BRIDGE_VERSION, 1)

    def test_verify_bridge_info_accepts_supported_version(self) -> None:

        info = parse_bridge_info(_bridge_payload(engine="cesium"))
        verify_bridge_info(info, expected_engine=MapEngineKind.CESIUM)

    def test_verify_bridge_info_rejects_unsupported_version(self) -> None:

        info = parse_bridge_info(_bridge_payload(version=2))

        with self.assertRaises(BridgeVersionError):
            verify_bridge_info(info, expected_engine=MapEngineKind.CESIUM)

    def test_verify_bridge_info_rejects_engine_mismatch(self) -> None:

        info = parse_bridge_info(_bridge_payload(engine="leaflet"))

        with self.assertRaises(BridgeVersionError):
            verify_bridge_info(info, expected_engine=MapEngineKind.CESIUM)

    def test_verify_bridge_info_rejects_missing_entry_points(self) -> None:

        info = parse_bridge_info(_bridge_payload(entry_points=["updateShips"]))

        with self.assertRaises(BridgeVersionError):
            verify_bridge_info(info, expected_engine=MapEngineKind.CESIUM)

    def test_parse_bridge_info_rejects_invalid_capabilities(self) -> None:

        payload = _bridge_payload()
        payload["capabilities"] = {"engine_id": "cesium"}

        with self.assertRaises(BridgeVersionError):
            parse_bridge_info(payload)


class Save108PhaseBTests(unittest.TestCase):

    def test_cesium_capabilities_include_globe_features(self) -> None:

        caps = default_capabilities()

        self.assertTrue(caps.supports_globe)
        self.assertTrue(caps.supports_pitch)
        self.assertTrue(caps.supports_heading)
        self.assertTrue(caps.supports_geodesic)
        self.assertFalse(caps.supports_terrain)

    def test_cesium_engine_declares_incremental_ship_api(self) -> None:

        source = resource_path("map", "engine", "cesium", "ship_layer.js").read_text(
            encoding="utf-8",
        )

        for symbol in ("addShip", "updateShip", "removeShip", "clearShips"):
            self.assertIn(f"function {symbol}", source)

    def test_cesium_engine_wires_maptiler_streets_imagery(self) -> None:

        source = resource_path("map", "engine", "cesium_engine.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("api.maptiler.com/maps/streets-v2", source)
        self.assertIn("ImageryLayer.fromProviderAsync", source)
        self.assertIn("__PROJECTX_MAPTILER_API_KEY__", source)
        self.assertNotIn("fromWorldImagery", source)
        self.assertNotIn("tile.openstreetmap.org", source)
        self.assertNotIn("imageryProvider:", source)

    def test_cesium_engine_does_not_draw_coverage_in_engine_shell(self) -> None:

        source = resource_path("map", "engine", "cesium_engine.js").read_text(
            encoding="utf-8",
        )

        self.assertNotIn("EllipseGraphics", source)
        self.assertIn("coverageLayer", source)

    def test_factory_loads_cesium_assets(self) -> None:

        source = resource_path("map", "engine", "factory.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("ensureCesiumLoaded", source)
        self.assertIn("cesium/Cesium.js", source)
        self.assertNotIn("leaflet", source)

    def test_contract_exposes_bridge_info(self) -> None:

        source = resource_path("map", "engine", "contract.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("getBridgeInfo", source)
        self.assertIn("entry_points", source)

    def test_fetch_cesium_script_exists(self) -> None:

        script = Path(__file__).resolve().parents[1] / "scripts" / "fetch_cesium.sh"
        self.assertTrue(script.is_file())

    def test_cesium_bundle_present_when_fetched(self) -> None:

        cesium_js = resource_path("map", "cesium", "Cesium.js")

        if not cesium_js.is_file():
            self.skipTest(
                "Cesium bundle not present; run scripts/fetch_cesium.sh first."
            )

        self.assertTrue(cesium_js.stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
