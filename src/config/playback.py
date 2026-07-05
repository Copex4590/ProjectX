# ============================================================================
# Project X
# Playback configuration
# ============================================================================

import os
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent

PLAYBACK_PREFERENCES_FILE = Path(
    os.environ.get(
        "PROJECTX_PLAYBACK_PREFERENCES_FILE",
        str(_CONFIG_DIR / "playback.json"),
    )
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
