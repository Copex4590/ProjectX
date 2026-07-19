# ============================================================================
# Project X
# Global notification manager
# ============================================================================

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication

from gui.notifications.notification_banner import NotificationBanner
from gui.notifications.severity import NotificationSeverity


@dataclass
class NotificationItem:
    message: str
    severity: NotificationSeverity
    key: str = field(default_factory=lambda: str(uuid4()))
    duration_ms: int | None = None
    sticky: bool = False
    animate: bool = True


class NotificationManager(QObject):
    """Application-wide notification queue with a single always-on-top banner."""

    _instance: NotificationManager | None = None

    def __init__(self):
        super().__init__()

        self._banner = NotificationBanner()
        self._queue: deque[NotificationItem] = deque()
        self._current: NotificationItem | None = None
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_current)
        self._is_animating_out = False
        self._shutdown = False

    @classmethod
    def instance(cls) -> NotificationManager:

        if cls._instance is None:
            cls._instance = NotificationManager()

        return cls._instance

    def show(
        self,
        message: str,
        *,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        key: str | None = None,
        duration_ms: int | None = None,
        sticky: bool = False,
        animate: bool = True,
    ) -> str:

        if self._shutdown:
            return key or ""

        item = NotificationItem(
            message=message,
            severity=severity,
            key=key or str(uuid4()),
            duration_ms=duration_ms,
            sticky=sticky,
            animate=animate,
        )

        if self._current is not None and self._current.key == item.key:
            self._apply_item(item, animate=item.animate and not self._banner.isHidden())
            return item.key

        if self._current is None and not self._is_animating_out:
            self._apply_item(item, animate=item.animate)
            return item.key

        self._queue = deque(
            existing for existing in self._queue if existing.key != item.key
        )
        self._queue.append(item)
        return item.key

    def update(
        self,
        key: str,
        message: str,
        *,
        severity: NotificationSeverity | None = None,
    ) -> None:

        if self._shutdown:
            return

        if self._current is not None and self._current.key == key:
            self._current.message = message

            if severity is not None:
                self._current.severity = severity

            self._banner.set_message(message, self._current.severity)
            self._banner.reposition()
            return

        for item in self._queue:
            if item.key == key:
                item.message = message

                if severity is not None:
                    item.severity = severity

                return

    def dismiss(self, key: str) -> None:

        if self._shutdown:
            return

        self._queue = deque(item for item in self._queue if item.key != key)

        if self._current is not None and self._current.key == key:
            self._hide_current(force=True)

    def clear_all(self) -> None:

        if self._shutdown:
            return

        self._hide_timer.stop()
        self._queue.clear()
        self._current = None
        self._is_animating_out = False
        self._banner.close_immediately()

    def shutdown(self) -> None:
        """Tear down all notification UI before application exit."""

        if self._shutdown:
            return

        self._shutdown = True
        self._hide_timer.stop()
        self._queue.clear()
        self._current = None
        self._is_animating_out = False
        self._banner.destroy_immediately()

        app = QApplication.instance()

        if app is not None:
            app.processEvents()

    def _apply_item(self, item: NotificationItem, *, animate: bool) -> None:

        if self._shutdown:
            return

        self._hide_timer.stop()
        self._current = item
        self._banner.set_message(item.message, item.severity)

        if animate:
            self._banner.animate_in()
        else:
            self._banner.reposition()
            self._banner.show()
            self._banner.raise_()
            self._banner.setWindowOpacity(1.0)

        if item.duration_ms is not None and not item.sticky:
            self._hide_timer.start(item.duration_ms)

    def _hide_current(self, *, force: bool = False) -> None:

        if self._shutdown:
            return

        if self._current is None:
            self._show_next()
            return

        if self._current.sticky and not force:
            return

        self._hide_timer.stop()
        self._current = None
        self._is_animating_out = False

        if force:
            self._banner.close_immediately()
            self._show_next()
            return

        self._is_animating_out = True

        def _finish_hide() -> None:
            self._is_animating_out = False
            self._banner.hide()
            self._show_next()

        self._banner.animate_out(finished=_finish_hide)

    def _show_next(self) -> None:

        if self._current is not None or self._is_animating_out:
            return

        if not self._queue:
            return

        item = self._queue.popleft()
        self._apply_item(item, animate=True)


def notification_manager() -> NotificationManager:

    return NotificationManager.instance()
