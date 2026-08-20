#!/usr/bin/env python3
"""VALIDATED camera map layer: JSON read-only, icon markers, existing Hunter click path."""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from camera_hunter.engine.catalog_validation import ValidationRecord, ValidationStatus
from cameras.validated_catalog import (
    load_validated_layer,
    should_publish_markers,
    validated_camera_markers,
    validation_json_path,
)
from gui.mappage import MapPage, _catalog_camera_markers


ROOT = Path(__file__).resolve().parents[1]


def _record(**overrides) -> ValidationRecord:

    values = {
        "camera_id": "id:ok",
        "name": "OK Cam",
        "lat": 47.498993,
        "lon": 19.043699,
        "web_url": "https://www.earthcam.com/world/hungary/budapest/",
        "status": ValidationStatus.VALIDATED,
        "playback_ok": True,
    }
    values.update(overrides)
    return ValidationRecord(**values)


class ValidatedMarkerPayloadTests(unittest.TestCase):

    def test_only_validated_cameras_are_kept(self) -> None:

        markers = validated_camera_markers(
            [
                _record(camera_id="id:ok"),
                _record(
                    camera_id="id:timeout",
                    status=ValidationStatus.TIMEOUT,
                    playback_ok=False,
                ),
                _record(
                    camera_id="id:error",
                    status=ValidationStatus.ERROR,
                    playback_ok=False,
                ),
                _record(
                    camera_id="id:failed",
                    status=ValidationStatus.PLAYBACK_FAILED,
                    playback_ok=False,
                ),
            ]
        )
        self.assertEqual([item["id"] for item in markers], ["id:ok"])
        self.assertEqual(set(markers[0]), {"id", "lat", "lon"})
        self.assertNotIn("name", markers[0])
        self.assertNotIn("web_url", markers[0])

    def test_keeps_validated_lat_lon_and_id(self) -> None:

        markers = _catalog_camera_markers(
            [_record(camera_id="hu-budapest-chainbridge", name="Chain Bridge")]
        )
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["id"], "hu-budapest-chainbridge")
        self.assertAlmostEqual(markers[0]["lat"], 47.498993)
        self.assertAlmostEqual(markers[0]["lon"], 19.043699)
        self.assertNotIn("name", markers[0])

    def test_skips_missing_coordinates(self) -> None:

        markers = validated_camera_markers(
            [
                _record(camera_id="zero", lat=0.0, lon=0.0),
                _record(camera_id="nan", lat=float("nan"), lon=19.0),
                _record(camera_id="bad-lon", lat=47.5, lon=200.0),
                _record(camera_id="ok", lat=47.5, lon=19.0),
            ]
        )
        self.assertEqual([item["id"] for item in markers], ["ok"])
        self.assertFalse(any(math.isnan(item["lat"]) for item in markers))

    def test_same_camera_is_not_duplicated(self) -> None:

        markers = validated_camera_markers(
            [
                _record(camera_id="id:dup", lat=47.5, lon=19.0),
                _record(camera_id="id:dup", lat=48.0, lon=19.0),
            ]
        )
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["id"], "id:dup")

    def test_empty_input(self) -> None:

        self.assertEqual(validated_camera_markers([]), [])
        self.assertEqual(validated_camera_markers(None), [])

    def test_first_read_publishes_even_if_fingerprint_matches_empty(self) -> None:

        empty = ()
        self.assertTrue(
            should_publish_markers(empty, empty, published=False)
        )
        self.assertFalse(
            should_publish_markers(empty, empty, published=True)
        )
        self.assertTrue(
            should_publish_markers((("id:a", 1.0, 2.0),), empty, published=True)
        )


