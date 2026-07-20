# ============================================================================
# Project X
# Data Root Initialization Service (SAVE-107-C3)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from storage.data_root_validation import DataRootValidationService
from storage.exceptions import InitializationError
from storage.layout import STANDARD_DATA_SUBDIRS
from storage.marker import ensure_marker, is_valid_data_root
from storage.resolver import StorageMode, resolve_data_root


@dataclass(frozen=True)
class DataRootInitializationResult:
    """Outcome of initializing a new Project X data root."""

    success: bool
    data_root: Path | None = None
    mode: StorageMode | None = None
    message: str = ""


class DataRootInitializationService:
    """Create the configured data layout and persist the chosen data root."""

    def __init__(
        self,
        *,
        validation_service: DataRootValidationService | None = None,
        preferences_manager=None,
    ) -> None:

        self._validation_service = validation_service or DataRootValidationService()

        if preferences_manager is None:
            from preferences.preferences_manager import (
                preferences_manager as default_manager,
            )

            preferences_manager = default_manager

        self._preferences_manager = preferences_manager

    def initialize(self, path: Path) -> DataRootInitializationResult:
        """Validate, create layout/marker, persist preferences, and verify."""

        validation = self._validation_service.validate(path)

        if validation.blocks_completion:
            return DataRootInitializationResult(
                success=False,
                message=validation.message,
            )

        data_root = validation.path.resolve()
        created_root: Path | None = None

        try:
            created_root = _create_data_subdirectory_layout(data_root)
            ensure_marker(created_root)
            self._preferences_manager.set_data_directory(str(created_root))
            _verify_post_initialization(
                expected_root=created_root,
                preferences_manager=self._preferences_manager,
            )
        except InitializationError as exc:
            return DataRootInitializationResult(
                success=False,
                data_root=created_root,
                message=str(exc),
            )

        return DataRootInitializationResult(
            success=True,
            data_root=created_root,
            mode=StorageMode.CONFIGURED,
            message="",
        )


def _create_data_subdirectory_layout(data_root: Path) -> Path:
    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)

    for name in STANDARD_DATA_SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)

    return root.resolve()


def _verify_post_initialization(
    *,
    expected_root: Path,
    preferences_manager,
) -> None:
    expected = expected_root.resolve()

    preferences = preferences_manager.get()
    configured = (preferences.data_directory or "").strip()

    if not configured:
        raise InitializationError(
            "Post-initialization verification failed: "
            "preferences.data_directory is unset."
        )

    configured_path = Path(configured).expanduser().resolve()
    if configured_path != expected:
        raise InitializationError(
            "Post-initialization verification failed: preferences point to "
            f"{configured_path}, expected {expected}."
        )

    if not is_valid_data_root(expected):
        raise InitializationError(
            "Post-initialization verification failed: marker is invalid."
        )

    resolved = resolve_data_root()

    if resolved.path.resolve() != expected:
        raise InitializationError(
            "Post-initialization verification failed: resolved path "
            f"{resolved.path} does not match selected path {expected}."
        )

    if resolved.mode is not StorageMode.CONFIGURED:
        raise InitializationError(
            "Post-initialization verification failed: active storage mode is "
            f"{resolved.mode.value}, expected configured."
        )

    if not resolved.has_marker:
        raise InitializationError(
            "Post-initialization verification failed: resolved data root "
            "does not report a valid marker."
        )
