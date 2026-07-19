# ============================================================================
# Project X
# File    : application.py
# Module  : Application
# Version : 0.3.0-alpha
# ============================================================================

import logging
import sys
import time

from storage import ensure_active_layout

ensure_active_layout()

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app.logging_config import configure_logging
from app.mainwindow import MainWindow
from app.single_instance import ensure_single_instance
from branding.assets import app_icon
from gui.notifications import notification_manager
from gui.languagewelcome_dialog import run_language_welcome_if_needed
from gui.splashscreen import create_splash_screen
from gui.theme import global_stylesheet
from i18n import tr
from version import PROJECT_NAME, PROJECT_VERSION

logger = logging.getLogger(__name__)

_STARTUP_T0: float | None = None


def _startup_elapsed_ms() -> int:

    if _STARTUP_T0 is None:
        return 0

    return int((time.monotonic() - _STARTUP_T0) * 1000)


def _log_startup_phase(phase: str) -> None:

    logger.info("Startup timing: %s at %d ms", phase, _startup_elapsed_ms())


def _is_first_run_pending() -> bool:

    from observation import observation_manager

    return not observation_manager.all()


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

        global _STARTUP_T0
        _STARTUP_T0 = time.monotonic()

        configure_logging()
        _install_exception_hook()
        _log_startup_phase("storage layout and logging ready")

        self.qt = QApplication(sys.argv)
        self.qt.setApplicationName(PROJECT_NAME)
        self.qt.setApplicationVersion(PROJECT_VERSION)
        self.qt.setOrganizationName("Project X")
        self.qt.setWindowIcon(app_icon())
        self.qt.setStyleSheet(global_stylesheet())
        _log_startup_phase("QApplication created")

        self._single_instance_lock = ensure_single_instance()
        _log_startup_phase("single-instance lock acquired")

        self.qt.aboutToQuit.connect(notification_manager().shutdown)

        if not run_language_welcome_if_needed():
            raise SystemExit(0)

        _log_startup_phase("language welcome complete")

        self._first_run_pending = _is_first_run_pending()
        self._splash = None

        if not self._first_run_pending:
            self._splash = create_splash_screen()
            self._splash.show()
            self.qt.processEvents()
            _log_startup_phase("splash screen visible")

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

        _log_startup_phase("MainWindow constructed")

    def run(self):

        if self._first_run_pending:
            _log_startup_phase("first-run startup scheduled")
            self.window.show()
            QTimer.singleShot(0, self._begin_first_run)
            return self.qt.exec()

        elapsed_ms = int((time.monotonic() - self._startup_started) * 1000)
        remaining_ms = max(0, self._SPLASH_MIN_MS - elapsed_ms)
        remaining_ms = min(remaining_ms, self._SPLASH_MAX_MS)

        QTimer.singleShot(remaining_ms, self._finish_startup)
        return self.qt.exec()

    def _begin_first_run(self) -> None:

        _log_startup_phase("first-run wizard opening")
        self.window.navigate_to_map()
        self.window.run_first_run_wizard()
        _log_startup_phase("first-run wizard complete")

    def _finish_startup(self) -> None:

        if self._splash is not None:
            self._splash.finish(self.window)
        self.window.show()
        _log_startup_phase("main window visible")
