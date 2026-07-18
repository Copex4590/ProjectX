# ============================================================================
# Project X
# Generic AIS Provider Window
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel

from gui.providers.provider_window import ProviderWindow
from gui.theme import dashboard_caption_stylesheet, dashboard_value_stylesheet
from i18n import tr


class GenericProviderWindow(ProviderWindow):
    def provider_icon(self) -> str:

        return "📡"

    def provider_title_key(self) -> str:

        from ais.user_provider_service import provider_label_key

        return provider_label_key(self._provider_id)

    def _build_configuration_fields(self, form: QFormLayout) -> None:

        caption = QLabel(tr("Status"))
        caption.setStyleSheet(dashboard_caption_stylesheet())
        self._status_value = QLabel(tr("Not configured"))
        self._status_value.setStyleSheet(dashboard_value_stylesheet())
        self._status_value.setWordWrap(True)
        form.addRow(caption, self._status_value)

        self._save_button.setVisible(False)

    def _apply_snapshot(self, snapshot) -> None:

        configured_text = tr("Configured") if snapshot.configured else tr("Not configured")
        self._status_value.setText(configured_text)

    def _collect_configuration(self) -> bool:

        return False
