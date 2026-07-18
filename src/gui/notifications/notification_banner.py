# ============================================================================
# Project X
# Global notification banner widget
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout

from gui.notifications.severity import NotificationSeverity
from gui.theme import (
    ACCENT,
    DANGER,
    SUCCESS,
    TEXT,
    WARNING,
)

_SEVERITY_STYLES = {
    NotificationSeverity.INFO: (ACCENT, TEXT),
    NotificationSeverity.SUCCESS: (SUCCESS, "#1b2e1c"),
    NotificationSeverity.WARNING: (WARNING, "#2e2418"),
    NotificationSeverity.ERROR: (DANGER, "#2e1818"),
}


class NotificationBanner(QFrame):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )

        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setWindowOpacity(0.0)

        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.addWidget(self._message_label)

        self._slide_animation: QPropertyAnimation | None = None
        self._fade_animation: QPropertyAnimation | None = None

        self.hide()

    def set_message(self, message: str, severity: NotificationSeverity) -> None:

        accent, background = _SEVERITY_STYLES[severity]
        self._message_label.setText(message)
        self._message_label.setStyleSheet(
            f"color: {TEXT}; font-size: 11pt; font-weight: 600;"
        )
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {background};
                border: 1px solid {accent};
                border-radius: 10px;
            }}
            """
        )

    def reposition(self) -> None:

        screen = QApplication.primaryScreen()

        if screen is None:
            return

        available = screen.availableGeometry()
        width = min(720, max(320, available.width() - 48))
        self.setFixedWidth(width)
        self.adjustSize()

        x = available.x() + (available.width() - width) // 2
        y = available.y() + 16
        self.move(x, y)

    def animate_in(self, finished=None) -> None:

        self.reposition()
        self.show()
        self.raise_()

        start_y = self.y() - self.height() - 12
        end_y = self.y()
        self.move(self.x(), start_y)

        self._stop_animations()

        self._slide_animation = QPropertyAnimation(self, b"pos")
        self._slide_animation.setDuration(280)
        self._slide_animation.setStartValue(self.pos())
        self._slide_animation.setEndValue(self.pos().__class__(self.x(), end_y))
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(280)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        if finished is not None:
            self._fade_animation.finished.connect(finished)

        self._slide_animation.start()
        self._fade_animation.start()

    def animate_out(self, finished=None) -> None:

        self._stop_animations()

        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(220)
        self._fade_animation.setStartValue(self.windowOpacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)

        end_y = self.y() - 12
        self._slide_animation = QPropertyAnimation(self, b"pos")
        self._slide_animation.setDuration(220)
        self._slide_animation.setStartValue(self.pos())
        self._slide_animation.setEndValue(self.pos().__class__(self.x(), end_y))
        self._slide_animation.setEasingCurve(QEasingCurve.Type.InCubic)

        if finished is not None:
            self._fade_animation.finished.connect(finished)

        self._slide_animation.start()
        self._fade_animation.start()

    def _stop_animations(self) -> None:

        for animation in (self._slide_animation, self._fade_animation):
            if animation is not None and animation.state() == animation.State.Running:
                animation.stop()
