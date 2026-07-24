# ============================================================================
# Project X
# Window Geometry Manager (SAVE-221 / SAVE-222)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QApplication, QWidget

_STARTUP_WORK_AREA_FRACTION = 0.9


@dataclass(frozen=True)
class WindowManagementSettings:
    """User-configurable window management options (preferences)."""

    start_maximized: bool = False
    restore_last: bool = True
    auto_fit: bool = True
    always_center: bool = False
    limit_to_monitor: bool = True
    saved_geometry: dict[str, int] | None = None


@dataclass(frozen=True)
class StartupWindowPlan:
    """Resolved MainWindow startup action."""

    maximized: bool
    geometry: QRect | None


class WindowGeometryManager:
    """Single place for monitor-aware window geometry calculations."""

    def available_work_area(
        self,
        widget: QWidget | None = None,
        *,
        hint: QRect | None = None,
    ) -> QRect | None:
        """
        Return the usable work area for the relevant screen.

        Prefer the screen that contains *hint*'s center (multi-monitor restore),
        then the widget's screen, then the primary screen.
        """

        app = QApplication.instance()
        if app is None:
            return None

        screen = None
        if hint is not None and not hint.isNull():
            screen = app.screenAt(hint.center())

        if screen is None and widget is not None:
            screen = widget.screen()

        if screen is None:
            screen = app.primaryScreen()

        if screen is None:
            return None

        return screen.availableGeometry()

    def plan_startup(
        self,
        settings: WindowManagementSettings,
        widget: QWidget | None = None,
    ) -> StartupWindowPlan:
        """
        Resolve startup geometry from preferences.

        Priority:
        1. Start maximized → maximized (ignore normal geometry)
        2. Else restore / fit / fallback 90% / center per options
        """

        if settings.start_maximized:
            return StartupWindowPlan(maximized=True, geometry=None)

        restored = (
            parse_window_geometry(settings.saved_geometry)
            if settings.restore_last
            else None
        )
        available = self.available_work_area(widget, hint=restored)
        if available is None:
            return StartupWindowPlan(maximized=False, geometry=None)

        geometry = restored

        if geometry is not None and settings.auto_fit:
            geometry = self.fit_to_work_area(geometry, available)

        if geometry is None or not self._is_usable_on(geometry, available):
            geometry = self.default_startup_geometry(available)

        if settings.limit_to_monitor:
            geometry = self.limit_to_work_area(geometry, available)

        # Hard safety: never open outside / larger than the work area.
        geometry = self.fit_to_work_area(geometry, available)

        if settings.always_center:
            geometry = self.center_on_work_area(geometry, available)
            geometry = self.fit_to_work_area(geometry, available)

        return StartupWindowPlan(maximized=False, geometry=geometry)

    def geometry_for_persist(
        self,
        widget: QWidget,
        *,
        limit_to_monitor: bool = True,
    ) -> dict[str, int]:
        """Serialize normalGeometry(), clamped to the current monitor when configured."""

        geometry = widget.normalGeometry()
        available = self.available_work_area(widget, hint=geometry)

        if available is not None:
            if limit_to_monitor or not self._is_usable_on(geometry, available):
                geometry = self.fit_to_work_area(geometry, available)

        return window_geometry_to_dict(geometry)

    def default_startup_geometry(self, available: QRect) -> QRect:
        """≈90% of the work area, centered."""

        width = max(1, int(available.width() * _STARTUP_WORK_AREA_FRACTION))
        height = max(1, int(available.height() * _STARTUP_WORK_AREA_FRACTION))
        return self._centered_rect(QSize(width, height), available)

    def fit_to_work_area(self, rect: QRect, available: QRect) -> QRect:
        """
        Clamp *rect* into *available*.

        Completely off-screen geometry becomes the default centered size.
        Oversized windows are shrunk; positions are clamped into the work area.
        """

        if available.width() <= 0 or available.height() <= 0:
            return QRect(rect)

        width = min(max(1, rect.width()), available.width())
        height = min(max(1, rect.height()), available.height())
        candidate = QRect(rect.x(), rect.y(), width, height)

        if not available.intersects(candidate):
            return self.default_startup_geometry(available)

        return self._clamp_position(candidate, available)

    def limit_to_work_area(self, rect: QRect, available: QRect) -> QRect:
        """Ensure width/height never exceed the work area; keep position when possible."""

        if available.width() <= 0 or available.height() <= 0:
            return QRect(rect)

        width = min(max(1, rect.width()), available.width())
        height = min(max(1, rect.height()), available.height())
        return self._clamp_position(QRect(rect.x(), rect.y(), width, height), available)

    def center_on_work_area(self, rect: QRect, available: QRect) -> QRect:
        """Keep size; move so the window is centered in the work area."""

        size = QSize(
            min(max(1, rect.width()), available.width()),
            min(max(1, rect.height()), available.height()),
        )
        return self._centered_rect(size, available)

    @staticmethod
    def _centered_rect(size: QSize, available: QRect) -> QRect:
        x = available.x() + (available.width() - size.width()) // 2
        y = available.y() + (available.height() - size.height()) // 2
        return QRect(QPoint(x, y), size)

    @staticmethod
    def _clamp_position(rect: QRect, available: QRect) -> QRect:
        max_x = available.x() + available.width() - rect.width()
        max_y = available.y() + available.height() - rect.height()
        x = min(max(rect.x(), available.x()), max_x)
        y = min(max(rect.y(), available.y()), max_y)
        return QRect(x, y, rect.width(), rect.height())

    @staticmethod
    def _is_usable_on(rect: QRect, available: QRect) -> bool:
        if rect.width() <= 0 or rect.height() <= 0:
            return False
        if not available.intersects(rect):
            return False
        # Treat as unusable when almost nothing is visible on this work area.
        intersection = available.intersected(rect)
        min_visible_w = max(1, int(available.width() * 0.05))
        min_visible_h = max(1, int(available.height() * 0.05))
        return (
            intersection.width() >= min_visible_w
            and intersection.height() >= min_visible_h
        )


window_geometry_manager = WindowGeometryManager()


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


# Backwards-compatible aliases (SAVE-221 call sites / tests)
def available_work_area(widget: QWidget | None = None) -> QRect | None:
    return window_geometry_manager.available_work_area(widget)


def default_startup_geometry(available: QRect) -> QRect:
    return window_geometry_manager.default_startup_geometry(available)


def ensure_visible_on_work_area(rect: QRect, available: QRect) -> QRect:
    return window_geometry_manager.fit_to_work_area(rect, available)
