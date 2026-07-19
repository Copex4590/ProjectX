#!/usr/bin/env python3
"""Unit tests for logbook storage path resolution (SAVE-107-B2.2)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logbook.logbook_manager import LogbookManager
from logbook.paths import CSV_FILENAME, CSV_HEADER, logbook_dir
from models.ship import Ship
from preferences.preferences import Preferences
from storage import StorageMode, ensure_data_layout, resolve_data_root


class LogbookPathResolutionTests(unittest.TestCase):

    def test_legacy_logbook_dir_uses_data_hajok(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                path = logbook_dir()
                resolved = resolve_data_root()

        self.assertEqual(resolved.mode, StorageMode.LEGACY)
        self.assertTrue(str(path).endswith("data/Hajók"))

    def test_configured_logbook_dir_uses_marked_data_root(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                path = logbook_dir()
                resolved = resolve_data_root()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertEqual(path, root / "Hajók")

    def test_logbook_env_override_takes_precedence(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            override = Path(temp_dir) / "custom-logbook"

            with patch.dict(os.environ, {"PROJECTX_LOGBOOK_DIR": str(override)}):
                self.assertEqual(logbook_dir(), override.resolve())


class LogbookManagerStorageTests(unittest.TestCase):

    def test_ensure_ship_folder_creates_csv_and_photos(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "Hajók"
            manager = LogbookManager(base_dir=base_dir)
            ship = Ship(
                mmsi=256992000,
                name="AA-D",
                lat=47.5,
                lon=19.0,
                last_seen=datetime.now(),
            )

            ship_dir = manager.ensure_ship_folder(ship)

            self.assertEqual(ship_dir, base_dir / "AA-D")
            self.assertTrue((ship_dir / CSV_FILENAME).is_file())
            self.assertTrue((ship_dir / "photos").is_dir())
            self.assertEqual(
                (ship_dir / CSV_FILENAME).read_text(encoding="utf-8"),
                CSV_HEADER,
            )

    def test_append_observation_writes_csv_row(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "Hajók"
            manager = LogbookManager(base_dir=base_dir)
            ship = Ship(
                mmsi=256992000,
                name="AA-D",
                lat=47.5,
                lon=19.0,
                speed=0.0,
                course=0.0,
                last_seen=datetime.now(),
                distance_km=438.14,
                direction="északra",
                text_heading="Áll északra",
            )

            manager.append_observation(ship)

            csv_file = base_dir / "AA-D" / CSV_FILENAME
            content = csv_file.read_text(encoding="utf-8")
            self.assertTrue(content.startswith(CSV_HEADER))
            self.assertIn("256992000", content)
            self.assertGreater(len(content), len(CSV_HEADER))


if __name__ == "__main__":
    unittest.main()
