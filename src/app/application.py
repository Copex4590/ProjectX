# ============================================================================
# Project X
# File    : application.py
# Module  : Application
# Version : 0.3.0-alpha
# ============================================================================

import logging
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app.logging_config import configure_logging
from app.mainwindow import MainWindow
from app.paths import ensure_runtime_data_dirs
from branding.assets import app_icon
from gui.splashscreen import create_splash_screen
from i18n import tr
from version import PROJECT_NAME, PROJECT_VERSION

logger = logging.getLogger(__name__)


def _is_first_run_pending() -> bool:

    from observation import observation_manager
    from preferences import preferences_manager

    if observation_manager.all():
        return False

    return not preferences_manager.get().first_run_completed


def _install_exception_hook() -> None:

    def handle_exception(exc_type, exc_value, exc_traceback) -> None:

        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.error(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

        message = tr(
            "Project X could not start because an unexpected error occurred."
        )

        detail = str(exc_value).strip() or exc_type.__name__
        if detail and detail != exc_type.__name__:
            message = f"{message}\n\n{detail}"

        app = QApplication.instance()

        if app is not None:
            QMessageBox.critical(None, PROJECT_NAME, message)

    sys.excepthook = handle_exception


class Application:
    """
    Main application controller.
    Responsible for creating and running the GUI.
    """

    _SPLASH_MIN_MS = 2000
    _SPLASH_MAX_MS = 3000

    def __init__(self):

        configure_logging()
        _install_exception_hook()
        ensure_runtime_data_dirs()

        self.qt = QApplication(sys.argv)
        self.qt.setApplicationName(PROJECT_NAME)
        self.qt.setApplicationVersion(PROJECT_VERSION)
        self.qt.setOrganizationName("Project X")
        self.qt.setWindowIcon(app_icon())

        self._first_run_pending = _is_first_run_pending()
        self._splash = None

        if not self._first_run_pending:
            self._splash = create_splash_screen()
            self._splash.show()
            self.qt.processEvents()

        self._startup_started = time.monotonic()

        try:
            self.window = MainWindow()
        except Exception:
            logger.exception("Failed to create main window")
            QMessageBox.critical(
                None,
                PROJECT_NAME,
                tr(
                    "Project X could not start because the main window "
                    "failed to initialize."
                ),
            )
            raise

    def run(self):

        if self._first_run_pending:
            self.window.run_first_run_wizard()
            self.window.show()
            return self.qt.exec()

        elapsed_ms = int((time.monotonic() - self._startup_started) * 1000)
        remaining_ms = max(0, self._SPLASH_MIN_MS - elapsed_ms)
        remaining_ms = min(remaining_ms, self._SPLASH_MAX_MS)

        QTimer.singleShot(remaining_ms, self._finish_startup)
        return self.qt.exec()

    def _finish_startup(self) -> None:

        if self._splash is not None:
            self._splash.finish(self.window)
        self.window.show()
