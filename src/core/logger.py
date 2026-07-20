from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from storage.deferred_paths import deferred_log_path

APP_NAME = "Project X"


def log_file() -> Path:
    """Return the active application log file path."""

    return deferred_log_path("PROJECTX_LOG_FILE", "projectx.log")


def _ensure_log_file() -> Path:

    path = log_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class _DeferredRotatingFileHandler(logging.Handler):
    """Attach the rotating log file only when the first record is emitted."""

    def __init__(self) -> None:
        super().__init__()
        self._handler: RotatingFileHandler | None = None

    def _real_handler(self) -> RotatingFileHandler:
        if self._handler is None:
            self._handler = RotatingFileHandler(
                _ensure_log_file(),
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            self._handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
        return self._handler

    def emit(self, record: logging.LogRecord) -> None:
        self._real_handler().emit(record)

    def flush(self) -> None:
        if self._handler is not None:
            self._handler.flush()

    def close(self) -> None:
        if self._handler is not None:
            self._handler.close()


logger = logging.getLogger(APP_NAME)

if not logger.handlers:

    logger.setLevel(logging.DEBUG)
    logger.addHandler(_DeferredRotatingFileHandler())


def __getattr__(name: str):
    if name == "LOG_FILE":
        return log_file()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
