# ============================================================================
# Project X
# Splash Screen
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen

from branding.assets import logo_pixmap
from i18n import tr
from version import PROJECT_NAME, PROJECT_VERSION


class ProjectXSplashScreen(QSplashScreen):

    def __init__(self):
        super().__init__(self._build_pixmap(), Qt.WindowType.WindowStaysOnTopHint)

    def _build_pixmap(self) -> QPixmap:

        width = 480
        height = 300
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#252a31"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QColor("#40444b"))
        painter.setBrush(QColor("#252a31"))
        painter.drawRoundedRect(1, 1, width - 2, height - 2, 12, 12)

        logo = logo_pixmap(96)

        if not logo.isNull():
            x = (width - logo.width()) // 2
            painter.drawPixmap(x, 36, logo)

        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(0, 150, width, 40, Qt.AlignmentFlag.AlignCenter, PROJECT_NAME)

        version_font = QFont()
        version_font.setPointSize(11)
        painter.setFont(version_font)
        painter.setPen(QColor("#bbbbbb"))
        painter.drawText(
            0,
            188,
            width,
            24,
            Qt.AlignmentFlag.AlignCenter,
            f"{tr('Version')} {PROJECT_VERSION}",
        )

        painter.setPen(QColor("#4FC3F7"))
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
            QColor("#4FC3F7"),
        )


def create_splash_screen() -> ProjectXSplashScreen:

    splash = ProjectXSplashScreen()
    splash.show_loading_message()
    return splash
