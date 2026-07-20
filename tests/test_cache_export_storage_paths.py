#!/usr/bin/env python3
"""Unit tests for cache and export storage path resolution (SAVE-107-B2.3)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from debug.obs_freeze_trace import trace_path
from preferences.preferences import Preferences
from storage import (
    StorageMode,
    active_cache_path,
    active_export_path,
    ensure_data_layout,
    resolve_data_root,
)
from vessels.photo_record import PhotoRecord
from vessels.photo_registry import PhotoRegistry, vessel_photos_dir


class CacheExportPathResolutionTests(unittest.TestCase):

    def test_legacy_cache_paths_use_flat_data_directory(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                ship_cache = active_cache_path("ship_cache.json")
                vessel_photos = active_cache_path("vessel_photos")
                deli_hajok = active_cache_path("deli_hajok")
                obs_trace = active_cache_path("obs_freeze.trace")
                export_dir = active_export_path()
                resolved = resolve_data_root()

        self.assertEqual(resolved.mode, StorageMode.LEGACY)
        self.assertTrue(str(ship_cache).endswith("data/ship_cache.json"))
        self.assertTrue(str(vessel_photos).endswith("data/vessel_photos"))
        self.assertTrue(str(deli_hajok).endswith("data/deli_hajok"))
        self.assertTrue(str(obs_trace).endswith("data/obs_freeze.trace"))
        self.assertTrue(str(export_dir).endswith("data/exports"))

    def test_configured_cache_and_export_paths(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                ship_cache = active_cache_path("ship_cache.json")
                export_dir = active_export_path()
                resolved = resolve_data_root()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertEqual(ship_cache, root / "Cache" / "ship_cache.json")
            self.assertEqual(export_dir, root / "Exports")

    def test_vessel_photos_env_override(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            override = Path(temp_dir) / "photos"

            with patch.dict(os.environ, {"PROJECTX_VESSEL_PHOTOS_DIR": str(override)}):
                self.assertEqual(vessel_photos_dir(), override.resolve())


class CacheExportWriteTests(unittest.TestCase):

    def test_photo_registry_creates_database_under_cache(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            photos_dir = Path(temp_dir) / "vessel_photos"
            registry = PhotoRegistry(db_path=photos_dir / "photos.db")

            registry.register(
                PhotoRecord(
                    mmsi=123456789,
                    source="test",
                    local_file="ship.jpg",
                )
            )

            self.assertTrue((photos_dir / "photos.db").is_file())
            self.assertEqual(registry.count(), 1)

    def test_obs_freeze_trace_path_matches_resolver(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                self.assertTrue(str(trace_path()).endswith("data/obs_freeze.trace"))

    def test_export_path_helper_creates_directory(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                export_dir = active_export_path()
                export_dir.mkdir(parents=True, exist_ok=True)
                export_file = export_dir / "radar.json"
                export_file.write_text(json.dumps({"ok": True}), encoding="utf-8")

            self.assertTrue(export_dir.is_dir())
            self.assertEqual(export_dir, root / "Exports")
            self.assertTrue(export_file.is_file())


if __name__ == "__main__":
    unittest.main()
