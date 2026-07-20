#!/usr/bin/env python3
"""Regression tests for lazy singleton module proxy exports."""

from __future__ import annotations

import os
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preferences.preferences import Preferences


class LazySingletonModuleProxyTests(unittest.TestCase):

    def _fresh_install_context(self) -> ExitStack:
        stack = ExitStack()
        stack.enter_context(patch.dict(os.environ, {}, clear=True))
        stack.enter_context(
            patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            )
        )
        stack.enter_context(patch("storage.manager.configured_data_root", return_value=None))
        stack.enter_context(patch("storage.legacy.legacy_data_exists", return_value=False))
        stack.enter_context(
            patch("storage.resolver.requires_data_root_setup", return_value=True)
        )
        return stack

    def test_package_import_binds_submodule_for_logbook_recorder(self) -> None:
        import types

        from logbook import logbook_recorder as package_import

        self.assertIsInstance(package_import, types.ModuleType)

    def test_submodule_delegates_start_without_storage_at_import(self) -> None:
        with self._fresh_install_context():
            from logbook import logbook_recorder

            self.assertTrue(callable(logbook_recorder.start))

    def test_mainwindow_import_symbols_expose_runtime_api(self) -> None:
        with self._fresh_install_context():
            import types

            from ais import ais_manager
            from logbook import logbook_recorder
            from observation import observation_manager
            from observation.observation_manager import ObservationManager

            self.assertIsInstance(logbook_recorder, types.ModuleType)
            self.assertIsInstance(observation_manager, types.ModuleType)
            self.assertTrue(callable(logbook_recorder.start))
            self.assertTrue(callable(ais_manager.start))
            self.assertTrue(hasattr(ObservationManager, "all"))


if __name__ == "__main__":
    unittest.main()
