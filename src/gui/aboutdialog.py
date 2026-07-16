# ============================================================================
# Project X
# About Dialog
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from branding.assets import logo_pixmap
from gui.i18n_support import bind_language_refresh
from gui.theme import (
    ACCENT_GLOW,
    BG_PANEL,
    TEXT_MUTED,
)
from i18n import tr
from version import GITHUB_URL, LICENSE_NAME, PROJECT_BUILD, PROJECT_NAME, PROJECT_VERSION


class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._logo_label)

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet(
            "font-size: 20pt; font-weight: bold; color: white;"
        )
        layout.addWidget(self._title_label)

        self._version_label = QLabel()
        self._version_label.setAlignment(Qt.AlignCenter)
        self._version_label.setStyleSheet(f"color: {TEXT_MUTED};")
        layout.addWidget(self._version_label)

        self._build_label = QLabel()
        self._build_label.setAlignment(Qt.AlignCenter)
        self._build_label.setStyleSheet(f"color: {TEXT_MUTED};")
        layout.addWidget(self._build_label)

        self._github_label = QLabel()
        self._github_label.setAlignment(Qt.AlignCenter)
        self._github_label.setOpenExternalLinks(True)
        self._github_label.setStyleSheet(f"color: {ACCENT_GLOW};")
        layout.addWidget(self._github_label)

        self._license_label = QLabel()
        self._license_label.setAlignment(Qt.AlignCenter)
        self._license_label.setStyleSheet(f"color: {TEXT_MUTED};")
        layout.addWidget(self._license_label)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
        )
        layout.addWidget(self._button_box)
        self._button_box.accepted.connect(self.accept)

        self.setStyleSheet(f"""
            QDialog {{
                background: {BG_PANEL};
            }}
        """)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        pixmap = logo_pixmap(128)

        if pixmap.isNull():
            self._logo_label.clear()
        else:
            self._logo_label.setPixmap(pixmap)

        self.setWindowTitle(tr("About Project X"))
        self._title_label.setText(PROJECT_NAME)
        self._version_label.setText(
            f"{tr('Version')} {PROJECT_VERSION}"
        )
        self._build_label.setText(
            f"{tr('Build')} {PROJECT_BUILD}"
        )

        if GITHUB_URL:
            self._github_label.setText(
                f'<a href="{GITHUB_URL}">{GITHUB_URL}</a>'
            )
            self._github_label.setVisible(True)
        else:
            self._github_label.setVisible(False)

        self._license_label.setText(
            f"{tr('License')}: {LICENSE_NAME}"
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            tr("OK")
        )