class ValidatedJsonLayerTests(unittest.TestCase):

    def test_refresh_picks_up_new_validated_and_drops_non_validated(self) -> None:

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hunter_catalog_validation.json"
            path.write_text(
                json.dumps(
                    {
                        "cameras": [
                            _record(camera_id="id:a").to_dict(),
                            _record(
                                camera_id="id:timeout",
                                status=ValidationStatus.TIMEOUT,
                            ).to_dict(),
                        ]
                    }
                ),
                encoding="utf-8",
            )
            first, index = load_validated_layer(path)
            self.assertEqual([item["id"] for item in first], ["id:a"])
            self.assertIn("id:a", index)
            path.write_text(
                json.dumps(
                    {
                        "cameras": [
                            _record(camera_id="id:a").to_dict(),
                            _record(camera_id="id:b", name="Later").to_dict(),
                            _record(
                                camera_id="id:timeout",
                                status=ValidationStatus.TIMEOUT,
                            ).to_dict(),
                        ]
                    }
                ),
                encoding="utf-8",
            )
            second, index = load_validated_layer(path)
        self.assertEqual([item["id"] for item in second], ["id:a", "id:b"])
        self.assertEqual(
            index["id:b"].web_url,
            "https://www.earthcam.com/world/hungary/budapest/",
        )

    def test_load_opens_json_read_only(self) -> None:

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hunter_catalog_validation.json"
            path.write_text(
                json.dumps({"cameras": [_record().to_dict()]}),
                encoding="utf-8",
            )
            modes: list[str] = []
            real_open = Path.open

            def tracking_open(self, mode="r", *args, **kwargs):
                modes.append(str(mode))
                return real_open(self, mode, *args, **kwargs)

            with patch.object(Path, "open", tracking_open):
                load_validated_layer(path)
        self.assertTrue(modes)
        self.assertTrue(
            all("w" not in mode and "a" not in mode and "+" not in mode for mode in modes)
        )


class CatalogCameraMapHtmlTests(unittest.TestCase):

    def test_google_and_leaflet_use_icon_only_select_camera(self) -> None:

        maps = ROOT / "src" / "resources" / "map"
        google = (maps / "google_map_3d.html").read_text(encoding="utf-8")
        leaflet = (maps / "map.html").read_text(encoding="utf-8")
        catalog = google.split("function installCatalogCameraMarkers")[1].split(
            "</script>"
        )[0]
        leaflet_catalog = leaflet.split("VALIDATED camera markers")[1]

        self.assertIn("function updateCatalogCameras", google)
        self.assertIn("Marker3DInteractiveElement", catalog)
        self.assertIn("new Marker3DInteractiveElement", catalog)
        self.assertNotIn("new Marker3DElement", catalog)
        self.assertIn("sizePreserved: true", catalog)
        self.assertIn("bridge.selectCamera", catalog)
        self.assertIn("makeCameraGlyph", catalog)
        self.assertIn("new PinElement", catalog)
        self.assertIn("scale: 1.05", catalog)
        self.assertNotIn("label: name", catalog)
        self.assertNotIn("#485da2", catalog)
        self.assertNotIn('createElement("img")', catalog)
        self.assertNotIn("makeCameraIcon", catalog)

        self.assertIn("function updateCatalogCameras", leaflet)
        self.assertIn("bridge.selectCamera", leaflet_catalog)
        self.assertIn("<svg", leaflet_catalog)
        self.assertNotIn("bindTooltip", leaflet_catalog)
        self.assertNotIn("catalog-camera-marker", leaflet)
        self.assertNotIn("start_hunter", google)
        self.assertNotIn("start_hunter", leaflet)
        self.assertNotIn("__PROJECTX_FIXED_MARKER_SCREEN_PX", google)

        observation = google.split("function installObservationPointMarkers")[1].split(
            "</script>"
        )[0]
        self.assertIn("sizePreserved: true", observation)
        self.assertIn("scale: 1.05", observation)
        self.assertIn("#43a047", observation)
        self.assertIn("#e53935", observation)

        pick = google.split("function placePickMarker")[1].split("function setPickMarker")[0]
        self.assertNotIn("sizePreserved", pick)

        ship_overlay = google.split('id="ship-overlay"')[1].split(
            "Observation Point markers"
        )[0]
        self.assertNotIn("sizePreserved", ship_overlay)


