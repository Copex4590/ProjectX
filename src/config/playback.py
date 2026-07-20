# ============================================================================
# Project X
# Playback configuration
# ============================================================================

import os
from pathlib import Path

from storage.deferred_paths import deferred_config_path


def playback_preferences_file() -> Path:
    """Return the active playback preferences file path."""

    return deferred_config_path(
        "PROJECTX_PLAYBACK_PREFERENCES_FILE",
        "playback.json",
    )

DEFAULT_PLAYBACK_MODE = os.environ.get(
    "PROJECTX_PLAYBACK_MODE",
    "automatic",
).strip().lower()

DEFAULT_PREFERRED_BACKEND = os.environ.get(
    "PROJECTX_PLAYBACK_BACKEND",
    "mpv",
).strip().lower()

DEFAULT_CUSTOM_EXECUTABLE = os.environ.get(
    "PROJECTX_PLAYBACK_CUSTOM_EXECUTABLE",
    "",
).strip()

DEFAULT_CUSTOM_ARGUMENTS = os.environ.get(
    "PROJECTX_PLAYBACK_CUSTOM_ARGUMENTS",
    "",
).strip()


def __getattr__(name: str):
    if name == "PLAYBACK_PREFERENCES_FILE":
        return playback_preferences_file()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
