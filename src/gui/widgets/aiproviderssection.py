# ============================================================================
# Project X
# AIS Providers Section
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ais.providers import normalize_provider_type
from ais.user_provider_service import (
    get_enabled_provider_ids,
    ordered_provider_ids,
    provider_display_status,
    provider_label_key,
)
from core.logger import logger
from gui.aiswizard import AISWizard
from gui.i18n_support import bind_language_refresh
from gui.provider_coverage import (
    default_coverage_provider,
    provider_coverage_url,
)
from gui.providercoveragenoticedialog import ProviderCoverageNoticeDialog
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


_CARD_STYLE = dashboard_card_stylesheet()
_BUTTON_STYLE = dashboard_button_stylesheet()


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

        self._settings_button = QPushButton()
        self._settings_button.setStyleSheet(_BUTTON_STYLE)
        self._settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_button.clicked.connect(self._on_settings)
        layout.addWidget(self._settings_button)

        self.refresh()

    def refresh(self) -> None:

        label_key = provider_label_key(self._provider_id)
        status = provider_display_status(self._provider_id)

        self._name_label.setText(f"{status.icon}   {tr(label_key)}")
        self._status_label.setText(status.text)
        self._settings_button.setText(tr("Settings"))

    def _on_settings(self) -> None:

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
        """Rebuild provider rows (membership / configuration changes)."""

        self._rebuild_provider_list(ordered_provider_ids())

    def refresh_statuses(self) -> None:
        """SAVE-106: update labels/counters without rebuilding widgets."""

        provider_ids = ordered_provider_ids()
        current_ids = [
            self._provider_list.itemAt(index).widget()._provider_id
            for index in range(self._provider_list.count())
            if self._provider_list.itemAt(index) is not None
            and self._provider_list.itemAt(index).widget() is not None
        ]

        if provider_ids != current_ids:
            self._rebuild_provider_list(provider_ids)
            return

        for index in range(self._provider_list.count()):
            item = self._provider_list.itemAt(index)

            if item is None:
                continue

            row = item.widget()

            if row is not None:
                row.refresh()

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

        has_providers = bool(provider_ids)

        self._empty_state.setVisible(not has_providers)
        self._add_provider_button.setVisible(True)
        self._add_provider_button.setEnabled(True)

        for provider_id in provider_ids:
            row = _ProviderRow(provider_id)
            self._provider_list.addWidget(row)

    def _on_add_provider(self) -> None:

        logger.info("New Provider Wizard requested")

        parent = self.window()

        if not self._maybe_show_coverage_notice(parent):
            return

        wizard = AISWizard(parent)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            return

        self.refresh()

    def _maybe_show_coverage_notice(self, parent) -> bool:

        preferences = preferences_manager.get()

        if preferences.ais_provider_coverage_notice_dismissed:
            return True

        provider = _coverage_notice_provider()
        dialog = ProviderCoverageNoticeDialog(parent)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        if dialog.dont_show_again():
            preferences_manager.set_ais_provider_coverage_notice_dismissed(True)

        if dialog.view_coverage_requested():
            coverage_url = provider_coverage_url(provider)

            if coverage_url:
                QDesktopServices.openUrl(QUrl(coverage_url))

            return False

        return True


def _coverage_notice_provider():

    provider_ids = get_enabled_provider_ids()

    if provider_ids:
        return normalize_provider_type(provider_ids[0])

    return default_coverage_provider()
