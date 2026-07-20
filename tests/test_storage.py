#!/usr/bin/env python3
"""Unit tests for storage (SAVE-107-A)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from isolated_paths import isolated_temp_dir
from preferences.preferences import Preferences
from storage import (
    DATA_ROOT_MARKER_NAME,
    STANDARD_DATA_SUBDIRS,
    configured_data_root,
    data_root,
    default_data_directory,
    ensure_data_layout,
    is_valid_data_root,
    read_marker,
    validate_data_directory,
)
from storage.exceptions import (
    DataDirectoryNotConfiguredError,
    InvalidDataDirectoryError,
)
from storage.layout import DEFAULT_DATA_DIRECTORY_NAME


class PreferencesSchemaTests(unittest.TestCase):

    def test_defaults_include_data_directory(self) -> None:

        preferences = Preferences.defaults()
        self.assertIsNone(preferences.data_directory)
        self.assertEqual(preferences.version, 2)
        self.assertFalse(preferences.has_data_directory())

    def test_migrate_v1_adds_data_directory(self) -> None:

        migrated = Preferences.migrate({"version": 1, "language": "en"})
        self.assertEqual(migrated["version"], 2)
        self.assertIsNone(migrated["data_directory"])

    def test_round_trip_data_directory(self) -> None:

        payload = Preferences(
            language="hu",
            data_directory="/tmp/Project X",
        ).to_dict()
        restored = Preferences.from_dict(payload)
        self.assertEqual(restored.data_directory, "/tmp/Project X")
        self.assertTrue(restored.has_data_directory())


class StorageLayoutTests(unittest.TestCase):

    def test_default_data_directory_name(self) -> None:

        self.assertEqual(
            default_data_directory(),
            Path.home() / DEFAULT_DATA_DIRECTORY_NAME,
        )

    def test_ensure_data_layout_creates_marker_and_subdirs(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            self.assertTrue((root / DATA_ROOT_MARKER_NAME).is_file())
            self.assertTrue(is_valid_data_root(root))

            for name in STANDARD_DATA_SUBDIRS:
                self.assertTrue((root / name).is_dir())

            marker = read_marker(root)
            self.assertEqual(marker["product"], "Project X")
            self.assertEqual(marker["schema"], 1)
            self.assertIn("uuid", marker)
            self.assertIn("created", marker)

    def test_validate_data_directory_accepts_writable_folder(self) -> None:

        with isolated_temp_dir() as temp_dir:
            candidate = Path(temp_dir) / "Project X"
            result = validate_data_directory(candidate)
            self.assertTrue(result.valid)
            self.assertTrue(candidate.is_dir())

    def test_validate_data_directory_rejects_empty_path(self) -> None:

        result = validate_data_directory(Path("   "))
        self.assertFalse(result.valid)


class ConfiguredDataRootTests(unittest.TestCase):

    def test_configured_data_root_from_env(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / "Project X"
            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(env_path)}):
                self.assertEqual(configured_data_root(), env_path.resolve())

    def test_data_root_requires_marker(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            root.mkdir()

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                with self.assertRaises(InvalidDataDirectoryError):
                    data_root()

                ensure_data_layout(root)
                self.assertEqual(data_root(), root.resolve())

    def test_data_root_raises_when_unconfigured(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with self.assertRaises(DataDirectoryNotConfiguredError):
                    data_root()


if __name__ == "__main__":
    unittest.main()
