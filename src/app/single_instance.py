# ============================================================================
# Project X
# Single-instance protection (QLockFile)
# ============================================================================

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from app.paths import runtime_config_dir

_LOCK_FILE_NAME = "projectx.lock"
_ALREADY_RUNNING_TITLE = "Project X"
_ALREADY_RUNNING_MESSAGE = (
    "Project X is already running.\n\n"
    "Only one instance of Project X can run at a time."
)


def _lock_file_path() -> Path:

    config_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )

    if config_dir:
        path = Path(config_dir)
    else:
        path = runtime_config_dir()

    path.mkdir(parents=True, exist_ok=True)
    return path / _LOCK_FILE_NAME


class SingleInstanceLock:
    """Holds a process-wide QLockFile for the lifetime of the application."""

    def __init__(self, lock_file: QLockFile):
        self._lock_file = lock_file

    def release(self) -> None:

        if self._lock_file.isLocked():
            self._lock_file.unlock()


def acquire_single_instance_lock() -> SingleInstanceLock | None:
    """Acquire the single-instance lock or prompt and return None."""

    lock_file = QLockFile(str(_lock_file_path()))
    lock_file.setStaleLockTime(0)

    if lock_file.tryLock():
        return SingleInstanceLock(lock_file)

    QMessageBox.information(
        None,
        _ALREADY_RUNNING_TITLE,
        _ALREADY_RUNNING_MESSAGE,
    )
    return None


def ensure_single_instance() -> SingleInstanceLock:
    """Acquire the lock or exit the process with code 0."""

    lock = acquire_single_instance_lock()

    if lock is None:
        app = QApplication.instance()

        if app is not None:
            app.quit()

        sys.exit(0)

    app = QApplication.instance()

    if app is not None:
        app.aboutToQuit.connect(lock.release)

    return lock
