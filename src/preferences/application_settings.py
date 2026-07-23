# ============================================================================
# Project X
# Application settings runtime helpers (SAVE-211)
# ============================================================================

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from preferences.preferences import (
    DEFAULT_LOG_LEVEL,
    SUPPORTED_LOG_LEVELS,
    Preferences,
)
from preferences.preferences_manager import preferences_manager

logger = logging.getLogger(__name__)

_STARTUP_PAGE_INDEX = {
    "dashboard": 0,
    "map": 1,
    "vessels": 2,
    "cameras": 3,
    "system_health": 9,
    "settings": 12,
}

_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def startup_page_index(preferences: Preferences | None = None) -> int:

    prefs = preferences or preferences_manager.get()
    return _STARTUP_PAGE_INDEX.get(prefs.startup_page, 0)


def apply_log_level(level_name: str | None = None) -> str:

    name = str(level_name or preferences_manager.get().log_level).strip().upper()

    if name not in SUPPORTED_LOG_LEVELS:
        name = DEFAULT_LOG_LEVEL

    level = _LEVELS[name]
    root = logging.getLogger()
    root.setLevel(level)

    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler,
            RotatingFileHandler,
        ):
            handler.setLevel(level)

    logging.getLogger("Project X").setLevel(level)
    return name


def apply_runtime_settings(preferences: Preferences | None = None) -> Preferences:

    prefs = preferences or preferences_manager.get()
    apply_log_level(prefs.log_level)
    return prefs


def desktop_notifications_enabled() -> bool:

    return bool(preferences_manager.get().notifications_desktop)


def sounds_enabled() -> bool:

    return bool(preferences_manager.get().notifications_sounds)


def diagnostics_enabled() -> bool:

    return bool(preferences_manager.get().diagnostics_enabled)


def developer_mode_enabled() -> bool:

    return bool(preferences_manager.get().developer_mode)
