# ============================================================================
# Project X — Map Core constants
# ============================================================================

from __future__ import annotations

from enum import Enum

# Stack index of the central geographic workspace page in MainWindow.pages.
MAP_PAGE_INDEX = 1


class PickMode(str, Enum):

    NONE = "none"
    LOCATION = "location"
    HEADING = "heading"
