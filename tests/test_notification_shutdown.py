#!/usr/bin/env python3
"""Unit tests for notification shutdown lifecycle."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gui.notifications.notification_manager import NotificationManager
from gui.notifications.severity import NotificationSeverity


class NotificationShutdownTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:

        NotificationManager._instance = None

    def test_shutdown_closes_visible_sticky_banner(self) -> None:

        manager = NotificationManager.instance()
        manager.show(
            "AIS connection lost.",
            severity=NotificationSeverity.WARNING,
            key="ais.connection",
            sticky=True,
        )

        banner = manager._banner
        self.assertFalse(banner.isHidden())

        manager.shutdown()

        self.assertTrue(banner.isHidden())
        self.assertTrue(manager._shutdown)

    def test_shutdown_is_idempotent(self) -> None:

        manager = NotificationManager.instance()
        manager.show(
            "Warning",
            severity=NotificationSeverity.WARNING,
            sticky=True,
        )

        manager.shutdown()
        manager.shutdown()

        self.assertTrue(manager._banner.isHidden())
        self.assertTrue(manager._shutdown)

    def test_double_shutdown_via_close_and_about_to_quit(self) -> None:

        manager = NotificationManager.instance()
        manager.show(
            "AIS connection lost.",
            severity=NotificationSeverity.WARNING,
            key="ais.connection",
            sticky=True,
        )

        banner = manager._banner

        manager.shutdown()
        manager.shutdown()

        self.assertTrue(banner._destroyed)
        self.assertTrue(banner.isHidden())

    def test_force_dismiss_closes_without_exit_animation(self) -> None:

        manager = NotificationManager.instance()
        manager.show(
            "Warning",
            severity=NotificationSeverity.WARNING,
            key="test.warning",
            sticky=True,
        )

        manager.dismiss("test.warning")

        self.assertIsNone(manager._current)
        self.assertTrue(manager._banner.isHidden())


if __name__ == "__main__":
    unittest.main()
