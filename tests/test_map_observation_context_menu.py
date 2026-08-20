#!/usr/bin/env python3
"""Right-click menu on saved observation points: reuse Control Panel set_active."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gui.map_core import PickMode
from gui.mappage import MapPage
from observation.observation_manager import ObservationManager


ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "src" / "resources" / "map"


class ObservationContextMenuHtmlTests(unittest.TestCase):

    def test_google_observation_reports_context_menu_without_changing_pins(self) -> None:

        google = (MAPS / "google_map_3d.html").read_text(encoding="utf-8")
        observation = google.split("function installObservationPointMarkers")[1].split(
            "</script>"
        )[0]
        catalog = google.split("function installCatalogCameraMarkers")[1].split(
            "</script>"
        )[0]
        ships = google.split('id="ship-overlay"')[1].split("Observation Point markers")[0]

        self.assertIn("window.__projectxProjectLatLng", google)
        self.assertIn("bridge.observationContextMenu", observation)
        self.assertIn(
            'document.addEventListener("contextmenu", onContextMenuCapture, true)',
            observation,
        )
        self.assertIn("observationIdAtClient", observation)
        self.assertIn("__projectxProjectLatLng", observation)
        self.assertIn("reportObservationContextMenu", observation)
        self.assertNotIn("marker.addEventListener", observation)
        self.assertIn("sizePreserved: true", observation)
        self.assertIn("scale: 1.05", observation)
        self.assertIn("#43a047", observation)
        self.assertIn("#e53935", observation)
        self.assertIn("label: name", observation)
        self.assertNotIn("gmp-click", observation)
        self.assertNotIn("selectCamera", observation)

        self.assertNotIn("observationContextMenu", catalog)
        self.assertNotIn("observationContextMenu", ships)

    def test_leaflet_observation_binds_contextmenu_cameras_do_not(self) -> None:

        leaflet = (MAPS / "map.html").read_text(encoding="utf-8")
        observation = leaflet.split("function updateObservationPoints")[1].split(
            "function updateCatalogCameras"
        )[0]
        catalog = leaflet.split("VALIDATED camera markers")[1]

        self.assertIn("reportObservationContextMenu", observation)
        self.assertIn('"contextmenu"', observation)
        self.assertIn("observation-marker--active", leaflet)
        self.assertNotIn("observationContextMenu", catalog)
        self.assertIn("bridge.selectCamera", catalog)


class ObservationContextMenuMapPageTests(unittest.TestCase):

    def _page(self) -> MapPage:

        page = MapPage.__new__(MapPage)
        page.map = MagicMock()
        page._map_controller = MagicMock()
        page._map_controller.pick_mode.return_value = PickMode.NONE
        return page

    def test_menu_select_calls_set_active(self) -> None:

        page = self._page()
        point = MagicMock()
        point.id = "op-b"
        point.name = "Budapest"
        action = MagicMock()
        menu = MagicMock()
        menu.addAction.side_effect = [MagicMock(), action]
        menu.exec.return_value = action

        with patch("gui.mappage.observation_manager") as manager:
            manager.get.return_value = point
            manager.active.return_value = MagicMock(id="op-a")
            with patch("gui.mappage.QMenu", return_value=menu):
                with patch("gui.mappage.QCursor"):
                    page._on_observation_context_menu("op-b")

        manager.set_active.assert_called_once_with("op-b")

    def test_already_active_does_not_call_set_active(self) -> None:

        page = self._page()

        with patch("gui.mappage.observation_manager") as manager:
            manager.active.return_value = MagicMock(id="op-a")
            page._activate_observation_point("op-a")
            manager.set_active.assert_not_called()

    def test_location_pick_ignores_context_menu(self) -> None:

        page = self._page()
        page._map_controller.pick_mode.return_value = PickMode.LOCATION

        with patch("gui.mappage.observation_manager") as manager:
            with patch("gui.mappage.QMenu") as menu_ctor:
                page._on_observation_context_menu("op-b")

        manager.get.assert_not_called()
        menu_ctor.assert_not_called()

    def test_unknown_point_does_not_open_menu(self) -> None:

        page = self._page()

        with patch("gui.mappage.observation_manager") as manager:
            manager.get.return_value = None
            with patch("gui.mappage.QMenu") as menu_ctor:
                page._on_observation_context_menu("missing")

        menu_ctor.assert_not_called()
        manager.set_active.assert_not_called()

    def test_activate_matches_control_panel_set_active(self) -> None:

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "observation_points.json"
            manager = ObservationManager(path=path)
            first = manager.create(
                name="First",
                latitude=47.5,
                longitude=19.0,
                coverage_radius_km=25.0,
            )
            second = manager.create(
                name="Second",
                latitude=47.6,
                longitude=19.1,
                coverage_radius_km=25.0,
                set_active=False,
            )
            self.assertEqual(manager.active().id, first.id)

            page = self._page()
            with patch("gui.mappage.observation_manager", manager):
                page._activate_observation_point(second.id)

            active = manager.active()
            self.assertIsNotNone(active)
            self.assertEqual(active.id, second.id)
            self.assertTrue(active.active)
            self.assertFalse(manager.get(first.id).active)


if __name__ == "__main__":
    unittest.main()
