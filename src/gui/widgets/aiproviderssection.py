# ============================================================================
# Project X
# AIS Providers Section
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ais.ais_manager import ais_manager
from ais.provider_manager import ConfiguredProvider, provider_manager
from ais.providers import AISProviderType, normalize_provider_type
from core.logger import logger
from gui.i18n_support import bind_language_refresh
from i18n import tr
from rtl import rtl_manager

_CARD_STYLE = """
    QFrame {
        background: #252a31;
        border: 1px solid #3d4a5c;
        border-radius: 10px;
    }
"""

_ENTRY_STYLE = """
    QPushButton {
        background: transparent;
        color: white;
        font-weight: 600;
        text-align: left;
        border: none;
        border-radius: 6px;
        padding: 6px 4px;
    }
    QPushButton:hover {
        background: #2a3548;
    }
"""

_ADD_PROVIDER_STYLE = """
    QPushButton {
        background: transparent;
        color: #9aa4af;
        text-align: left;
        border: none;
        border-radius: 6px;
        padding: 6px 4px;
    }
    QPushButton:hover {
        background: #2a3548;
        color: white;
    }
"""

_HEADER_STYLE = """
    QPushButton {
        background: transparent;
        color: white;
        font-size: 16pt;
        font-weight: bold;
        text-align: left;
        border: none;
        padding: 0;
    }
    QPushButton:hover {
        color: #d5dbe3;
    }
"""


class AISProvidersSection(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._header_button = QPushButton()
        self._header_button.setCheckable(True)
        self._header_button.setChecked(False)
        self._header_button.setStyleSheet(_HEADER_STYLE)
        self._header_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_button.clicked.connect(self._on_toggle)
        layout.addWidget(self._header_button)

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        self._provider_list = QVBoxLayout()
        self._provider_list.setSpacing(4)
        content_layout.addLayout(self._provider_list)

        self._separator = QFrame()
        self._separator.setFrameShape(QFrame.Shape.HLine)
        self._separator.setStyleSheet("color: #3d4a5c;")
        content_layout.addWidget(self._separator)

        self._add_provider_button = QPushButton()
        self._add_provider_button.setStyleSheet(_ADD_PROVIDER_STYLE)
        self._add_provider_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_provider_button.clicked.connect(self._on_add_provider)
        content_layout.addWidget(self._add_provider_button)

        self._content.setVisible(False)
        layout.addWidget(self._content)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh()

    def refresh_translations(self) -> None:

        self._update_header_text()
        self._add_provider_button.setText(tr("➕ New provider..."))
        self.refresh()

    def refresh(self) -> None:

        self._rebuild_provider_list(provider_manager.configured_providers())

    def _update_header_text(self) -> None:

        icon = "▼" if self._header_button.isChecked() else "▶"
        self._header_button.setText(f"{icon} {tr('AIS Providers')}")

    def _on_toggle(self, checked: bool) -> None:

        self._content.setVisible(checked)
        self._update_header_text()

    def _rebuild_provider_list(self, providers: list[ConfiguredProvider]) -> None:

        while self._provider_list.count():
            item = self._provider_list.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        for provider in providers:
            button = QPushButton(self._provider_label(provider))
            button.setStyleSheet(_ENTRY_STYLE)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, item=provider: self._on_provider_clicked(item)
            )
            self._provider_list.addWidget(button)

    @staticmethod
    def _status_icon(status: str) -> str:

        if status == "connected":
            return "🟢"

        return "⚪"

    @staticmethod
    def _provider_connection_status(provider_id: str) -> str:

        provider = normalize_provider_type(provider_id)

        if provider == AISProviderType.AISSTREAM:
            return ais_manager.ais_connection_status()

        if provider == AISProviderType.LOCAL:
            return rtl_manager.rtl_connection_status()

        return "offline"

    def _provider_label(self, provider: ConfiguredProvider) -> str:

        status = self._provider_connection_status(provider.provider_id)
        return f"{self._status_icon(status)} {tr(provider.label_key)}"

    def _on_provider_clicked(self, provider: ConfiguredProvider) -> None:

        logger.info("Provider clicked: %s", provider.display_name)

    def _on_add_provider(self) -> None:

        logger.info("New Provider Wizard requested")
