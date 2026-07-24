# ============================================================================
# Project X
# Window Geometry Manager (SAVE-221 / SAVE-222)
# ============================================================================
#
# Startup order (mandatory):
#   1. Detect the current monitor (Qt QScreen)
#   2. Read QScreen.availableGeometry()
#   3. Read stored window geometry from preferences
#   4. Validate stored geometry against that work area
#   5. Apply Window Management behaviour options
#   6. Caller shows the window
#
# Monitor detection is never optional and never user-selected.

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QCursor, QGuiApplication, QScreen
from PySide6.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)

_STARTUP_WORK_AREA_FRACTION = 0.9


@dataclass(frozen=True)
class WindowManagementSettings:
    """Behaviour options applied AFTER the current monitor is detected."""

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
    work_area: QRect | None
    screen_name: str = ""


class WindowGeometryManager:
    """Monitor-aware window geometry — detection first, preferences second."""

    def detect_current_screen(self, widget: QWidget | None = None) -> QScreen | None:
        """
        Always detect the monitor the user is currently on.

        Order: screen under the cursor → widget screen → primary screen.
        """

        app = QGuiApplication.instance()
        if app is None:
            app = QApplication.instance()
        if app is None:
            return None

        screen = app.screenAt(QCursor.pos())
        if screen is None and widget is not None:
            screen = widget.screen()
        if screen is None:
            screen = app.primaryScreen()
        return screen

    def current_work_area(self, widget: QWidget | None = None) -> QRect | None:
        """Mandatory runtime call: QScreen.availableGeometry() for the current monitor."""

        screen = self.detect_current_screen(widget)
        if screen is None:
            logger.warning("No Qt screen available for window geometry")
            return None

        work_area = QRect(screen.availableGeometry())
        logger.debug(
            "Current monitor work area: screen=%r geometry=%s",
            screen.name(),
            work_area,
        )
        return work_area

    def plan_startup(
        self,
        settings: WindowManagementSettings,
        widget: QWidget | None = None,
    ) -> StartupWindowPlan:
        """
        Required startup flow:

        1. Detect current monitor
        2. Read availableGeometry()
        3. Read stored window geometry
        4. Validate against the detected monitor
        5. Apply Window Management options
        """

        # 1–2. Always detect monitor + read availableGeometry() (never optional).
        screen = self.detect_current_screen(widget)
        if screen is None:
            logger.warning("Startup geometry: no current monitor detected")
            return StartupWindowPlan(
                maximized=bool(settings.start_maximized),
                geometry=None,
                work_area=None,
            )

        work_area = QRect(screen.availableGeometry())
        screen_name = str(screen.name() or "")
        logger.info(
            "Startup monitor detected: %s availableGeometry=%s",
            screen_name or "<unnamed>",
            work_area.getRect(),
        )

        # 3. Always read stored geometry (restore option decides whether to use it).
        stored = parse_window_geometry(settings.saved_geometry)

        # 4. Validate stored geometry against the detected monitor work area.
        validated = None
        if stored is not None:
            validated = self.validate_against_work_area(stored, work_area)

        # 5. Apply Window Management behaviour options.
        if settings.start_maximized:
            # Still keep a valid normal geometry under the maximized state.
            fallback = validated or self.default_startup_geometry(work_area)
            fallback = self.limit_to_work_area(fallback, work_area)
            return StartupWindowPlan(
                maximized=True,
                geometry=fallback,
                work_area=work_area,
                screen_name=screen_name,
            )

        geometry: QRect | None = None
        if settings.restore_last and validated is not None:
            geometry = QRect(validated)

        if geometry is not None and settings.auto_fit:
            geometry = self.fit_to_work_area(geometry, work_area)

        if geometry is None or not self._is_usable_on(geometry, work_area):
            geometry = self.default_startup_geometry(work_area)

        if settings.limit_to_monitor:
            geometry = self.limit_to_work_area(geometry, work_area)

        # Absolute safety on the detected monitor (always).
        geometry = self.fit_to_work_area(geometry, work_area)

        if settings.always_center:
            geometry = self.center_on_work_area(geometry, work_area)
            geometry = self.fit_to_work_area(geometry, work_area)

        return StartupWindowPlan(
            maximized=False,
            geometry=geometry,
            work_area=work_area,
            screen_name=screen_name,
        )

    def validate_against_work_area(self, rect: QRect, work_area: QRect) -> QRect | None:
        """
        Validate stored geometry against the current monitor.

        Returns a corrected rect, or None when the geometry is unusable and
        the caller should fall back to the default ~90% layout.
        """

        if work_area.width() <= 0 or work_area.height() <= 0:
            return None
        if rect.width() <= 0 or rect.height() <= 0:
            return None

        corrected = self.fit_to_work_area(rect, work_area)
        if not self._is_usable_on(corrected, work_area):
            return None
        return corrected

    def geometry_for_persist(
        self,
        widget: QWidget,
        *,
        limit_to_monitor: bool = True,
    ) -> dict[str, int]:
        """Serialize normalGeometry() against the current monitor work area."""

        geometry = widget.normalGeometry()
        work_area = self.current_work_area(widget)

        if work_area is not None:
            if limit_to_monitor or not self._is_usable_on(geometry, work_area):
                geometry = self.fit_to_work_area(geometry, work_area)

        return window_geometry_to_dict(geometry)

    def default_startup_geometry(self, available: QRect) -> QRect:
        """≈90% of the detected work area, centered."""

        width = max(1, int(available.width() * _STARTUP_WORK_AREA_FRACTION))
        height = max(1, int(available.height() * _STARTUP_WORK_AREA_FRACTION))
        return self._centered_rect(QSize(width, height), available)

    def fit_to_work_area(self, rect: QRect, available: QRect) -> QRect:
        """Clamp *rect* into *available* (size + position)."""

        if available.width() <= 0 or available.height() <= 0:
            return QRect(rect)

        width = min(max(1, rect.width()), available.width())
        height = min(max(1, rect.height()), available.height())
        candidate = QRect(rect.x(), rect.y(), width, height)

        if not available.intersects(candidate):
            return self.default_startup_geometry(available)

        return self._clamp_position(candidate, available)

    def limit_to_work_area(self, rect: QRect, available: QRect) -> QRect:
        """Ensure width/height never exceed the work area."""

        if available.width() <= 0 or available.height() <= 0:
            return QRect(rect)

        width = min(max(1, rect.width()), available.width())
        height = min(max(1, rect.height()), available.height())
        return self._clamp_position(QRect(rect.x(), rect.y(), width, height), available)

    def center_on_work_area(self, rect: QRect, available: QRect) -> QRect:
        """Keep size; center on the detected work area."""

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


# Backwards-compatible aliases
def available_work_area(widget: QWidget | None = None) -> QRect | None:
    return window_geometry_manager.current_work_area(widget)


def default_startup_geometry(available: QRect) -> QRect:
    return window_geometry_manager.default_startup_geometry(available)


def ensure_visible_on_work_area(rect: QRect, available: QRect) -> QRect:
    return window_geometry_manager.fit_to_work_area(rect, available)
