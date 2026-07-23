# ============================================================================
# Project X
# Logging Configuration (SAVE-202 — single initialization)
# ============================================================================

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False

_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _resolve_level() -> int:

    level_name = os.environ.get("PROJECTX_LOG_LEVEL", "").strip().upper()

    if level_name in _LEVELS:
        return _LEVELS[level_name]

    if os.environ.get("PROJECTX_DEBUG"):
        return logging.DEBUG

    return logging.WARNING


def _log_dir() -> Path:

    candidates = []

    if os.name == "nt":
        candidates.append(
            Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Project X" / "logs"
        )
    else:
        candidates.append(Path.home() / ".local" / "share" / "projectx" / "logs")

    try:
        from app.paths import runtime_data_dir

        candidates.append(runtime_data_dir() / "logs")
    except Exception:
        pass

    last_error: Exception | None = None

    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as error:
            last_error = error

    raise RuntimeError(f"Unable to create log directory: {last_error}")


def configure_logging() -> None:
    """Initialize console + rotating file logging once for the whole app."""

    global _CONFIGURED

    if _CONFIGURED:
        return

    level = _resolve_level()
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(
            logging.Formatter("%(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(console)

    file_level = logging.DEBUG if os.environ.get("PROJECTX_DEBUG") else level
    log_path = _log_dir() / "projectx.log"
    has_file = any(
        isinstance(h, RotatingFileHandler)
        and getattr(h, "baseFilename", "") == str(log_path)
        for h in root.handlers
    )

    if not has_file:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Project X named logger used by legacy imports of core.logger
    app_logger = logging.getLogger("Project X")
    app_logger.setLevel(level)
    app_logger.propagate = True

    _CONFIGURED = True
