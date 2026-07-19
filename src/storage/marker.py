# ============================================================================
# Project X
# Data Root Marker (.projectx-data-root)
# ============================================================================

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from storage.layout import DATA_ROOT_MARKER_NAME, DATA_ROOT_MARKER_SCHEMA

_PRODUCT_NAME = "Project X"


def marker_path(data_root: Path) -> Path:
    """Return the marker file path for a data root directory."""

    return Path(data_root) / DATA_ROOT_MARKER_NAME


def build_marker_payload(*, created: datetime | None = None) -> dict:
    """Build a new marker payload."""

    timestamp = created or datetime.now(timezone.utc)
    return {
        "product": _PRODUCT_NAME,
        "schema": DATA_ROOT_MARKER_SCHEMA,
        "created": timestamp.isoformat(),
        "uuid": str(uuid4()),
    }


def read_marker(data_root: Path) -> dict | None:
    """Read and parse the data-root marker, if present."""

    path = marker_path(data_root)

    if not path.is_file():
        return None

    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def is_valid_marker_payload(payload: dict | None) -> bool:
    """Return True when payload identifies a Project X data root."""

    if not isinstance(payload, dict):
        return False

    if payload.get("product") != _PRODUCT_NAME:
        return False

    try:
        schema = int(payload.get("schema", 0))
    except (TypeError, ValueError):
        return False

    return schema >= 1


def is_valid_data_root(data_root: Path) -> bool:
    """Return True when the directory contains a valid Project X marker."""

    return is_valid_marker_payload(read_marker(data_root))


def ensure_marker(data_root: Path) -> Path:
    """Create the marker file when missing and return its path."""

    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)

    path = marker_path(root)

    if path.is_file():
        payload = read_marker(root)

        if is_valid_marker_payload(payload):
            return path

    payload = build_marker_payload()

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    return path
