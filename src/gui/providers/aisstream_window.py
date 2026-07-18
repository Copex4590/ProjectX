# ============================================================================
# Project X
# AISStream Provider Window
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)

from ais.user_provider_service import save_aisstream_configuration
from gui.providers.provider_window import ProviderWindow
from gui.theme import dashboard_button_stylesheet, dashboard_caption_stylesheet
from i18n import tr


class AISStreamWindow(ProviderWindow):
    def __init__(self, provider_id: str, parent=None):
        self._api_key_input = QLineEdit()
        self._toggle_visibility_button = QPushButton()
        super().__init__(provider_id, parent)

    def provider_icon(self) -> str:

        return "📡"

    def provider_title_key(self) -> str:

        return "AISStream"

    def _build_configuration_fields(self, form: QFormLayout) -> None:

        self._api_key_label = QLabel()
        self._api_key_label.setStyleSheet(dashboard_caption_stylesheet())

        self._api_key_input.setPlaceholderText(tr("Paste here"))
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self._toggle_visibility_button.setCheckable(True)
        self._toggle_visibility_button.setStyleSheet(dashboard_button_stylesheet())
        self._toggle_visibility_button.clicked.connect(self._toggle_api_key_visibility)

        api_key_row = QWidget()
        api_key_layout = QHBoxLayout(api_key_row)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.setSpacing(8)
        api_key_layout.addWidget(self._api_key_input, 1)
        api_key_layout.addWidget(self._toggle_visibility_button)

        form.addRow(self._api_key_label, api_key_row)
        self._register_configuration_widget(self._api_key_input)

    def refresh_translations(self) -> None:

        self._api_key_label.setText(tr("API Key"))
        self._update_visibility_button_text()
        super().refresh_translations()

    def _toggle_api_key_visibility(self, visible: bool) -> None:

        echo_mode = (
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self._api_key_input.setEchoMode(echo_mode)
        self._update_visibility_button_text()

    def _update_visibility_button_text(self) -> None:

        if self._toggle_visibility_button.isChecked():
            self._toggle_visibility_button.setText(tr("Hide"))
        else:
            self._toggle_visibility_button.setText(tr("Show"))

    def _apply_snapshot(self, snapshot) -> None:

        self._api_key_input.setText(snapshot.api_key)

    def _collect_configuration(self) -> bool:

        api_key = self._api_key_input.text().strip()

        if not api_key:
            QMessageBox.warning(
                self,
                tr("AIS Providers"),
                tr("AISStream requires an API key."),
            )
            return False

        save_aisstream_configuration(api_key)
        return True
