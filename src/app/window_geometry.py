# ============================================================================
# Project X
# Main window startup geometry helpers (SAVE-221)
# ============================================================================

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QWidget

_STARTUP_WORK_AREA_FRACTION = 0.9


def available_work_area(widget: QWidget | None = None) -> QRect | None:
    """Return the usable desktop work area for the widget's screen."""

    screen = widget.screen() if widget is not None else None

    if screen is None:
        app = QApplication.instance()
        if app is not None:
            screen = app.primaryScreen()

    if screen is None:
        return None

    return screen.availableGeometry()


def default_startup_geometry(available: QRect) -> QRect:
    """≈90% of the work area, centered."""

    width = max(1, int(available.width() * _STARTUP_WORK_AREA_FRACTION))
    height = max(1, int(available.height() * _STARTUP_WORK_AREA_FRACTION))
    x = available.x() + (available.width() - width) // 2
    y = available.y() + (available.height() - height) // 2
    return QRect(x, y, width, height)


def parse_window_geometry(data: Any) -> QRect | None:
    """Parse a preferences window_geometry dict into a QRect."""

    if not isinstance(data, dict):
        return None

    try:
        x = int(data["x"])
        y = int(data["y"])
        width = int(data["width"])
        height = int(data["height"])
    except (KeyError, TypeError, ValueError):
        return None

    if width <= 0 or height <= 0:
        return None

    return QRect(x, y, width, height)


def window_geometry_to_dict(rect: QRect) -> dict[str, int]:
    return {
        "x": int(rect.x()),
        "y": int(rect.y()),
        "width": int(rect.width()),
        "height": int(rect.height()),
    }


def ensure_visible_on_work_area(rect: QRect, available: QRect) -> QRect:
    """
    Keep *rect* inside *available*.

    Completely off-screen geometry is replaced with the default centered size.
    Oversized windows are shrunk to fit; positions are clamped into the work area.
    """

    if available.width() <= 0 or available.height() <= 0:
        return QRect(rect)

    width = min(max(1, rect.width()), available.width())
    height = min(max(1, rect.height()), available.height())
    candidate = QRect(rect.x(), rect.y(), width, height)

    if not available.intersects(candidate):
        return default_startup_geometry(available)

    max_x = available.x() + available.width() - width
    max_y = available.y() + available.height() - height
    x = min(max(candidate.x(), available.x()), max_x)
    y = min(max(candidate.y(), available.y()), max_y)
    return QRect(x, y, width, height)
