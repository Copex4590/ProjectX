# ============================================================================
# Project X
# Application Paths (development + PyInstaller)
# ============================================================================

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:

    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def bundle_dir() -> Path:

    if is_frozen():
        return Path(sys._MEIPASS)

    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:

    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home())
        path = base / "Project X"
    else:
        path = Path.home() / ".local" / "share" / "projectx"

    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_config_dir() -> Path:

    if is_frozen():
        path = user_data_dir() / "config"
        path.mkdir(parents=True, exist_ok=True)
        return path

    path = bundle_dir() / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_data_dir() -> Path:

    if is_frozen():
        path = user_data_dir() / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    return bundle_dir().parent / "data"


def resource_path(*parts: str) -> Path:

    return bundle_dir().joinpath("resources", *parts)


def bundled_config_dir() -> Path:

    return bundle_dir() / "config"


def runtime_config_path(filename: str) -> Path:

    return runtime_config_dir() / filename


def runtime_data_path(filename: str) -> Path:

    return runtime_data_dir() / filename
