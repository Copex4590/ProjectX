"""Resolve the Google Maps JavaScript API key for Map3D.

Priority:
  1. Dev/runtime env override (never logged):
       PROJECTX_GOOGLE_MAPS_API_KEY
       PROJECTX_GOOGLE_MAPS_DEMO_KEY  (legacy alias)
  2. Release-time bundled file (gitignored, injected by build scripts):
       resources/map/google_maps_api_key.bundled

The key must never be written to logs or committed to the source tree.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.paths import resource_path

_BUNDLED_NAME = "google_maps_api_key.bundled"
_ENV_NAMES = (
    "PROJECTX_GOOGLE_MAPS_API_KEY",
    "PROJECTX_GOOGLE_MAPS_DEMO_KEY",
)


def bundled_key_path() -> Path:
    return resource_path("map", _BUNDLED_NAME)


def resolve_google_maps_api_key() -> str:
    for name in _ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value

    path = bundled_key_path()
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def google_maps_key_source() -> str:
    """Return a non-secret label describing where the key came from."""
    for name in _ENV_NAMES:
        if os.environ.get(name, "").strip():
            return f"env:{name}"
    path = bundled_key_path()
    try:
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            return "bundled"
    except OSError:
        pass
    return "none"
