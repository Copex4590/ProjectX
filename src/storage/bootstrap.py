# ============================================================================
# Project X
# Bootstrap Profile Paths
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path

from app.paths import bundle_dir, is_frozen

_BOOTSTRAP_DIR_NAME = "projectx"
_WINDOWS_APP_NAME = "Project X"


def bootstrap_profile_dir() -> Path:
    """Fixed OS profile directory for bootstrap metadata only."""

    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home())
        path = base / _WINDOWS_APP_NAME
    else:
        path = Path.home() / ".local" / "share" / _BOOTSTRAP_DIR_NAME

    path.mkdir(parents=True, exist_ok=True)
    return path


def bootstrap_config_dir() -> Path:
    """Directory for bootstrap configuration such as preferences.json."""

    if is_frozen():
        path = bootstrap_profile_dir() / "config"
    else:
        path = bundle_dir() / "config"

    path.mkdir(parents=True, exist_ok=True)
    return path


def bootstrap_config_path(filename: str) -> Path:
    """Resolve a bootstrap configuration file path."""

    return bootstrap_config_dir() / filename
