# ============================================================================
# Project X
# Storage Manager
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path

from storage.exceptions import (
    DataDirectoryNotConfiguredError,
    DataDirectoryValidationError,
    InvalidDataDirectoryError,
)
from storage.layout import DEFAULT_DATA_DIRECTORY_NAME, STANDARD_DATA_SUBDIRS
from storage.data_root_validation import (
    DataRootValidationResult,
    DataRootValidationService,
)
from storage.marker import ensure_marker, is_valid_data_root

_ENV_DATA_DIRECTORY = "PROJECTX_DATA_DIRECTORY"

DataDirectoryValidationResult = DataRootValidationResult
_default_data_root_validator = DataRootValidationService()


def default_data_directory() -> Path:
    """Recommended default location for new Project X installations."""

    return Path.home() / DEFAULT_DATA_DIRECTORY_NAME


def configured_data_root() -> Path | None:
    """Return the configured data root from env or preferences, if any."""

    env_value = os.environ.get(_ENV_DATA_DIRECTORY, "").strip()

    if env_value:
        return Path(env_value).expanduser().resolve()

    from preferences.preferences_manager import preferences_manager

    preferences = preferences_manager.get()
    configured = (preferences.data_directory or "").strip()

    if not configured:
        return None

    if preferences.storage_activation_deferred_until_restart:
        return None

    return Path(configured).expanduser().resolve()


def data_root() -> Path:
    """Return the configured and validated user data root."""

    root = configured_data_root()

    if root is None:
        raise DataDirectoryNotConfiguredError(
            "Project X user data directory is not configured."
        )

    if not is_valid_data_root(root):
        raise InvalidDataDirectoryError(
            f"Configured data directory is missing a valid marker: {root}"
        )

    return root


def data_subdirectory(name: str) -> Path:
    """Return a standard subdirectory inside the configured data root."""

    if name not in STANDARD_DATA_SUBDIRS:
        raise ValueError(f"Unknown data subdirectory: {name}")

    return data_root() / name


def ensure_data_layout(data_root_path: Path | None = None) -> Path:
    """Create the standard data layout and marker under the given root."""

    root = Path(data_root_path or data_root())
    root.mkdir(parents=True, exist_ok=True)

    for name in STANDARD_DATA_SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)

    ensure_marker(root)
    return root


def ensure_active_storage_layout() -> Path:
    """Ensure the active Project X storage layout exists for the current mode."""

    configured = configured_data_root()

    if configured is not None:
        return ensure_data_layout(configured)

    from storage.resolver import requires_data_root_setup

    if requires_data_root_setup():
        raise DataDirectoryNotConfiguredError(
            "Project X data directory setup is required before storage can be "
            "initialized."
        )

    from storage.legacy import ensure_legacy_data_layout

    return ensure_legacy_data_layout()


def validate_data_directory(
    path: Path,
    *,
    allow_existing_root: bool = False,
) -> DataDirectoryValidationResult:
    """Validate that a candidate path can be used as a Project X data root."""

    return _default_data_root_validator.validate(
        path,
        allow_existing_root=allow_existing_root,
    )


def validate_data_directory_or_raise(
    path: Path,
    *,
    allow_existing_root: bool = False,
) -> Path:
    """Validate a candidate data directory or raise DataDirectoryValidationError."""

    result = validate_data_directory(
        path,
        allow_existing_root=allow_existing_root,
    )

    if result.blocks_completion:
        raise DataDirectoryValidationError(result.message)

    return result.path
