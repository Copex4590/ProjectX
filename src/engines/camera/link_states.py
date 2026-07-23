# ============================================================================
# Project X
# Camera link states (SAVE-217)
# ============================================================================

from __future__ import annotations

from enum import Enum


class CameraLinkState(str, Enum):
    """Operational / selection state for a linked camera."""

    ONLINE = "Online"
    OFFLINE = "Offline"
    BUSY = "Busy"
    PREFERRED = "Preferred"


class CameraLinkMode(str, Enum):

    AUTO = "Auto"
    MANUAL = "Manual"


EVENT_CAMERA_LINK_CHANGED = "camera.link.changed"
EVENT_CAMERA_LINK_MODE = "camera.link.mode"
EVENT_CAMERA_COVERAGE_TOGGLED = "camera.coverage.toggled"
