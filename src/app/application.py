# ============================================================================
# Project X
# File    : application.py
# Module  : Application
# Version : 0.3.0-alpha
# ============================================================================

import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.mainwindow import MainWindow
from branding.assets import app_icon
from gui.splashscreen import create_splash_screen
from version import PROJECT_NAME, PROJECT_VERSION


class Application:
    """
    Main application controller.
    Responsible for creating and running the GUI.
    """

    _SPLASH_MIN_MS = 2000
    _SPLASH_MAX_MS = 3000

    def __init__(self):

        self.qt = QApplication(sys.argv)
        self.qt.setApplicationName(PROJECT_NAME)
        self.qt.setApplicationVersion(PROJECT_VERSION)
        self.qt.setOrganizationName("Project X")
        self.qt.setWindowIcon(app_icon())

        self._splash = create_splash_screen()
        self._splash.show()
        self.qt.processEvents()

        self._startup_started = time.monotonic()
        self.window = MainWindow()

    def run(self):

        elapsed_ms = int((time.monotonic() - self._startup_started) * 1000)
        remaining_ms = max(0, self._SPLASH_MIN_MS - elapsed_ms)
        remaining_ms = min(remaining_ms, self._SPLASH_MAX_MS)

        QTimer.singleShot(remaining_ms, self._finish_startup)
        return self.qt.exec()

    def _finish_startup(self) -> None:

        self._splash.finish(self.window)
        self.window.show()
