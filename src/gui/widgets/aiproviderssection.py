# ============================================================================
# Project X
# AIS Providers Section
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ais.ais_manager import ais_manager
from ais.providers import AISProviderType, normalize_provider_type
from core.logger import logger
from gui.aiswizard import AISWizard
from gui.i18n_support import bind_language_refresh
from gui.providers import open_provider_window
from gui.theme import (
    DASHBOARD_BUTTON_ROW_SPACING,
    DASHBOARD_CARD_PADDING,
    DASHBOARD_LIST_SPACING,
    DASHBOARD_SECTION_SPACING,
    dashboard_button_stylesheet,
    dashboard_caption_stylesheet,
    dashboard_card_stylesheet,
    dashboard_provider_header_stylesheet,
    dashboard_value_stylesheet,
)
from i18n import tr
from preferences import preferences_manager
from rtl import rtl_manager

_CARD_STYLE = dashboard_card_stylesheet()
_BUTTON_STYLE = dashboard_button_stylesheet()

_PROVIDER_LABEL_KEYS = {
    AISProviderType.AISSTREAM.value: "AISStream",
    AISProviderType.LOCAL.value: "RTL-SDR",
    AISProviderType.MARINE_TRAFFIC.value: "MarineTraffic",
    AISProviderType.AISHUB.value: "AISHub",
}

_PROVIDER_DISPLAY_ORDER = (
    AISProviderType.AISSTREAM,
    AISProviderType.LOCAL,
    AISProviderType.MARINE_TRAFFIC,
    AISProviderType.AISHUB,
)


def _is_provider_configured(provider: AISProviderType) -> bool:

    preferences = preferences_manager.get()

    if provider == AISProviderType.AISSTREAM:
        return bool(preferences.aisstream_api_key.strip())

    if provider == AISProviderType.LOCAL:
        return bool(preferences.rtl_sdr_configured)

    if provider in (AISProviderType.MARINE_TRAFFIC, AISProviderType.AISHUB):
        return False

    return False


def _user_added_provider_ids() -> list[str]:

    preferences = preferences_manager.get()
    enabled_values = preferences.ais_enabled_providers

    if enabled_values is not None:
        return [str(value).strip() for value in enabled_values if str(value).strip()]

    provider = normalize_provider_type(preferences.ais_provider)

    if provider == AISProviderType.LATER:
        return []

    if provider == AISProviderType.HYBRID:
        return [
            AISProviderType.AISSTREAM.value,
            AISProviderType.LOCAL.value,
        ]

    return [provider.value]


