# ============================================================================
# Project X
# Application Restart Helpers
# ============================================================================

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication

from app.single_instance import SingleInstanceLock
from gui.notifications import notification_manager

logger = logging.getLogger(__name__)


def relaunch_command() -> list[str]:
    """Build the command line used to start a fresh Project X instance."""

    if getattr(sys, "frozen", False):
        return [sys.executable, *sys.argv[1:]]

    main_py = Path(__file__).resolve().parents[1] / "main.py"
    return [sys.executable, str(main_py), *sys.argv[1:]]


def request_application_restart(
    app: QApplication,
    single_instance_lock: SingleInstanceLock,
) -> None:
    """Shut down cleanly and relaunch Project X."""

    notification_manager().shutdown()
    single_instance_lock.release()

    command = relaunch_command()
    program = command[0]
    arguments = command[1:]

    logger.info("Restarting Project X: %s", command)

    if not QProcess.startDetached(program, arguments):
        logger.error("Failed to relaunch Project X: %s", command)
        app.quit()
        return

    app.quit()
