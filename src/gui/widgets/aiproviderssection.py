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
from gui.providers import open_provider_window
from gui.theme import (
    DASHBOARD_CARD_PADDING,
    DASHBOARD_LIST_SPACING,
    DASHBOARD_SECTION_SPACING,
    dashboard_card_stylesheet,
    dashboard_provider_add_stylesheet,
    dashboard_provider_entry_stylesheet,
    dashboard_provider_header_stylesheet,
)
from i18n import tr
from rtl import rtl_manager

_CARD_STYLE = dashboard_card_stylesheet()


class AISProvidersSection(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
        )
        layout.setSpacing(DASHBOARD_SECTION_SPACING)

        self._header_button = QPushButton()
        self._header_button.setCheckable(True)
        self._header_button.setChecked(False)
        self._header_button.setStyleSheet(dashboard_provider_header_stylesheet())
        self._header_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_button.clicked.connect(self._on_toggle)
        layout.addWidget(self._header_button)

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(DASHBOARD_LIST_SPACING)

        self._provider_list = QVBoxLayout()
        self._provider_list.setSpacing(DASHBOARD_LIST_SPACING)
        content_layout.addLayout(self._provider_list)

        self._add_provider_button = QPushButton()
        self._add_provider_button.setStyleSheet(dashboard_provider_add_stylesheet())
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
        self._header_button.setText(f"{icon}   {tr('AIS Providers')}")

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
            button.setStyleSheet(dashboard_provider_entry_stylesheet())
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
        icon = self._status_icon(status)
        return f"{icon}   {tr(provider.label_key)}"

    def _on_provider_clicked(self, provider: ConfiguredProvider) -> None:

        logger.info("Provider clicked: %s", provider.display_name)
        open_provider_window(provider.provider_id, self.window())

    def _on_add_provider(self) -> None:

        logger.info("New Provider Wizard requested")
