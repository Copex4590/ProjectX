#!/usr/bin/env python3
"""Unit tests for the data root initialization service (SAVE-107-C3)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from isolated_paths import isolated_temp_dir
from preferences.preferences_manager import PreferencesManager
from storage import (
    DATA_ROOT_MARKER_NAME,
    ResolvedDataRoot,
    STANDARD_DATA_SUBDIRS,
    StorageMode,
    configured_data_root,
    is_valid_data_root,
    resolve_data_root,
)
from storage.data_root_initialization import DataRootInitializationService


class DataRootInitializationServiceTests(unittest.TestCase):

    def test_successful_initialization_creates_layout_marker_and_preferences(
        self,
    ) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            preferences_path = base / "bootstrap" / "preferences.json"
            preferences_manager = PreferencesManager(preferences_path)
            service = DataRootInitializationService(
                preferences_manager=preferences_manager,
            )
            target = base / "Project X"

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                result = service.initialize(target)

            self.assertTrue(result.success, result.message)
            self.assertEqual(result.mode, StorageMode.CONFIGURED)
            self.assertIsNotNone(result.data_root)
            assert result.data_root is not None

            self.assertTrue(is_valid_data_root(result.data_root))
            self.assertTrue((result.data_root / DATA_ROOT_MARKER_NAME).is_file())

            for name in STANDARD_DATA_SUBDIRS:
                self.assertTrue((result.data_root / name).is_dir())

            preferences = preferences_manager.get()
            self.assertEqual(
                preferences.data_directory,
                str(result.data_root),
            )

    def test_initialization_rejects_invalid_directory(self) -> None:

        with isolated_temp_dir() as temp_dir:
            preferences_path = Path(temp_dir) / "preferences.json"
            preferences_manager = PreferencesManager(preferences_path)
            service = DataRootInitializationService(
                preferences_manager=preferences_manager,
            )

            result = service.initialize(Path("   "))

            self.assertFalse(result.success)
            self.assertIsNone(result.data_root)
            self.assertIsNone(result.mode)
            self.assertFalse(preferences_manager.get().has_data_directory())

    def test_resolver_enters_configured_mode_after_initialization(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            preferences_path = base / "bootstrap" / "preferences.json"
            preferences_manager = PreferencesManager(preferences_path)
            service = DataRootInitializationService(
                preferences_manager=preferences_manager,
            )
            target = base / "Project X"

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                result = service.initialize(target)
                self.assertTrue(result.success, result.message)

                self.assertEqual(
                    configured_data_root(),
                    result.data_root,
                )
                resolved = resolve_data_root()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertTrue(resolved.has_marker)
            self.assertEqual(resolved.path, result.data_root)

    def test_post_initialization_verification_failure_preserves_layout(
        self,
    ) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            preferences_path = base / "bootstrap" / "preferences.json"
            preferences_manager = PreferencesManager(preferences_path)
            service = DataRootInitializationService(
                preferences_manager=preferences_manager,
            )
            target = base / "Project X"

            wrong_root = base / "Wrong Root"

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                with patch(
                    "storage.data_root_initialization.resolve_data_root",
                    return_value=ResolvedDataRoot(
                        path=wrong_root,
                        mode=StorageMode.CONFIGURED,
                        has_marker=True,
                    ),
                ):
                    result = service.initialize(target)

            self.assertFalse(result.success)
            self.assertIsNotNone(result.data_root)
            assert result.data_root is not None
            self.assertTrue(is_valid_data_root(result.data_root))
            self.assertIn("verification failed", result.message.lower())
            self.assertTrue(preferences_manager.get().has_data_directory())


if __name__ == "__main__":
    unittest.main()
