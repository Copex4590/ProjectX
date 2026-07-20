#!/usr/bin/env python3
"""Regression tests for import-time storage isolation before first-run setup."""

from __future__ import annotations

import importlib
import os
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preferences.preferences import Preferences
from storage.exceptions import DataDirectoryNotConfiguredError


class ImportTimeStorageIsolationTests(unittest.TestCase):

    def _fresh_install_context(self) -> ExitStack:
        stack = ExitStack()
        stack.enter_context(patch.dict(os.environ, {}, clear=True))
        stack.enter_context(
            patch(
                "app.startup_mode.preferences_manager.get",
                return_value=Preferences.defaults(),
            )
        )
        stack.enter_context(patch("storage.manager.configured_data_root", return_value=None))
        stack.enter_context(patch("storage.legacy.legacy_data_exists", return_value=False))
        stack.enter_context(
            patch("storage.resolver.requires_data_root_setup", return_value=True)
        )
        return stack

    def test_startup_mode_import_does_not_touch_active_storage(self) -> None:
        with self._fresh_install_context():
            import app.startup_mode as startup_mode

            importlib.reload(startup_mode)

            with patch.object(startup_mode, "configured_data_root", return_value=None):
                with patch.object(startup_mode, "requires_data_root_setup", return_value=True):
                    with patch.object(startup_mode, "legacy_data_exists", return_value=False):
                        self.assertFalse(startup_mode.has_observation_points())
                        self.assertFalse(startup_mode.is_existing_user())
                        self.assertTrue(startup_mode.needs_deferred_storage_layout())

    def test_obs_freeze_trace_import_does_not_touch_active_storage(self) -> None:
        with self._fresh_install_context():
            import debug.obs_freeze_trace as obs_freeze_trace

            importlib.reload(obs_freeze_trace)

            with self.assertRaises(DataDirectoryNotConfiguredError):
                obs_freeze_trace.trace_path()

    def test_geo_context_import_does_not_touch_active_storage(self) -> None:
        with self._fresh_install_context():
            geo_context_module = importlib.import_module("observation.geo_context")

            importlib.reload(geo_context_module)

            self.assertIsNotNone(geo_context_module.geo_context)

    def test_ship_registry_import_does_not_touch_active_storage(self) -> None:
        with self._fresh_install_context():
            import database.ship_registry as ship_registry

            importlib.reload(ship_registry)

            ship_registry.get_ship_registry()

    def test_hybrid_ais_engine_import_does_not_touch_active_storage(self) -> None:
        with self._fresh_install_context():
            hybrid_ais_engine_module = importlib.import_module(
                "engines.ais.hybrid_ais_engine"
            )

            self.assertIsNotNone(hybrid_ais_engine_module.hybrid_ais_engine)

    def test_vessel_sync_import_does_not_touch_active_storage(self) -> None:
        with self._fresh_install_context():
            import database.vessel_sync as vessel_sync

            importlib.reload(vessel_sync)

            vessel_sync.get_vessel_sync()

    def test_vessel_database_raises_only_on_use(self) -> None:
        with self._fresh_install_context():
            import database.vessel_database as vessel_database

            importlib.reload(vessel_database)

            with self.assertRaises(DataDirectoryNotConfiguredError):
                vessel_database.get_vessel_database()


if __name__ == "__main__":
    unittest.main()
