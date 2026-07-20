#!/usr/bin/env python3
"""Unit tests for first-run data root startup integration (SAVE-107-C4)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from isolated_paths import isolated_temp_dir
from preferences.preferences import Preferences
from preferences.preferences_manager import PreferencesManager
from storage import (
    StorageMode,
    ensure_active_storage_layout,
    requires_data_root_setup,
    resolve_data_root,
)
from storage.data_root_initialization import DataRootInitializationService
from storage.exceptions import DataDirectoryNotConfiguredError


class StartupDataRootIntegrationTests(unittest.TestCase):

    def test_requires_data_root_setup_skips_legacy_layout_creation(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("storage.resolver.legacy_data_exists", return_value=False):
                    with patch(
                        "storage.legacy.ensure_legacy_data_layout",
                    ) as ensure_legacy:
                        self.assertTrue(requires_data_root_setup())

                        with self.assertRaises(DataDirectoryNotConfiguredError):
                            ensure_active_storage_layout()

                        ensure_legacy.assert_not_called()

    def test_configured_startup_skips_legacy_resolution(self) -> None:

        with isolated_temp_dir() as temp_dir:
            root = Path(temp_dir) / "Project X"
            preferences_path = Path(temp_dir) / "preferences.json"
            preferences_manager = PreferencesManager(preferences_path)
            service = DataRootInitializationService(
                preferences_manager=preferences_manager,
            )

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                result = service.initialize(root)
                self.assertTrue(result.success, result.message)

                with patch(
                    "storage.resolver.ensure_legacy_data_layout",
                ) as ensure_legacy:
                    resolved = resolve_data_root()

                ensure_legacy.assert_not_called()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertEqual(resolved.path, root.resolve())

    def test_run_data_location_setup_if_needed_skips_when_not_required(
        self,
    ) -> None:

        with patch(
            "gui.data_location_wizard.needs_data_root_wizard",
            return_value=False,
        ):
            from gui.data_location_wizard import run_data_location_setup_if_needed

            self.assertTrue(run_data_location_setup_if_needed())

    def test_existing_user_skips_data_location_wizard(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("app.startup_mode.legacy_data_exists", return_value=True):
                    with patch(
                        "app.startup_mode.has_observation_points",
                        return_value=True,
                    ):
                        from app.startup_mode import needs_data_root_wizard

                        self.assertFalse(needs_data_root_wizard())


if __name__ == "__main__":
    unittest.main()
