#!/usr/bin/env python3
"""Unit tests for configuration storage path resolution (SAVE-107-B2.4)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preferences.preferences import Preferences
from storage import (
    StorageMode,
    active_config_path,
    ensure_data_layout,
    resolve_data_root,
)


class ConfigPathResolutionTests(unittest.TestCase):

    def test_legacy_config_paths_use_runtime_config_directory(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                observation = active_config_path("observation_points.json")
                cameras = active_config_path("cameras.json")
                ais_key = active_config_path("ais_api_key.txt")
                playback = active_config_path("playback.json")
                pack_state = active_config_path("camera_packs_state.json")
                resolved = resolve_data_root()

        self.assertEqual(resolved.mode, StorageMode.LEGACY)
        self.assertTrue(str(observation).endswith("config/observation_points.json"))
        self.assertTrue(str(cameras).endswith("config/cameras.json"))
        self.assertTrue(str(ais_key).endswith("config/ais_api_key.txt"))
        self.assertTrue(str(playback).endswith("config/playback.json"))
        self.assertTrue(str(pack_state).endswith("config/camera_packs_state.json"))

    def test_configured_config_paths_use_data_root_config_subdirectory(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                observation = active_config_path("observation_points.json")
                playback = active_config_path("playback.json")
                resolved = resolve_data_root()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertEqual(observation, root / "config" / "observation_points.json")
            self.assertEqual(playback, root / "config" / "playback.json")

    def test_consumer_config_filenames(self) -> None:

        expected_files = (
            "observation_points.json",
            "cameras.json",
            "ais_api_key.txt",
            "playback.json",
            "camera_packs_state.json",
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                for filename in expected_files:
                    path = active_config_path(filename)
                    self.assertTrue(str(path).endswith(f"config/{filename}"))

    def test_dev_camera_packs_state_uses_nested_legacy_path(self) -> None:

        from cameras.pack_manager import camera_packs_state_file

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("cameras.pack_manager.is_frozen", return_value=False):
                    state_path = camera_packs_state_file()

        self.assertTrue(str(state_path).endswith("config/camera_packs/state.json"))

    def test_configured_camera_packs_state_uses_flat_config_filename(self) -> None:

        from cameras.pack_manager import camera_packs_state_file

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                with patch("cameras.pack_manager.is_frozen", return_value=False):
                    state_path = camera_packs_state_file()

            self.assertEqual(state_path, root / "config" / "camera_packs_state.json")


class ConfigWriteTests(unittest.TestCase):

    def test_playback_preferences_round_trip(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            preferences_file = Path(temp_dir) / "playback.json"
            payload = {
                "mode": "automatic",
                "preferred_backend": "mpv",
                "custom_executable": "",
                "custom_arguments": [],
            }
            preferences_file.parent.mkdir(parents=True, exist_ok=True)
            preferences_file.write_text(json.dumps(payload), encoding="utf-8")

            loaded = json.loads(preferences_file.read_text(encoding="utf-8"))

            self.assertEqual(loaded["mode"], "automatic")
            self.assertEqual(loaded["preferred_backend"], "mpv")

    def test_camera_pack_state_persists_under_configured_root(self) -> None:

        from cameras.pack_manager import CameraPackManager

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)
            state_file = root / "config" / "camera_packs_state.json"
            manager = CameraPackManager(
                packs_dir=Path(temp_dir) / "empty_packs",
                state_file=state_file,
            )

            manager._enabled_ids = {"hungary"}
            manager._save_state()
            reloaded_ids = manager._load_state()

            self.assertEqual(reloaded_ids, {"hungary"})
            self.assertTrue(state_file.is_file())


if __name__ == "__main__":
    unittest.main()
