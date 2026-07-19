# ============================================================================
# Project X
# Storage Exceptions
# ============================================================================

from __future__ import annotations


class StorageError(Exception):
    """Base class for storage-related errors."""


class DataDirectoryNotConfiguredError(StorageError):
    """Raised when no user data directory has been configured yet."""


class InvalidDataDirectoryError(StorageError):
    """Raised when a path is not a valid Project X data root."""


class DataDirectoryValidationError(StorageError):
    """Raised when a candidate data directory fails validation."""
