# ============================================================================
# Project X
# MapTiler configuration
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path

from app.paths import bundled_config_dir, is_frozen


def _developer_key_file() -> Path:

    return Path(__file__).resolve().parent / "maptiler_api_key.txt"


def maptiler_api_key() -> str:
    """Return the bundled MapTiler API key for map imagery."""

    env_key = os.environ.get("PROJECTX_MAPTILER_API_KEY", "").strip()
    if env_key:
        return env_key

    bundled_key = bundled_config_dir() / "maptiler_api_key.txt"
    if bundled_key.is_file():
        key = bundled_key.read_text(encoding="utf-8").strip()
        if key:
            return key

    if not is_frozen():
        dev_key = _developer_key_file()
        if dev_key.is_file():
            key = dev_key.read_text(encoding="utf-8").strip()
            if key:
                return key

    raise RuntimeError(
        "MapTiler API key is not configured. "
        "Add src/config/maptiler_api_key.txt or set PROJECTX_MAPTILER_API_KEY."
    )
