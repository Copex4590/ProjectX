#!/usr/bin/env python3
"""Unit tests for startup storage layout initialization (SAVE-107-B3)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preferences.preferences import Preferences
from storage import (
    DATA_ROOT_MARKER_NAME,
    STANDARD_DATA_SUBDIRS,
    StorageMode,
    ensure_active_layout,
    ensure_active_storage_layout,
    ensure_legacy_data_layout,
    resolve_data_root,
)


class StartupLayoutTests(unittest.TestCase):

    def test_legacy_startup_creates_expected_directories(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir) / "data"
            config_root = Path(temp_dir) / "config"
            logs_root = Path(temp_dir) / "logs"
            logs_root.mkdir(parents=True, exist_ok=True)

            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "preferences.preferences_manager.preferences_manager.get",
                    return_value=Preferences.defaults(),
                ):
                    with patch("storage.legacy.legacy_data_root", return_value=data_root):
                        with patch(
                            "storage.legacy.legacy_config_root",
                            return_value=config_root,
                        ):
                            with patch(
                                "storage.legacy.legacy_logs_root",
                                return_value=logs_root,
                            ):
                                root = ensure_legacy_data_layout()

            self.assertEqual(root, data_root)
            self.assertTrue((data_root / "Hajók").is_dir())
            self.assertTrue((data_root / "vessel_photos").is_dir())
            self.assertTrue(config_root.is_dir())
            self.assertTrue(logs_root.is_dir())

    def test_configured_startup_creates_complete_layout_and_marker(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                active_root = ensure_active_storage_layout()
                resolved = resolve_data_root()

            self.assertEqual(active_root, root.resolve())
            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)

            for name in STANDARD_DATA_SUBDIRS:
                self.assertTrue((root / name).is_dir(), name)

            self.assertTrue((root / DATA_ROOT_MARKER_NAME).is_file())

    def test_ensure_active_layout_is_idempotent(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                first = ensure_active_layout()
                second = ensure_active_layout()

            self.assertEqual(first, second)
            self.assertTrue((root / DATA_ROOT_MARKER_NAME).is_file())

    def test_paths_wrapper_delegates_to_active_storage_layout(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                from app.paths import ensure_runtime_data_dirs

                ensure_runtime_data_dirs()

            self.assertTrue((root / "databases").is_dir())
            self.assertTrue((root / DATA_ROOT_MARKER_NAME).is_file())

    def test_legacy_active_layout_does_not_create_configured_marker(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir) / "data"

            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "preferences.preferences_manager.preferences_manager.get",
                    return_value=Preferences.defaults(),
                ):
                    with patch("storage.legacy.legacy_data_root", return_value=data_root):
                        with patch(
                            "storage.legacy.legacy_config_root",
                            return_value=Path(temp_dir) / "config",
                        ):
                            with patch(
                                "storage.legacy.legacy_logs_root",
                                return_value=Path(temp_dir) / "logs",
                            ):
                                with patch(
                                    "storage.resolver.legacy_data_exists",
                                    return_value=True,
                                ):
                                    ensure_active_layout()

            self.assertFalse((data_root / DATA_ROOT_MARKER_NAME).exists())


if __name__ == "__main__":
    unittest.main()
