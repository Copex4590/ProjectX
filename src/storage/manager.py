# ============================================================================
# Project X
# Storage Manager
# ============================================================================

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.paths import bundle_dir, is_frozen
from storage.exceptions import (
    DataDirectoryNotConfiguredError,
    DataDirectoryValidationError,
    InvalidDataDirectoryError,
)
from storage.layout import DEFAULT_DATA_DIRECTORY_NAME, STANDARD_DATA_SUBDIRS
from storage.marker import ensure_marker, is_valid_data_root

_ENV_DATA_DIRECTORY = "PROJECTX_DATA_DIRECTORY"
_FORBIDDEN_PREFIXES = (
    Path("/opt/projectx"),
)


@dataclass(frozen=True)
class DataDirectoryValidationResult:
    """Outcome of validating a candidate user data directory."""

    path: Path
    valid: bool
    message: str = ""


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

    from storage.legacy import ensure_legacy_data_layout

    return ensure_legacy_data_layout()


def _is_forbidden_path(path: Path) -> bool:
    resolved = path.resolve()

    for prefix in _FORBIDDEN_PREFIXES:
        try:
            resolved.relative_to(prefix.resolve())
            return True
        except ValueError:
            continue

    if is_frozen():
        bundle = bundle_dir().resolve()

        try:
            resolved.relative_to(bundle)
            return True
        except ValueError:
            pass

    return False


def validate_data_directory(path: Path) -> DataDirectoryValidationResult:
    """Validate that a candidate path can be used as a Project X data root."""

    candidate = Path(path).expanduser()

    if not str(candidate).strip():
        return DataDirectoryValidationResult(
            path=candidate,
            valid=False,
            message="A folder must be selected.",
        )

    if _is_forbidden_path(candidate):
        return DataDirectoryValidationResult(
            path=candidate,
            valid=False,
            message="Project X cannot store data inside the application install folder.",
        )

    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return DataDirectoryValidationResult(
            path=candidate,
            valid=False,
            message=f"Could not create the selected folder: {exc}",
        )

    resolved = candidate.resolve()

    try:
        with tempfile.NamedTemporaryFile(
            dir=resolved,
            prefix=".projectx-write-test-",
            delete=True,
        ):
            pass
    except OSError as exc:
        return DataDirectoryValidationResult(
            path=resolved,
            valid=False,
            message=f"The selected folder is not writable: {exc}",
        )

    return DataDirectoryValidationResult(
        path=resolved,
        valid=True,
        message="",
    )


def validate_data_directory_or_raise(path: Path) -> Path:
    """Validate a candidate data directory or raise DataDirectoryValidationError."""

    result = validate_data_directory(path)

    if not result.valid:
        raise DataDirectoryValidationError(result.message)

    return result.path