class _ProviderRow(QFrame):
    def __init__(
        self,
        provider_id: str,
        *,
        parent=None,
    ):
        super().__init__(parent)

        self._provider_id = provider_id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DASHBOARD_BUTTON_ROW_SPACING)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(4)

        self._name_label = QLabel()
        self._name_label.setStyleSheet(dashboard_value_stylesheet())
        info.addWidget(self._name_label)

        self._status_label = QLabel()
        self._status_label.setStyleSheet(dashboard_caption_stylesheet())
        info.addWidget(self._status_label)

        layout.addLayout(info, 1)

        self._open_button = QPushButton()
        self._open_button.setStyleSheet(_BUTTON_STYLE)
        self._open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_button.clicked.connect(self._on_open)
        layout.addWidget(self._open_button)

        self.refresh()

    def refresh(self) -> None:

        provider = normalize_provider_type(self._provider_id)
        label_key = _PROVIDER_LABEL_KEYS.get(provider.value, provider.value)
        icon, status_text = _provider_status(self._provider_id)

        self._name_label.setText(f"{icon}   {tr(label_key)}")
        self._status_label.setText(status_text)
        self._open_button.setText(tr("Open"))

    def _on_open(self) -> None:

        open_provider_window(self._provider_id, self.window())


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
        self._header_button.setChecked(True)
        self._header_button.setStyleSheet(dashboard_provider_header_stylesheet())
        self._header_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_button.clicked.connect(self._on_toggle)
        layout.addWidget(self._header_button)

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(DASHBOARD_LIST_SPACING)

        self._empty_state = QWidget()
        empty_layout = QVBoxLayout(self._empty_state)
        empty_layout.setContentsMargins(0, 4, 0, 8)
        empty_layout.setSpacing(6)

        self._empty_primary_label = QLabel()
        self._empty_primary_label.setWordWrap(True)
        self._empty_primary_label.setStyleSheet(dashboard_caption_stylesheet())
        empty_layout.addWidget(self._empty_primary_label)

        self._empty_hint_label = QLabel()
        self._empty_hint_label.setWordWrap(True)
        self._empty_hint_label.setStyleSheet(dashboard_caption_stylesheet())
        empty_layout.addWidget(self._empty_hint_label)

        content_layout.addWidget(self._empty_state)

        self._provider_list = QVBoxLayout()
        self._provider_list.setSpacing(DASHBOARD_LIST_SPACING)
        content_layout.addLayout(self._provider_list)

        self._add_provider_button = QPushButton()
        self._add_provider_button.setStyleSheet(_BUTTON_STYLE)
        self._add_provider_button.setEnabled(True)
        self._add_provider_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_provider_button.clicked.connect(self._on_add_provider)
        content_layout.addWidget(self._add_provider_button)

        self._content.setVisible(True)
        layout.addWidget(self._content)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh()

    def refresh_translations(self) -> None:

        self._update_header_text()
        self._empty_primary_label.setText(tr("No AIS providers added."))
        self._empty_hint_label.setText(
            tr('To get started, choose "+ New provider...".')
        )
        self._add_provider_button.setText(tr("+ New provider..."))
        self.refresh()

    def refresh(self) -> None:

        self._rebuild_provider_list(_user_added_provider_ids())

    def _update_header_text(self) -> None:

        icon = "▼" if self._header_button.isChecked() else "▶"
        self._header_button.setText(f"{icon}   {tr('AIS Providers')}")

    def _on_toggle(self, checked: bool) -> None:

        self._content.setVisible(checked)
        self._update_header_text()

    def _rebuild_provider_list(self, provider_ids: list[str]) -> None:

        while self._provider_list.count():
            item = self._provider_list.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        ordered_ids = _ordered_provider_ids(provider_ids)
        has_providers = bool(ordered_ids)

        self._empty_state.setVisible(not has_providers)
        self._add_provider_button.setVisible(True)
        self._add_provider_button.setEnabled(True)

        for provider_id in ordered_ids:
            row = _ProviderRow(provider_id)
            self._provider_list.addWidget(row)

    def _on_add_provider(self) -> None:

        logger.info("New Provider Wizard requested")

        parent = self.window()
        wizard = AISWizard(parent)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            return

        self.refresh()


def _ordered_provider_ids(provider_ids: list[str]) -> list[str]:

    normalized = {
        normalize_provider_type(provider_id).value
        for provider_id in provider_ids
    }

    ordered: list[str] = []

    for provider in _PROVIDER_DISPLAY_ORDER:
        if provider.value in normalized:
            ordered.append(provider.value)

    for provider_id in provider_ids:
        normalized_id = normalize_provider_type(provider_id).value

        if normalized_id not in ordered:
            ordered.append(normalized_id)

    return ordered


def _provider_connection_status(provider_id: str) -> str:

    provider = normalize_provider_type(provider_id)

    if provider == AISProviderType.AISSTREAM:
        return ais_manager.ais_connection_status()

    if provider == AISProviderType.LOCAL:
        return rtl_manager.rtl_connection_status()

    return "offline"


def _provider_status(provider_id: str) -> tuple[str, str]:

    provider = normalize_provider_type(provider_id)

    if not _is_provider_configured(provider):
        icon = "⚪" if provider == AISProviderType.LOCAL else "🟡"
        return icon, tr("Not configured")

    if _provider_connection_status(provider_id) == "connected":
        return "🟢", tr("Connected")

    return "⚪", tr("Not configured")
