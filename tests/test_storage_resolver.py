#!/usr/bin/env python3
"""Unit tests for storage resolver (SAVE-107-B1)."""

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
    DATA_SUBDIR_CACHE,
    DATA_SUBDIR_CONFIG,
    DATA_SUBDIR_DATABASES,
    DATA_SUBDIR_EXPORTS,
    DATA_SUBDIR_HAJOK,
    DATA_SUBDIR_LOGS,
    LegacyDataInventory,
    StorageMode,
    active_data_path,
    assert_marker_authority,
    collect_legacy_inventory,
    ensure_active_layout,
    ensure_data_layout,
    legacy_data_exists,
    require_marked_data_root,
    requires_data_root_setup,
    resolve_data_root,
)
from storage.exceptions import InvalidDataDirectoryError


class StorageResolverTests(unittest.TestCase):

    def test_resolve_data_root_uses_legacy_when_unconfigured(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                resolved = resolve_data_root()

        self.assertEqual(resolved.mode, StorageMode.LEGACY)
        self.assertFalse(resolved.has_marker)

    def test_resolve_data_root_uses_configured_marker(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                resolved = resolve_data_root()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertTrue(resolved.has_marker)
            self.assertEqual(resolved.path, root.resolve())

    def test_resolve_data_root_rejects_configured_path_without_marker(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            root.mkdir()

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                with self.assertRaises(InvalidDataDirectoryError):
                    resolve_data_root()

    def test_active_data_path_legacy_database_mapping(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                path = active_data_path(DATA_SUBDIR_DATABASES, "vessels.db")

        self.assertTrue(str(path).endswith("data/vessels.db"))

    def test_active_data_path_configured_layout(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                path = active_data_path(DATA_SUBDIR_CONFIG, "cameras.json")

            self.assertEqual(path, root / DATA_SUBDIR_CONFIG / "cameras.json")

    def test_active_data_path_legacy_cache_and_exports(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                cache_path = active_data_path(DATA_SUBDIR_CACHE, "ship_cache.json")
                export_path = active_data_path(DATA_SUBDIR_EXPORTS, "radar.json")
                log_path = active_data_path(DATA_SUBDIR_LOGS, "projectx.log")

        self.assertTrue(str(cache_path).endswith("data/ship_cache.json"))
        self.assertTrue(str(export_path).endswith("data/exports/radar.json"))
        self.assertIn("Project X/logs/projectx.log", str(log_path))

    def test_requires_data_root_setup_for_empty_install(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("storage.resolver.legacy_data_exists", return_value=False):
                    self.assertTrue(requires_data_root_setup())

    def test_requires_data_root_setup_false_when_legacy_exists(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("storage.resolver.legacy_data_exists", return_value=True):
                    self.assertFalse(requires_data_root_setup())

    def test_ensure_active_layout_creates_marker_only_when_configured(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                ensure_active_layout()

            self.assertTrue((root / ".projectx-data-root").is_file())

    def test_marker_authority_required_for_destructive_targets(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            unmarked = Path(temp_dir) / "not-project-x"
            unmarked.mkdir()

            with self.assertRaises(InvalidDataDirectoryError):
                require_marked_data_root(unmarked)

            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            self.assertEqual(assert_marker_authority(root / DATA_SUBDIR_HAJOK), root)

    def test_collect_legacy_inventory_counts_files(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir) / "data"
            config_root = Path(temp_dir) / "config"
            config_root.mkdir()
            hajok_dir = data_root / DATA_SUBDIR_HAJOK / "AA-D"
            hajok_dir.mkdir(parents=True)
            (hajok_dir / "adatlap.csv").write_text("row", encoding="utf-8")
            (data_root / "vessels.db").write_bytes(b"db")
            (config_root / "observation_points.json").write_text("[]", encoding="utf-8")

            with patch("storage.legacy.legacy_data_root", return_value=data_root):
                with patch("storage.legacy.legacy_config_root", return_value=config_root):
                    with patch("storage.legacy.legacy_logs_root", return_value=Path(temp_dir) / "logs"):
                        inventory = collect_legacy_inventory()

            self.assertIsInstance(inventory, LegacyDataInventory)
            self.assertEqual(inventory.ship_folder_count, 1)
            self.assertEqual(len(inventory.database_files), 1)
            self.assertGreater(inventory.file_count, 0)
            self.assertGreater(inventory.total_bytes, 0)


if __name__ == "__main__":
    unittest.main()
