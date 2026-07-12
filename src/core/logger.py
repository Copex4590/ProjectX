from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os

APP_NAME = "Project X"


def _log_dir() -> Path:

    if os.name == "nt":
        base = Path(os.environ["LOCALAPPDATA"]) / APP_NAME
    else:
        base = Path.home() / ".local" / "share" / APP_NAME

    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir


logger = logging.getLogger(APP_NAME)

if not logger.handlers:

    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        _log_dir() / "projectx.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)
