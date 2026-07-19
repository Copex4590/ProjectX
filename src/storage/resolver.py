# ============================================================================
# Project X
# Storage Resolver (configured root + legacy fallback)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from storage.exceptions import InvalidDataDirectoryError
from storage.layout import (
    DATA_SUBDIR_CACHE,
    DATA_SUBDIR_CONFIG,
    DATA_SUBDIR_DATABASES,
    DATA_SUBDIR_EXPORTS,
    DATA_SUBDIR_LOGS,
    STANDARD_DATA_SUBDIRS,
)
from storage.legacy import (
    ensure_legacy_data_layout,
    legacy_data_exists,
    legacy_path_for_subdir,
)
from storage.manager import configured_data_root, ensure_data_layout
from storage.marker import find_marked_data_root, is_valid_data_root, require_marked_data_root


class StorageMode(str, Enum):
    CONFIGURED = "configured"
    LEGACY = "legacy"


@dataclass(frozen=True)
class ResolvedDataRoot:
    """Active Project X data root selected for runtime path resolution."""

    path: Path
    mode: StorageMode
    has_marker: bool


def resolve_data_root() -> ResolvedDataRoot:
    """Return the active data root, preferring a marked configured location."""

    configured = configured_data_root()

    if configured is not None:
        if not is_valid_data_root(configured):
            raise InvalidDataDirectoryError(
                "Configured Project X data directory is missing a valid "
                f".projectx-data-root marker: {configured}"
            )

        return ResolvedDataRoot(
            path=configured,
            mode=StorageMode.CONFIGURED,
            has_marker=True,
        )

    legacy_root = ensure_legacy_data_layout()

    return ResolvedDataRoot(
        path=legacy_root,
        mode=StorageMode.LEGACY,
        has_marker=is_valid_data_root(legacy_root),
    )


def requires_data_root_setup() -> bool:
    """Return True when no configured data root exists and no legacy data is present."""

    if configured_data_root() is not None:
        return False

    return not legacy_data_exists()


def active_data_path(subdir: str, *parts: str) -> Path:
    """Resolve a writable path under the active storage layout."""

    if subdir not in STANDARD_DATA_SUBDIRS:
        raise ValueError(f"Unknown data subdirectory: {subdir}")

    resolved = resolve_data_root()

    if resolved.mode is StorageMode.CONFIGURED:
        return resolved.path.joinpath(subdir, *parts)

    return legacy_path_for_subdir(subdir, *parts)


def active_database_path(filename: str) -> Path:
    """Resolve a writable SQLite database path under the active storage layout."""

    return active_data_path(DATA_SUBDIR_DATABASES, filename)


def active_config_path(*parts: str) -> Path:
    """Resolve a writable configuration path under the active storage layout."""

    return active_data_path(DATA_SUBDIR_CONFIG, *parts)


def active_cache_path(*parts: str) -> Path:
    """Resolve a writable cache path under the active storage layout."""

    return active_data_path(DATA_SUBDIR_CACHE, *parts)


def active_export_path(*parts: str) -> Path:
    """Resolve a writable export path under the active storage layout."""

    return active_data_path(DATA_SUBDIR_EXPORTS, *parts)


def active_log_path(*parts: str) -> Path:
    """Resolve a writable log path under the active storage layout."""

    return active_data_path(DATA_SUBDIR_LOGS, *parts)


def ensure_active_layout() -> Path:
    """Ensure the active storage layout exists for the current runtime mode."""

    configured = configured_data_root()

    if configured is not None:
        return ensure_data_layout(configured)

    return ensure_legacy_data_layout()


def assert_marker_authority(path: Path) -> Path:
    """Require that destructive operations target a marked Project X data root."""

    return require_marked_data_root(path)


def marked_data_root_for(path: Path) -> Path | None:
    """Return the marked data root containing path, if any."""

    return find_marked_data_root(path)
