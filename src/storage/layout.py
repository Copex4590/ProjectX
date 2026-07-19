# ============================================================================
# Project X
# User Data Layout Constants
# ============================================================================

from __future__ import annotations

DATA_ROOT_MARKER_NAME = ".projectx-data-root"
DATA_ROOT_MARKER_SCHEMA = 1

DATA_SUBDIR_HAJOK = "Hajók"
DATA_SUBDIR_LOGS = "Logs"
DATA_SUBDIR_CACHE = "Cache"
DATA_SUBDIR_EXPORTS = "Exports"
DATA_SUBDIR_CONFIG = "config"
DATA_SUBDIR_DATABASES = "databases"

STANDARD_DATA_SUBDIRS = (
    DATA_SUBDIR_HAJOK,
    DATA_SUBDIR_LOGS,
    DATA_SUBDIR_CACHE,
    DATA_SUBDIR_EXPORTS,
    DATA_SUBDIR_CONFIG,
    DATA_SUBDIR_DATABASES,
)

DEFAULT_DATA_DIRECTORY_NAME = "Project X"
