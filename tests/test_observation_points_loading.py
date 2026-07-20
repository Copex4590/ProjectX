#!/usr/bin/env python3
"""Tests for observation point file loading and storage-path reload."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observation.observation_manager import (
    file_contains_observation_points,
    get_observation_manager,
    reset_observation_manager,
    write_empty_observation_points_file,
)


class ObservationPointsLoadingTests(unittest.TestCase):

    def test_file_contains_observation_points_detects_saved_points(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "observation_points.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 3,
                        "points": [{"id": "op-1", "name": "Harbor"}],
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(file_contains_observation_points(path))

    def test_write_empty_observation_points_file_clears_points(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "observation_points.json"
            path.write_text(
                json.dumps({"version": 3, "points": [{"id": "op-1"}]}),
                encoding="utf-8",
            )

            write_empty_observation_points_file(path)

            self.assertFalse(file_contains_observation_points(path))

    def test_reset_observation_manager_reloads_configured_path(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            legacy_path = Path(temp_dir) / "legacy" / "observation_points.json"
            configured_path = Path(temp_dir) / "configured" / "observation_points.json"
            legacy_path.parent.mkdir(parents=True)
            configured_path.parent.mkdir(parents=True)
            legacy_path.write_text(
                json.dumps(
                    {
                        "version": 3,
                        "points": [
                            {
                                "id": "legacy-op",
                                "name": "Harbor",
                                "latitude": 47.0,
                                "longitude": 19.0,
                                "coverage_radius_km": 50.0,
                                "active": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            write_empty_observation_points_file(configured_path)

            trace_path = Path(temp_dir) / "obs_freeze.trace"

            get_observation_manager.reset()

            with patch("debug.obs_freeze_trace._trace_path", return_value=trace_path), patch(
                "observation.observation_manager.observation_points_file",
                side_effect=[legacy_path, configured_path],
            ):
                legacy_manager = get_observation_manager()
                self.assertEqual(len(legacy_manager.all()), 1)

                reloaded = reset_observation_manager()

            self.assertEqual(reloaded._path, configured_path)
            self.assertEqual(len(reloaded._points), 0)


if __name__ == "__main__":
    unittest.main()
