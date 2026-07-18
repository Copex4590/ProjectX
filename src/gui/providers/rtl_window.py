# ============================================================================
# Project X
# RTL-SDR Provider Window
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ais.user_provider_service import save_local_configuration
from gui.providers.provider_window import ProviderWindow
from gui.theme import TEXT_MUTED, dashboard_caption_stylesheet, dashboard_value_stylesheet
from i18n import tr


class RTLWindow(ProviderWindow):
    def __init__(self, provider_id: str, parent=None):
        self._host_input = QLineEdit()
        self._port_input = QSpinBox()
        self._auto_start_checkbox = QCheckBox()
        self._configured_value = QLabel()
        super().__init__(provider_id, parent)

    def provider_icon(self) -> str:

        return "📻"

    def provider_title_key(self) -> str:

        return "RTL-SDR"

    def _build_configuration_fields(self, form: QFormLayout) -> None:

        self._configured_caption = QLabel()
        self._configured_caption.setStyleSheet(dashboard_caption_stylesheet())
        self._configured_value.setStyleSheet(dashboard_value_stylesheet())
        form.addRow(self._configured_caption, self._configured_value)

        self._host_label = QLabel()
        self._host_label.setStyleSheet(dashboard_caption_stylesheet())
        form.addRow(self._host_label, self._host_input)
        self._register_configuration_widget(self._host_input)

        self._port_label = QLabel()
        self._port_label.setStyleSheet(dashboard_caption_stylesheet())
        self._port_input.setMinimum(1)
        self._port_input.setMaximum(65535)
        form.addRow(self._port_label, self._port_input)
        self._register_configuration_widget(self._port_input)

        self._auto_start_checkbox.setStyleSheet(f"color: {TEXT_MUTED};")
        form.addRow("", self._auto_start_checkbox)
        self._register_configuration_widget(self._auto_start_checkbox)

        self._setup_button = QPushButton()
        self._setup_button.clicked.connect(self._on_run_setup)
        setup_row = QVBoxLayout()
        setup_row.addWidget(self._setup_button)
        form.addRow("", setup_row)

    def refresh_translations(self) -> None:

        self._configured_caption.setText(tr("Receiver setup"))
        self._host_label.setText(tr("Host"))
        self._port_label.setText(tr("Port"))
        self._auto_start_checkbox.setText(tr("Auto-start AIS-Catcher"))
        self._setup_button.setText(tr("Run RTL-SDR Setup"))
        super().refresh_translations()

    def _apply_snapshot(self, snapshot) -> None:

        configured_text = tr("Configured") if snapshot.rtl_configured else tr("Not configured")
        self._configured_value.setText(configured_text)
        self._host_input.setText(snapshot.host)
        self._port_input.setValue(snapshot.port)
        self._auto_start_checkbox.setChecked(snapshot.rtl_auto_start)

    def _collect_configuration(self) -> bool:

        save_local_configuration(
            host=self._host_input.text().strip(),
            port=self._port_input.value(),
            auto_start=self._auto_start_checkbox.isChecked(),
        )
        return True

    def _on_run_setup(self) -> None:

        from gui.rtlsdrwizard import RTLSdrWizard

        RTLSdrWizard(self.window()).exec()
        self._reset_configuration_edited()
        self.refresh_state()
