#!/usr/bin/env python3
"""Unit tests for centralized startup mode decisions (SAVE-107-C5)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.startup_mode import (
    StartupMode,
    determine_startup_mode,
    is_existing_user,
    needs_data_root_wizard,
    should_offer_legacy_upgrade,
)
from preferences.preferences import Preferences


class StartupModeDecisionTests(unittest.TestCase):

    def test_fresh_install_uses_first_run_setup(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("app.startup_mode.legacy_data_exists", return_value=False):
                    with patch("app.startup_mode.requires_data_root_setup", return_value=True):
                        with patch(
                            "app.startup_mode.has_observation_points",
                            return_value=False,
                        ):
                            plan = determine_startup_mode()

        self.assertEqual(plan.mode, StartupMode.FIRST_RUN_SETUP)
        self.assertTrue(plan.needs_data_root_wizard)
        self.assertTrue(plan.needs_observation_wizard)
        self.assertFalse(plan.needs_legacy_upgrade)

    def test_existing_legacy_user_uses_legacy_upgrade(self) -> None:

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
        self.assertFalse(plan.needs_data_root_wizard)

    def test_existing_user_never_needs_data_root_wizard(self) -> None:

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
                        self.assertTrue(is_existing_user())
                        self.assertFalse(needs_data_root_wizard())

    def test_configured_user_uses_normal_startup(self) -> None:

        preferences = Preferences.defaults()
        preferences.data_directory = "/tmp/Project X"

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=preferences,
            ):
                with patch("app.startup_mode.has_observation_points", return_value=True):
                    plan = determine_startup_mode()

        self.assertEqual(plan.mode, StartupMode.NORMAL)
        self.assertFalse(plan.needs_data_root_wizard)
        self.assertFalse(plan.needs_observation_wizard)
        self.assertTrue(plan.show_splash)

    def test_deferred_migration_uses_normal_startup(self) -> None:

        preferences = Preferences.defaults()
        preferences.legacy_migration_deferred = True

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=preferences,
            ):
                with patch("app.startup_mode.legacy_data_exists", return_value=True):
                    with patch(
                        "app.startup_mode.has_observation_points",
                        return_value=True,
                    ):
                        with patch(
                            "app.startup_mode.should_offer_legacy_upgrade",
                            return_value=False,
                        ):
                            plan = determine_startup_mode()
                            self.assertFalse(should_offer_legacy_upgrade())

        self.assertEqual(plan.mode, StartupMode.NORMAL)

    def test_first_run_pending_never_offers_legacy_upgrade(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("app.startup_mode.legacy_data_exists", return_value=True):
                    with patch(
                        "app.startup_mode.has_observation_points",
                        return_value=False,
                    ):
                        self.assertFalse(should_offer_legacy_upgrade())
                        plan = determine_startup_mode()

        self.assertEqual(plan.mode, StartupMode.NORMAL)
        self.assertFalse(plan.needs_data_root_wizard)
        self.assertFalse(plan.needs_observation_wizard)


    def test_has_observation_points_skips_storage_before_data_root_setup(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "app.startup_mode.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                with patch("app.startup_mode.configured_data_root", return_value=None):
                    with patch(
                        "app.startup_mode.requires_data_root_setup",
                        return_value=True,
                    ):
                        from app.startup_mode import has_observation_points

                        self.assertFalse(has_observation_points())


if __name__ == "__main__":
    unittest.main()
