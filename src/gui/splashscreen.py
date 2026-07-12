# ============================================================================
# Project X
# Splash Screen
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen

from branding.assets import logo_pixmap
from gui.theme import ACCENT_GLOW, BG_BASE, BORDER, TEXT_MUTED, TEXT_PRIMARY
from i18n import tr
from version import PROJECT_NAME, PROJECT_VERSION


class ProjectXSplashScreen(QSplashScreen):

    def __init__(self):
        super().__init__(self._build_pixmap(), Qt.WindowType.WindowStaysOnTopHint)

    def _build_pixmap(self) -> QPixmap:

        width = 480
        height = 300
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(BG_BASE))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QColor(BORDER))
        painter.setBrush(QColor(BG_BASE))
        painter.drawRoundedRect(1, 1, width - 2, height - 2, 12, 12)

        logo = logo_pixmap(96)

        if not logo.isNull():
            x = (width - logo.width()) // 2
            painter.drawPixmap(x, 36, logo)

        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(0, 150, width, 40, Qt.AlignmentFlag.AlignCenter, PROJECT_NAME)

        version_font = QFont()
        version_font.setPointSize(11)
        painter.setFont(version_font)
        painter.setPen(QColor(TEXT_MUTED))
        painter.drawText(
            0,
            188,
            width,
            24,
            Qt.AlignmentFlag.AlignCenter,
            f"{tr('Version')} {PROJECT_VERSION}",
        )

        painter.setPen(QColor(ACCENT_GLOW))
        painter.drawText(
            0,
            height - 48,
            width,
            24,
            Qt.AlignmentFlag.AlignCenter,
            f"{tr('Loading')}...",
        )

        painter.end()
        return pixmap

    def show_loading_message(self) -> None:

        self.showMessage(
            "",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            QColor(ACCENT_GLOW),
        )


def create_splash_screen() -> ProjectXSplashScreen:

    splash = ProjectXSplashScreen()
    splash.show_loading_message()
    return splash
