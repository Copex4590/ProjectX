from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from storage import active_log_path

APP_NAME = "Project X"
LOG_FILE = active_log_path("projectx.log")


def _ensure_log_file() -> Path:

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    return LOG_FILE


logger = logging.getLogger(APP_NAME)

if not logger.handlers:

    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        _ensure_log_file(),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)
