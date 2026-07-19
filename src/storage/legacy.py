# ============================================================================
# Project X
# Legacy Storage Locations and Detection
# ============================================================================

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.paths import runtime_config_dir, runtime_data_dir
from storage.layout import (
    DATA_SUBDIR_CACHE,
    DATA_SUBDIR_CONFIG,
    DATA_SUBDIR_DATABASES,
    DATA_SUBDIR_EXPORTS,
    DATA_SUBDIR_HAJOK,
    DATA_SUBDIR_LOGS,
)

_LEGACY_LOGS_DIR_NAME = "Project X"
_LEGACY_DB_NAMES = ("vessels.db", "timeline.db", "alerts.db")
_LEGACY_CACHE_NAMES = ("ship_cache.json", "obs_freeze.trace")
_LEGACY_CACHE_DIRS = ("deli_hajok", "vessel_photos", "exports")
_LEGACY_DATA_SUBDIRS = (DATA_SUBDIR_HAJOK, "vessel_photos")
_LEGACY_CONFIG_NAMES = (
    "observation_points.json",
    "cameras.json",
    "ais_api_key.txt",
    "camera_packs_state.json",
    "playback.json",
)


@dataclass(frozen=True)
class LegacyDataInventory:
    """Pre-flight inventory of legacy user data (used before migration in B4)."""

    data_root: Path
    config_root: Path
    logs_root: Path
    ship_folder_count: int
    database_files: tuple[Path, ...]
    config_files: tuple[Path, ...]
    file_count: int
    total_bytes: int

    def to_dict(self) -> dict:
        return {
            "data_root": str(self.data_root),
            "config_root": str(self.config_root),
            "logs_root": str(self.logs_root),
            "ship_folder_count": self.ship_folder_count,
            "database_files": [str(path) for path in self.database_files],
            "config_files": [str(path) for path in self.config_files],
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
        }


def legacy_data_root() -> Path:
    """Return the pre-107 legacy writable data directory."""

    return runtime_data_dir()


def legacy_config_root() -> Path:
    """Return the pre-107 legacy runtime configuration directory."""

    return runtime_config_dir()


def legacy_logs_dir() -> Path:
    """Return the legacy application log directory without creating it."""

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        return base / _LEGACY_LOGS_DIR_NAME / "logs"

    return Path.home() / ".local" / "share" / _LEGACY_LOGS_DIR_NAME / "logs"


def legacy_logs_root() -> Path:
    """Return the legacy application log directory, creating it when needed."""

    path = legacy_logs_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _count_tree_files(root: Path) -> tuple[int, int]:
    file_count = 0
    total_bytes = 0

    try:
        if not root.exists():
            return file_count, total_bytes
    except OSError:
        return file_count, total_bytes

    try:
        paths = root.rglob("*")
    except OSError:
        return file_count, total_bytes

    for path in paths:
        if not path.is_file():
            continue

        file_count += 1

        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue

    return file_count, total_bytes


def _ship_folder_count(data_root: Path) -> int:
    hajok_dir = data_root / DATA_SUBDIR_HAJOK

    if not hajok_dir.is_dir():
        return 0

    return sum(1 for child in hajok_dir.iterdir() if child.is_dir())


def collect_legacy_inventory() -> LegacyDataInventory:
    """Collect a pre-flight inventory of legacy user data."""

    data_root = legacy_data_root()
    config_root = legacy_config_root()
    logs_root = legacy_logs_dir()

    database_files = tuple(
        sorted(path for name in _LEGACY_DB_NAMES if (path := data_root / name).is_file())
    )
    config_files = tuple(
        sorted(
            path
            for name in _LEGACY_CONFIG_NAMES
            if (path := config_root / name).is_file()
        )
    )

    counted_roots = {data_root, config_root, logs_root}
    file_count = 0
    total_bytes = 0

    for root in counted_roots:
        root_files, root_bytes = _count_tree_files(root)
        file_count += root_files
        total_bytes += root_bytes

    return LegacyDataInventory(
        data_root=data_root,
        config_root=config_root,
        logs_root=logs_root,
        ship_folder_count=_ship_folder_count(data_root),
        database_files=database_files,
        config_files=config_files,
        file_count=file_count,
        total_bytes=total_bytes,
    )


def legacy_data_exists() -> bool:
    """Return True when recognizable legacy Project X user data is present."""

    inventory = collect_legacy_inventory()

    if inventory.ship_folder_count > 0:
        return True

    if inventory.database_files:
        return True

    for name in _LEGACY_CACHE_NAMES:
        if (inventory.data_root / name).is_file():
            return True

    for name in _LEGACY_CACHE_DIRS:
        if (inventory.data_root / name).exists():
            return True

    for config_file in inventory.config_files:
        if config_file.name == "observation_points.json":
            try:
                if config_file.stat().st_size > 2:
                    return True
            except OSError:
                continue
            continue

        if config_file.stat().st_size > 0:
            return True

    return False


def ensure_legacy_data_layout() -> Path:
    """Create legacy runtime directories used before SAVE-107 migration."""

    data_dir = legacy_data_root()
    data_dir.mkdir(parents=True, exist_ok=True)

    for name in _LEGACY_DATA_SUBDIRS:
        (data_dir / name).mkdir(parents=True, exist_ok=True)

    legacy_config_root().mkdir(parents=True, exist_ok=True)
    legacy_logs_root()

    return data_dir


def legacy_path_for_subdir(subdir: str, *parts: str) -> Path:
    """Map a standard data subdirectory to its legacy filesystem location."""

    data_root = legacy_data_root()
    config_root = legacy_config_root()
    logs_root = legacy_logs_dir()

    if subdir == DATA_SUBDIR_HAJOK:
        return data_root.joinpath(subdir, *parts)

    if subdir == DATA_SUBDIR_DATABASES:
        return data_root.joinpath(*parts)

    if subdir == DATA_SUBDIR_CACHE:
        return data_root.joinpath(*parts)

    if subdir == DATA_SUBDIR_EXPORTS:
        return data_root.joinpath("exports", *parts)

    if subdir == DATA_SUBDIR_CONFIG:
        return config_root.joinpath(*parts)

    if subdir == DATA_SUBDIR_LOGS:
        return logs_root.joinpath(*parts)

    return data_root.joinpath(subdir, *parts)
