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


_RUNTIME_DATA_SUBDIRS = (
    "Hajók",
    "vessel_photos",
    "hybrid",
    "hybrid/deli_hajok",
)


def backups_dir() -> Path:
    """Project X backups directory (…/ProjectX/backups or user-data/backups)."""

    override = os.environ.get("PROJECTX_BACKUPS_DIR", "").strip()
    if override:
        path = Path(override)
    elif is_frozen():
        path = user_data_dir() / "backups"
    else:
        path = bundle_dir().parent / "backups"

    path.mkdir(parents=True, exist_ok=True)
    return path


def hybrid_runtime_dir() -> Path:
    """Runtime directory for HybridEngine radar/cache/side-car files."""

    path = runtime_data_dir() / "hybrid"
    path.mkdir(parents=True, exist_ok=True)
    return path


def hybrid_runtime_path(*parts: str) -> Path:

    return hybrid_runtime_dir().joinpath(*parts)


def ensure_runtime_data_dirs() -> None:

    data_dir = runtime_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    for name in _RUNTIME_DATA_SUBDIRS:
        (data_dir / name).mkdir(parents=True, exist_ok=True)

    backups_dir()