class MapPageValidatedCameraTests(unittest.TestCase):

    def test_push_now_uses_loaded_markers_without_waiting_for_signal(self) -> None:

        page = MapPage.__new__(MapPage)
        page.map = MagicMock()
        page._validated_catalog = MagicMock()
        page._validated_catalog.has_loaded = True
        page._validated_catalog.current_markers.return_value = [
            {"id": "keep", "lat": 47.5, "lon": 19.04}
        ]
        page._push_validated_cameras_now()
        page.map.set_cameras.assert_called_once_with(
            [{"id": "keep", "lat": 47.5, "lon": 19.04}]
        )

    def test_signal_still_pushes_markers_to_map(self) -> None:

        page = MapPage.__new__(MapPage)
        page.map = MagicMock()
        markers = [{"id": "keep", "lat": 47.5, "lon": 19.04}]
        page._on_validated_cameras_updated(markers)
        page.map.set_cameras.assert_called_once_with(markers)

    def test_push_now_skips_empty_before_first_json_read(self) -> None:

        page = MapPage.__new__(MapPage)
        page.map = MagicMock()
        page._validated_catalog = MagicMock()
        page._validated_catalog.has_loaded = False
        page._validated_catalog.current_markers.return_value = []
        page._push_validated_cameras_now()
        page.map.set_cameras.assert_not_called()

    def test_refresh_skips_when_map_missing(self) -> None:

        page = MapPage.__new__(MapPage)
        page.map = None
        page._validated_catalog = MagicMock()
        page._refresh_catalog_camera_markers()
        page._validated_catalog.refresh.assert_not_called()

    def test_refresh_delegates_to_validated_service(self) -> None:

        page = MapPage.__new__(MapPage)
        page.map = MagicMock()
        page._validated_catalog = MagicMock()
        page._refresh_catalog_camera_markers()
        page._validated_catalog.refresh.assert_called_once()

    def test_camera_selected_uses_validation_web_url_for_hunter_discovery(self) -> None:

        source = ROOT / "src" / "gui" / "mappage.py"
        text = source.read_text(encoding="utf-8")
        self.assertIn("cameraSelected.connect", text)
        self.assertIn("self.start_hunter_camera_discovery(page_url)", text)
        handler = text.split("def _on_catalog_camera_selected")[1].split("def ")[0]
        self.assertIn("web_url_for", handler)
        self.assertNotIn("camera_manager", handler)
        self.assertNotIn("thumbnail", handler)
        self.assertNotIn("snapshot_url", handler)

    def test_catalog_click_starts_existing_hunter_path(self) -> None:

        page = MapPage.__new__(MapPage)
        page.start_hunter_camera_discovery = MagicMock(return_value=True)
        page._validated_catalog = MagicMock()
        page._validated_catalog.web_url_for.return_value = (
            "https://www.earthcam.com/world/hungary/budapest/"
        )
        page._on_catalog_camera_selected("id:abc")
        page.start_hunter_camera_discovery.assert_called_once_with(
            "https://www.earthcam.com/world/hungary/budapest/"
        )
        page._validated_catalog.web_url_for.assert_called_once_with("id:abc")

    def test_px_does_not_start_catalog_validator_or_listing_scan(self) -> None:

        mappage = (ROOT / "src" / "gui" / "mappage.py").read_text(encoding="utf-8")
        catalog = (ROOT / "src" / "cameras" / "validated_catalog.py").read_text(
            encoding="utf-8"
        )
        combined = mappage + "\n" + catalog
        self.assertNotIn("from camera_hunter.app.catalog_validator", combined)
        self.assertNotIn("from camera_hunter.catalog_validator", combined)
        self.assertNotIn("CatalogValidationScanner", combined)
        self.assertNotIn("hunter_listing_catalog_service.start", mappage)
        self.assertIn("ValidatedCatalogService", mappage)
        self.assertIn("QueuedConnection", mappage)
        self.assertIn("_push_validated_cameras_now", mappage)
        self.assertIn('getattr(self.map, "_page_ready", False)', mappage)
        widget = (ROOT / "src" / "gui" / "widgets" / "mapwidget.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("QTimer.singleShot(0, self._flush_catalog_cameras)", widget)
        self.assertIn("if self._pending_cameras is None:", widget)
        self.assertIn("DEFAULT_REFRESH_MS = 30_000", catalog)
        self.assertIn("QueuedConnection", catalog)
        self.assertIn("should_publish_markers", catalog)
        self.assertIn("load_validated_records", catalog)
        self.assertNotIn(".save(", catalog)
        self.assertNotIn(".put(", catalog)

    def test_start_hunter_discovery_stops_prior_session_before_discover(self) -> None:

        source = ROOT / "src" / "gui" / "widgets" / "camerapreviewpanel.py"
        method = source.read_text(encoding="utf-8").split(
            "def start_hunter_discovery"
        )[1].split("def ")[0]
        self.assertIn("self._hunter.stop()", method)
        self.assertLess(
            method.index("self._hunter.stop()"),
            method.index("self._hunter.discover"),
        )
        self.assertLess(
            method.index("self._hunter.stop()"),
            method.index("_show_hunter_chrome"),
        )

    def test_validation_json_path_is_the_validator_cache_file(self) -> None:

        self.assertEqual(validation_json_path().name, "hunter_catalog_validation.json")


if __name__ == "__main__":
    unittest.main()
