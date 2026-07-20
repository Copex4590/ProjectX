#!/usr/bin/env python3
"""SAVE-107-C6 completion verification for Phase C first-run storage."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from isolated_paths import isolated_temp_dir
from app.startup_mode import (
    StartupMode,
    determine_startup_mode,
    needs_data_root_wizard,
    should_offer_legacy_upgrade,
)
from gui.data_location_wizard import DataLocationWizard, run_data_location_setup_if_needed
from preferences.preferences import Preferences
from preferences.preferences_manager import PreferencesManager
from storage import (
    DATA_ROOT_MARKER_NAME,
    StorageMode,
    configured_data_root,
    is_valid_data_root,
    resolve_data_root,
)
from storage.data_root_initialization import DataRootInitializationService
from storage.data_root_validation import (
    DataRootValidationResult,
    DataRootValidationService,
    ValidationSeverity,
)


class Save107C6InitializationTests(unittest.TestCase):

    def _initialize_with_manager(
        self,
        target: Path,
        *,
        preferences_path: Path,
    ):
        preferences_manager = PreferencesManager(preferences_path)
        service = DataRootInitializationService(
            preferences_manager=preferences_manager,
        )

        with patch(
            "preferences.preferences_manager.preferences_manager",
            preferences_manager,
        ):
            result = service.initialize(target)

        return result, preferences_manager

    def test_recommended_location_initialization(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            target = base / "Project X"
            preferences_path = base / "bootstrap" / "preferences.json"

            result, preferences_manager = self._initialize_with_manager(
                target,
                preferences_path=preferences_path,
            )

            self.assertTrue(result.success, result.message)
            self.assertEqual(result.mode, StorageMode.CONFIGURED)
            assert result.data_root is not None
            self.assertTrue(is_valid_data_root(result.data_root))
            self.assertEqual(
                preferences_manager.get().data_directory,
                str(result.data_root),
            )

    def test_custom_location_initialization(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            target = base / "Maritime Data"
            preferences_path = base / "bootstrap" / "preferences.json"

            result, preferences_manager = self._initialize_with_manager(
                target,
                preferences_path=preferences_path,
            )

            self.assertTrue(result.success, result.message)
            assert result.data_root is not None
            self.assertEqual(result.data_root, target.resolve())
            self.assertTrue((result.data_root / DATA_ROOT_MARKER_NAME).is_file())
            self.assertEqual(
                preferences_manager.get().data_directory,
                str(result.data_root),
            )


class Save107C6ValidationTests(unittest.TestCase):

    def setUp(self) -> None:

        self.service = DataRootValidationService()

    def test_invalid_directory_rejection(self) -> None:

        result = self.service.validate(Path("   "))

        self.assertFalse(result.valid)
        self.assertEqual(result.severity, ValidationSeverity.ERROR)
        self.assertTrue(result.blocks_completion)

    def test_existing_marker_allows_completion(self) -> None:

        with isolated_temp_dir() as temp_dir:
            from storage import ensure_data_layout

            existing = Path(temp_dir) / "Project X"
            ensure_data_layout(existing)

            result = self.service.validate(existing)

            self.assertTrue(result.valid)
            self.assertEqual(result.severity, ValidationSeverity.NONE)
            self.assertFalse(result.blocks_completion)


class Save107C6WizardCompletionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._app = QApplication.instance() or QApplication([])

    def test_warning_does_not_block_finish(self) -> None:

        with isolated_temp_dir() as temp_dir:
            target = Path(temp_dir) / "Project X"
            target.mkdir()
            (target / "notes.txt").write_text("existing", encoding="utf-8")

            wizard = DataLocationWizard()
            wizard.show()
            QApplication.processEvents()
            wizard._page.set_custom_directory(target)
            wizard._page._custom_option.setChecked(True)
            wizard._validate_current_selection()

            self.assertTrue(wizard._finish_button.isEnabled())
            self.assertFalse(wizard._page._error_label.isVisible())
            self.assertTrue(wizard._page._warning_label.isVisible())
            self.assertIn("not empty", wizard._page._warning_label.text().lower())

    def test_error_blocks_finish(self) -> None:

        wizard = DataLocationWizard()
        error = DataRootValidationResult.error(Path("."), "Invalid selection.")

        with patch.object(wizard._validation_service, "validate", return_value=error):
            wizard._validate_current_selection()

        self.assertFalse(wizard._finish_button.isEnabled())

    def test_existing_data_root_enables_next(self) -> None:

        with isolated_temp_dir() as temp_dir:
            from storage import ensure_data_layout

            existing = Path(temp_dir) / "Project X"
            ensure_data_layout(existing)

            wizard = DataLocationWizard()
            wizard.show()
            QApplication.processEvents()
            wizard._page.set_custom_directory(existing)
            wizard._page._custom_option.setChecked(True)
            wizard._validate_current_selection()

            self.assertTrue(wizard._finish_button.isEnabled())
            self.assertFalse(wizard._page._error_label.isVisible())
            self.assertFalse(wizard._page._warning_label.isVisible())


class Save107C6PersistenceAndRestartTests(unittest.TestCase):

    def test_preferences_persistence_and_configured_restart(self) -> None:

        with isolated_temp_dir() as temp_dir:
            base = Path(temp_dir)
            target = base / "Project X"
            preferences_path = base / "bootstrap" / "preferences.json"

            writer = PreferencesManager(preferences_path)
            service = DataRootInitializationService(preferences_manager=writer)

            with patch(
                "preferences.preferences_manager.preferences_manager",
                writer,
            ):
                result = service.initialize(target)

            self.assertTrue(result.success, result.message)

            restarted_manager = PreferencesManager(preferences_path)

            with patch(
                "preferences.preferences_manager.preferences_manager",
                restarted_manager,
            ):
                self.assertEqual(
                    configured_data_root(),
                    result.data_root,
                )
                resolved = resolve_data_root()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertEqual(resolved.path, result.data_root)
            self.assertTrue(resolved.has_marker)


class Save107C6StartupExclusionTests(unittest.TestCase):

    def test_existing_users_never_enter_first_run_storage_wizard(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("app.startup_mode.legacy_data_exists", return_value=True):
                    with patch(
                        "app.startup_mode.has_observation_points",
                        return_value=True,
                    ):
                        self.assertFalse(needs_data_root_wizard())
                        with patch(
                            "gui.data_location_wizard.needs_data_root_wizard",
                            return_value=False,
                        ):
                            self.assertTrue(run_data_location_setup_if_needed())

    def test_legacy_users_enter_upgrade_path(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("app.startup_mode.legacy_data_exists", return_value=True):
                    with patch(
                        "app.startup_mode.has_observation_points",
                        return_value=True,
                    ):
                        plan = determine_startup_mode()

        self.assertEqual(plan.mode, StartupMode.LEGACY_UPGRADE)
        self.assertTrue(plan.needs_legacy_upgrade)

    def test_fresh_installations_never_see_upgrade_dialog(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("app.startup_mode.legacy_data_exists", return_value=False):
                    with patch(
                        "app.startup_mode.has_observation_points",
                        return_value=False,
                    ):
                        self.assertFalse(should_offer_legacy_upgrade())
                        plan = determine_startup_mode()

        self.assertEqual(plan.mode, StartupMode.FIRST_RUN_SETUP)
        self.assertFalse(plan.needs_legacy_upgrade)


if __name__ == "__main__":
    unittest.main()
