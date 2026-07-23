#!/usr/bin/env python3
"""Tests for MapPage ship rendering gate and EventBus wiring."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gui.map_core import PickMode
from gui.mappage import MapPage


class MapPageShipUpdateGateTests(unittest.TestCase):

    def _page(self) -> MapPage:

        page = MapPage.__new__(MapPage)
        page._map_controller = MagicMock()
        page._ships_update_busy = False
        page._ship_refresh_generation = 0
        page._selected_mmsi = None
        page._marker_timer = MagicMock()
        page._popup_timer = MagicMock()
        page.camera_preview = MagicMock()
        return page

    def test_map_updates_disabled_during_location_pick(self) -> None:

        page = self._page()
        page._map_controller.pick_mode.return_value = PickMode.LOCATION

        with patch.object(MapPage, "_map_page_is_current", return_value=True):
            with patch.object(MapPage, "isVisible", return_value=True):
                self.assertFalse(page._map_updates_enabled())

    def test_map_updates_enabled_when_map_visible_and_not_picking(self) -> None:

        page = self._page()
        page._map_controller.pick_mode.return_value = PickMode.NONE

        with patch.object(MapPage, "_map_page_is_current", return_value=True):
            with patch.object(MapPage, "isVisible", return_value=True):
                self.assertTrue(page._map_updates_enabled())

    def test_on_ship_updated_skips_during_location_pick(self) -> None:

        page = self._page()
        page._map_controller.pick_mode.return_value = PickMode.LOCATION

        with patch.object(MapPage, "_map_page_is_current", return_value=True):
            with patch.object(MapPage, "isVisible", return_value=True):
                with patch.object(MapPage, "_update_ship_markers") as marker_update:
                    page.on_ship_updated()
                    marker_update.assert_not_called()

    def test_on_ship_updated_publishes_when_monitoring(self) -> None:

        page = self._page()
        page._map_controller.pick_mode.return_value = PickMode.NONE
        page._markers_dirty = False
        page._marker_timer.isActive.return_value = True

        with patch.object(MapPage, "_map_page_is_current", return_value=True):
            with patch.object(MapPage, "isVisible", return_value=True):
                page.on_ship_updated()
                self.assertTrue(page._markers_dirty)


class MapControllerStalePickTests(unittest.TestCase):

    def test_clear_stale_pick_mode_clears_orphaned_location_mode(self) -> None:

        from gui.mapcontroller import MapController

        controller = MapController.__new__(MapController)
        controller._pick_mode = PickMode.LOCATION
        controller._location_pick_callback = None
        controller._pending_pick_host = None
        controller._pending_pick_message = None
        controller._pick_host = None
        controller._pick_host_was_modal = False
        controller._widget = MagicMock()

        with patch.object(MapController, "cancel_pick_mode") as cancel_pick:
            controller.clear_stale_pick_mode()
            cancel_pick.assert_called_once_with(restore_host=False)

    def test_clear_stale_pick_mode_keeps_active_pick_session(self) -> None:

        from gui.mapcontroller import MapController

        controller = MapController.__new__(MapController)
        controller._pick_mode = PickMode.LOCATION
        controller._location_pick_callback = lambda lat, lon: None

        with patch.object(MapController, "cancel_pick_mode") as cancel_pick:
            controller.clear_stale_pick_mode()
            cancel_pick.assert_not_called()


if __name__ == "__main__":
    unittest.main()
