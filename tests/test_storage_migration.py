#!/usr/bin/env python3
"""Unit tests for legacy data migration engine (SAVE-107-B4)."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from isolated_paths import isolated_temp_dir
from preferences.preferences import Preferences
from preferences.preferences_manager import PreferencesManager
from storage import (
    DATA_ROOT_MARKER_NAME,
    DATA_SUBDIR_CACHE,
    DATA_SUBDIR_CONFIG,
    DATA_SUBDIR_DATABASES,
    DATA_SUBDIR_EXPORTS,
    DATA_SUBDIR_HAJOK,
    DATA_SUBDIR_LOGS,
    MigrationPhase,
    ResolvedDataRoot,
    StorageMode,
    build_migration_copy_plan,
    configured_data_root,
    is_valid_data_root,
)
from storage.exceptions import MigrationError
from storage.legacy import LegacyDataInventory, _count_tree_files, _ship_folder_count
from storage.migration import CopyAction, DataMigrationService, _copy_file
from storage.migration_state import MigrationState, MigrationStateStore


def _write_sqlite(path: Path, *, table_sql: str, insert_sql: str) -> None:

    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(table_sql)
        connection.execute(insert_sql)
        connection.commit()


def _build_synthetic_legacy_layout(base: Path) -> LegacyDataInventory:

    data_root = base / "data"
    config_root = base / "config"
    logs_root = base / "logs"
    config_root.mkdir(parents=True, exist_ok=True)
    logs_root.mkdir(parents=True, exist_ok=True)

    ship_dir = data_root / DATA_SUBDIR_HAJOK / "AA-D"
    ship_dir.mkdir(parents=True)
    (ship_dir / "adatlap.csv").write_text("name,imo\nTEST,123\n", encoding="utf-8")

    _write_sqlite(
        data_root / "vessels.db",
        table_sql="CREATE TABLE vessels (mmsi INTEGER PRIMARY KEY, name TEXT)",
        insert_sql="INSERT INTO vessels (mmsi, name) VALUES (123456789, 'TEST')",
    )
    _write_sqlite(
        data_root / "timeline.db",
        table_sql="CREATE TABLE timeline (id INTEGER PRIMARY KEY, label TEXT)",
        insert_sql="INSERT INTO timeline (id, label) VALUES (1, 'event')",
    )

    (data_root / "ship_cache.json").write_text('{"ships": []}', encoding="utf-8")
    (data_root / "obs_freeze.trace").write_text("trace\n", encoding="utf-8")

    photos_dir = data_root / "vessel_photos"
    photos_dir.mkdir()
    _write_sqlite(
        photos_dir / "photos.db",
        table_sql="CREATE TABLE vessel_photos (mmsi INTEGER PRIMARY KEY)",
        insert_sql="INSERT INTO vessel_photos (mmsi) VALUES (123456789)",
    )

    exports_dir = data_root / "exports"
    exports_dir.mkdir()
    (exports_dir / "radar.json").write_text('{"ok": true}', encoding="utf-8")

    (config_root / "observation_points.json").write_text("[]", encoding="utf-8")
    (config_root / "cameras.json").write_text("[]", encoding="utf-8")
    (config_root / "ais_api_key.txt").write_text("secret-key", encoding="utf-8")
    (config_root / "playback.json").write_text(
        '{"mode": "automatic"}',
        encoding="utf-8",
    )

    (logs_root / "projectx.log").write_text("startup log\n", encoding="utf-8")

    database_files = tuple(
        sorted(
            path
            for name in ("vessels.db", "timeline.db", "alerts.db")
            if (path := data_root / name).is_file()
        )
    )
    config_files = tuple(
        sorted(
            path
            for name in (
                "observation_points.json",
                "cameras.json",
                "ais_api_key.txt",
                "playback.json",
            )
            if (path := config_root / name).is_file()
        )
    )

    file_count = 0
    total_bytes = 0

    for root in (data_root, config_root, logs_root):
        root_files, root_bytes = _count_tree_files(root)
        file_count += root_files
        total_bytes += root_bytes

    return LegacyDataInventory(
        data_root=data_root,
        config_root=config_root,
        logs_root=logs_root,
        ship_folder_count=_ship_folder_count(data_root),
        database_files=database_files,
        config_files=config_files,
        file_count=file_count,
        total_bytes=total_bytes,
    )


class MigrationCopyPlanTests(unittest.TestCase):

    def test_copy_plan_maps_legacy_paths_to_configured_layout(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            inventory = _build_synthetic_legacy_layout(base)
            destination = base / "Project X"
            plan = build_migration_copy_plan(inventory, destination)

            destinations = {item.destination for item in plan}

            self.assertIn(destination / DATA_SUBDIR_HAJOK / "AA-D" / "adatlap.csv", destinations)
            self.assertIn(destination / DATA_SUBDIR_DATABASES / "vessels.db", destinations)
            self.assertIn(destination / DATA_SUBDIR_CACHE / "ship_cache.json", destinations)
            self.assertIn(destination / DATA_SUBDIR_EXPORTS / "radar.json", destinations)
            self.assertIn(destination / DATA_SUBDIR_CONFIG / "cameras.json", destinations)
            self.assertIn(destination / DATA_SUBDIR_LOGS / "projectx.log", destinations)


class MigrationServiceSuccessTests(unittest.TestCase):

    def _run_service(
        self,
        base: Path,
        *,
        inventory: LegacyDataInventory,
    ) -> tuple[DataMigrationService, Path, object, PreferencesManager]:

        destination = base / "Project X"
        state_path = base / "bootstrap" / "migration_state.json"
        preferences_path = base / "bootstrap" / "preferences.json"
        state_store = MigrationStateStore(state_path)
        preferences_manager = PreferencesManager(preferences_path)

        service = DataMigrationService(
            state_store=state_store,
            preferences_manager=preferences_manager,
        )

        with patch(
            "preferences.preferences_manager.preferences_manager",
            preferences_manager,
        ):
            with patch(
                "storage.migration.collect_legacy_inventory",
                return_value=inventory,
            ):
                result = service.run(destination)

        return service, destination, result, preferences_manager

    def test_successful_migration_copies_verifies_and_commits(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            inventory = _build_synthetic_legacy_layout(base)
            source_snapshot = {
                path: path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }

            service, destination, result, preferences_manager = self._run_service(
                base,
                inventory=inventory,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.phase, MigrationPhase.COMPLETED)
            self.assertTrue(is_valid_data_root(destination))
            self.assertEqual(
                preferences_manager.get().data_directory,
                str(destination.resolve()),
            )
            self.assertTrue(
                (destination / DATA_SUBDIR_DATABASES / "vessels.db").is_file()
            )
            self.assertTrue(
                (destination / DATA_SUBDIR_CONFIG / "observation_points.json").is_file()
            )

            for path, content in source_snapshot.items():
                self.assertEqual(path.read_bytes(), content)

    def test_source_files_remain_unmodified(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            inventory = _build_synthetic_legacy_layout(base)
            before = {
                str(path): (path.stat().st_mtime_ns, path.read_bytes())
                for path in base.rglob("*")
                if path.is_file()
            }

            _service, _destination, result, _preferences = self._run_service(
                base,
                inventory=inventory,
            )

            self.assertTrue(result.success)

            for path_str, (mtime_ns, content) in before.items():
                path = Path(path_str)
                self.assertEqual(path.stat().st_mtime_ns, mtime_ns)
                self.assertEqual(path.read_bytes(), content)


class MigrationFailureTests(unittest.TestCase):

    def test_verification_failure_rolls_back_and_leaves_preferences_unset(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            inventory = _build_synthetic_legacy_layout(base)
            destination = base / "Project X"
            state_path = base / "bootstrap" / "migration_state.json"
            preferences_path = base / "bootstrap" / "preferences.json"
            state_store = MigrationStateStore(state_path)
            preferences_manager = PreferencesManager(preferences_path)

            service = DataMigrationService(
                state_store=state_store,
                preferences_manager=preferences_manager,
            )

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                with patch(
                    "storage.migration.collect_legacy_inventory",
                    return_value=inventory,
                ):
                    with patch(
                        "storage.migration._verify_sqlite_files",
                        side_effect=MigrationError("simulated sqlite failure"),
                    ):
                        result = service.run(destination)

            self.assertFalse(result.success)
            self.assertTrue(result.rolled_back)
            self.assertIsNone(preferences_manager.get().data_directory)
            self.assertFalse(
                (destination / DATA_SUBDIR_DATABASES / "vessels.db").exists()
            )

    def test_newer_destination_file_aborts_migration(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            inventory = _build_synthetic_legacy_layout(base)
            destination = base / "Project X"
            state_path = base / "bootstrap" / "migration_state.json"
            preferences_path = base / "bootstrap" / "preferences.json"

            service = DataMigrationService(
                state_store=MigrationStateStore(state_path),
                preferences_manager=PreferencesManager(preferences_path),
            )
            preferences_manager = service._preferences_manager

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                with patch(
                    "storage.migration.collect_legacy_inventory",
                    return_value=inventory,
                ):
                    with patch(
                        "storage.migration._copy_file",
                        return_value=CopyAction.SKIPPED_NEWER_DESTINATION,
                    ):
                        result = service.run(destination)

            self.assertFalse(result.success)
            self.assertIn("newer", result.message.lower())

    def test_interrupted_migration_can_restart_after_rollback(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            inventory = _build_synthetic_legacy_layout(base)
            destination = base / "Project X"
            state_path = base / "bootstrap" / "migration_state.json"
            preferences_path = base / "bootstrap" / "preferences.json"
            state_store = MigrationStateStore(state_path)
            preferences_manager = PreferencesManager(preferences_path)

            service = DataMigrationService(
                state_store=state_store,
                preferences_manager=preferences_manager,
            )

            original_copy = _copy_file
            call_count = {"count": 0}

            def flaky_copy(source: Path, destination_path: Path) -> CopyAction:

                call_count["count"] += 1

                if call_count["count"] == 2:
                    raise OSError("simulated interrupted migration")

                return original_copy(source, destination_path)

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                with patch(
                    "storage.migration.collect_legacy_inventory",
                    return_value=inventory,
                ):
                    with patch("storage.migration._copy_file", side_effect=flaky_copy):
                        first = service.run(destination)

                    self.assertFalse(first.success)
                    self.assertTrue(first.rolled_back)

                    second = service.run(destination)

            self.assertTrue(second.success)
            self.assertEqual(second.phase, MigrationPhase.COMPLETED)
            self.assertIsNotNone(preferences_manager.get().data_directory)


class MigrationStateTests(unittest.TestCase):

    def test_migration_state_persists_across_store_round_trip(self) -> None:

        with isolated_temp_dir() as temp_dir:
            store = MigrationStateStore(Path(temp_dir) / "migration_state.json")
            state = MigrationState.new(
                Path(temp_dir) / "Project X",
                {"file_count": 3},
                destination_preexisting=False,
            )
            state.touch(phase=MigrationPhase.COPYING)
            state.copied_paths.append("databases/vessels.db")
            store.save(state)

            loaded = store.load()

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.phase, MigrationPhase.COPYING)
            self.assertEqual(loaded.copied_paths, ["databases/vessels.db"])

    def test_completed_migration_refuses_rollback(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            inventory = _build_synthetic_legacy_layout(base)
            state_path = base / "migration_state.json"
            preferences_path = base / "preferences.json"
            state_store = MigrationStateStore(state_path)
            preferences_manager = PreferencesManager(preferences_path)

            service = DataMigrationService(
                state_store=state_store,
                preferences_manager=preferences_manager,
            )

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                with patch(
                    "storage.migration.collect_legacy_inventory",
                    return_value=inventory,
                ):
                    result = service.run(base / "Project X")

            self.assertTrue(result.success)

            with self.assertRaises(MigrationError):
                service.rollback()


class MigrationPostCommitTests(unittest.TestCase):

    def test_post_commit_failure_keeps_data_and_marks_state_failed(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            inventory = _build_synthetic_legacy_layout(base)
            destination = base / "Project X"
            state_path = base / "bootstrap" / "migration_state.json"
            preferences_path = base / "bootstrap" / "preferences.json"
            state_store = MigrationStateStore(state_path)
            preferences_manager = PreferencesManager(preferences_path)

            service = DataMigrationService(
                state_store=state_store,
                preferences_manager=preferences_manager,
            )

            legacy_resolved = ResolvedDataRoot(
                path=inventory.data_root,
                mode=StorageMode.LEGACY,
                has_marker=False,
            )

            with patch(
                "preferences.preferences_manager.preferences_manager",
                preferences_manager,
            ):
                with patch(
                    "storage.migration.collect_legacy_inventory",
                    return_value=inventory,
                ):
                    with patch(
                        "storage.migration.resolve_data_root",
                        return_value=legacy_resolved,
                    ):
                        result = service.run(destination)

            self.assertFalse(result.success)
            self.assertFalse(result.rolled_back)
            self.assertIn("Fatal migration error", result.message)
            self.assertEqual(
                preferences_manager.get().data_directory,
                str(destination.resolve()),
            )
            self.assertTrue((destination / DATA_SUBDIR_DATABASES / "vessels.db").is_file())

            saved_state = state_store.load()
            self.assertIsNotNone(saved_state)
            assert saved_state is not None
            self.assertEqual(saved_state.phase, MigrationPhase.FAILED)
            self.assertIn("post-commit", (saved_state.error or "").lower())


class UpgradePromptTests(unittest.TestCase):

    def test_should_offer_data_upgrade_for_existing_legacy_user(self) -> None:

        from gui.data_upgrade_dialog import should_offer_data_upgrade

        with patch(
            "app.startup_mode.should_offer_legacy_upgrade",
            return_value=True,
        ):
            self.assertTrue(should_offer_data_upgrade(first_run_pending=False))

    def test_should_not_offer_data_upgrade_for_first_run(self) -> None:

        from gui.data_upgrade_dialog import should_offer_data_upgrade

        with patch(
            "app.startup_mode.should_offer_legacy_upgrade",
            return_value=False,
        ):
            self.assertFalse(should_offer_data_upgrade(first_run_pending=True))

    def test_should_not_offer_data_upgrade_when_deferred(self) -> None:

        from gui.data_upgrade_dialog import should_offer_data_upgrade

        with patch(
            "app.startup_mode.should_offer_legacy_upgrade",
            return_value=False,
        ):
            self.assertFalse(should_offer_data_upgrade(first_run_pending=False))


class PreferencesMigrationDeferTests(unittest.TestCase):

    def test_legacy_migration_deferred_round_trip(self) -> None:

        with isolated_temp_dir() as temp_dir:
            manager = PreferencesManager(Path(temp_dir) / "preferences.json")
            updated = manager.set_legacy_migration_deferred(True)

            self.assertTrue(updated.legacy_migration_deferred)
            self.assertTrue(manager.get().legacy_migration_deferred)

    def test_storage_activation_deferred_until_restart_round_trip(self) -> None:

        with isolated_temp_dir() as temp_dir:
            manager = PreferencesManager(Path(temp_dir) / "preferences.json")
            updated = manager.set_storage_activation_deferred_until_restart(True)

            self.assertTrue(updated.storage_activation_deferred_until_restart)
            self.assertTrue(manager.get().storage_activation_deferred_until_restart)


class ConfiguredRootDeferTests(unittest.TestCase):

    def test_configured_data_root_ignored_while_activation_deferred(self) -> None:

        with isolated_temp_dir() as temp_dir:
            root = Path(temp_dir) / "Project X"
            preferences_path = Path(temp_dir) / "preferences.json"
            manager = PreferencesManager(preferences_path)
            manager.set_data_directory(str(root))
            manager.set_storage_activation_deferred_until_restart(True)

            with patch(
                "preferences.preferences_manager.preferences_manager",
                manager,
            ):
                self.assertIsNone(configured_data_root())

    def test_startup_prepare_clears_deferred_activation(self) -> None:

        with isolated_temp_dir() as temp_dir:
            root = Path(temp_dir) / "Project X"
            preferences_path = Path(temp_dir) / "preferences.json"
            manager = PreferencesManager(preferences_path)
            manager.set_data_directory(str(root))
            manager.set_storage_activation_deferred_until_restart(True)

            with patch(
                "preferences.preferences_manager.preferences_manager",
                manager,
            ):
                from app.application import _prepare_storage_for_startup

                _prepare_storage_for_startup()
                self.assertFalse(
                    manager.get().storage_activation_deferred_until_restart
                )


class MigrationRestartTests(unittest.TestCase):

    def test_relaunch_command_in_development_mode(self) -> None:

        from app.restart import relaunch_command

        with patch("app.restart.sys") as mock_sys:
            mock_sys.frozen = False
            mock_sys.executable = "/usr/bin/python3"
            mock_sys.argv = ["main.py"]

            command = relaunch_command()

        self.assertEqual(command[0], "/usr/bin/python3")
        self.assertTrue(str(command[1]).endswith("main.py"))


class MigrationCopyPolicyTests(unittest.TestCase):

    def test_copy_skips_identical_destination_file(self) -> None:

        with isolated_temp_dir() as temp_dir:
            source = Path(temp_dir) / "source.txt"
            destination = Path(temp_dir) / "dest.txt"
            source.write_text("same", encoding="utf-8")
            destination.write_text("same", encoding="utf-8")

            action = _copy_file(source, destination)

            self.assertEqual(action, CopyAction.SKIPPED_IDENTICAL)


if __name__ == "__main__":
    unittest.main()
