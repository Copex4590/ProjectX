# ============================================================================
# Project X
# Deferred Storage Path Resolution
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path


def _env_override_path(env_var: str) -> Path | None:
    override = os.environ.get(env_var, "").strip()

    if not override:
        return None

    return Path(override).expanduser().resolve()


def deferred_config_path(env_var: str, *parts: str) -> Path:
    """Resolve a config path when called, not at module import time."""

    override = _env_override_path(env_var)

    if override is not None:
        return override

    from storage import active_config_path

    return active_config_path(*parts)


def deferred_database_path(env_var: str, filename: str) -> Path:
    """Resolve a database path when called, not at module import time."""

    override = _env_override_path(env_var)

    if override is not None:
        return override

    from storage import active_database_path

    return active_database_path(filename)


def deferred_cache_path(env_var: str, *parts: str) -> Path:
    """Resolve a cache path when called, not at module import time."""

    override = _env_override_path(env_var)

    if override is not None:
        return override

    from storage import active_cache_path

    return active_cache_path(*parts)


def deferred_log_path(env_var: str, *parts: str) -> Path:
    """Resolve a log path when called, not at module import time."""

    override = _env_override_path(env_var)

    if override is not None:
        return override

    from storage import active_log_path

    return active_log_path(*parts)
