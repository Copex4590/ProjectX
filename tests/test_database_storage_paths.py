#!/usr/bin/env python3
"""Unit tests for database storage path resolution (SAVE-107-B2.1)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alerts.alert_event import AlertEvent
from alerts.alert_registry import AlertRegistry
from alerts.alert_rule import AlertRule
from database.vessel_database import VesselDatabase
from models.vessel_record import VesselRecord
from preferences.preferences import Preferences
from storage import StorageMode, active_database_path, ensure_data_layout, resolve_data_root
from timeline.timeline_registry import TimelineRegistry
from timeline.timeline_record import TimelineRecord


class DatabasePathResolutionTests(unittest.TestCase):

    def test_legacy_database_paths_use_flat_data_directory(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                vessel_path = active_database_path("vessels.db")
                timeline_path = active_database_path("timeline.db")
                alert_path = active_database_path("alerts.db")
                resolved = resolve_data_root()

        self.assertEqual(resolved.mode, StorageMode.LEGACY)
        self.assertTrue(str(vessel_path).endswith("data/vessels.db"))
        self.assertTrue(str(timeline_path).endswith("data/timeline.db"))
        self.assertTrue(str(alert_path).endswith("data/alerts.db"))

    def test_configured_database_paths_use_databases_subdirectory(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                vessel_path = active_database_path("vessels.db")
                timeline_path = active_database_path("timeline.db")
                alert_path = active_database_path("alerts.db")
                resolved = resolve_data_root()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertEqual(vessel_path, root / "databases" / "vessels.db")
            self.assertEqual(timeline_path, root / "databases" / "timeline.db")
            self.assertEqual(alert_path, root / "databases" / "alerts.db")


class DatabasePersistenceTests(unittest.TestCase):

    def test_vessel_database_round_trip(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "vessels.db"
            database = VesselDatabase(db_path)
            now = datetime.now()

            database.upsert(
                VesselRecord(
                    mmsi=123456789,
                    name="TEST SHIP",
                    first_seen=now,
                    last_seen=now,
                    created_at=now,
                    updated_at=now,
                )
            )

            self.assertEqual(database.count(), 1)
            record = database.get(123456789)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.name, "TEST SHIP")

    def test_timeline_registry_round_trip(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "timeline.db"
            registry = TimelineRegistry(db_path)
            now = datetime.now()

            registry.append(
                TimelineRecord(
                    mmsi=123456789,
                    timestamp=now,
                    event_type="POSITION",
                    source="AIS",
                )
            )

            self.assertEqual(registry.count(), 1)
            history = registry.history(123456789)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].event_type, "POSITION")

    def test_alert_registry_round_trip(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "alerts.db"
            registry = AlertRegistry(db_path)

            rule = registry.register_rule(
                AlertRule(
                    name="Speed",
                    event_type="SPEED",
                )
            )

            registry.append_event(
                AlertEvent(
                    rule_id=rule.id or 0,
                    mmsi=123456789,
                    event_type="SPEED",
                    message="Too fast",
                )
            )

            self.assertEqual(len(registry.rules()), 1)
            self.assertEqual(len(registry.events()), 1)


if __name__ == "__main__":
    unittest.main()
