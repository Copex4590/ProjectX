# ============================================================================
# Project X
# RTL-SDR Diagnostics Dialog
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from gui.i18n_support import bind_language_refresh
from gui.theme import wizard_shell_stylesheet
from i18n import tr
from rtl import rtl_manager


class RTLSdrDiagnosticsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._title_label = QLabel()
        self._title_label.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        layout.addWidget(self._title_label)

        form = QFormLayout()
        self._device_label = QLabel()
        self._catcher_label = QLabel()
        self._tcp_label = QLabel()
        self._signal_label = QLabel()
        self._messages_label = QLabel()
        self._ships_label = QLabel()
        self._last_message_label = QLabel()
        self._last_message_label.setWordWrap(True)

        for label in (
            self._device_label,
            self._catcher_label,
            self._tcp_label,
            self._signal_label,
            self._messages_label,
            self._ships_label,
            self._last_message_label,
        ):
            label.setStyleSheet("color: white;")

        self._device_caption = QLabel()
        self._catcher_caption = QLabel()
        self._tcp_caption = QLabel()
        self._signal_caption = QLabel()
        self._messages_caption = QLabel()
        self._ships_caption = QLabel()
        self._last_message_caption = QLabel()

        form.addRow(self._device_caption, self._device_label)
        form.addRow(self._catcher_caption, self._catcher_label)
        form.addRow(self._tcp_caption, self._tcp_label)
        form.addRow(self._signal_caption, self._signal_label)
        form.addRow(self._messages_caption, self._messages_label)
        form.addRow(self._ships_caption, self._ships_label)
        form.addRow(self._last_message_caption, self._last_message_label)
        layout.addLayout(form)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        layout.addWidget(self._button_box)
        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self.accept)

        self.setStyleSheet(wizard_shell_stylesheet())

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self._refresh_values()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("RTL-SDR Diagnostics"))
        self._title_label.setText(tr("RTL-SDR Diagnostics"))
        self._device_caption.setText(tr("RTL device"))
        self._catcher_caption.setText(tr("AIS-Catcher"))
        self._tcp_caption.setText(tr("TCP connection"))
        self._signal_caption.setText(tr("Signal"))
        self._messages_caption.setText(tr("AIS messages"))
        self._ships_caption.setText(tr("Ships detected"))
        self._last_message_caption.setText(tr("Last message"))
        self._button_box.button(QDialogButtonBox.StandardButton.Close).setText(
            tr("Close")
        )
        self._refresh_values()

    def _refresh_values(self) -> None:

        report = rtl_manager.run_diagnostics()

        if report.device.detected:
            details = ", ".join(
                part
                for part in (
                    report.device.manufacturer,
                    report.device.tuner,
                    report.device.serial,
                )
                if part
            )
            self._device_label.setText(f"✓ {details or tr('Receiver detected')}")
        else:
            self._device_label.setText(f"✗ {tr('Receiver not detected')}")

        catcher_parts = []

        if report.ais_catcher_installed:
            catcher_parts.append(tr("Installed"))
        else:
            catcher_parts.append(tr("Not installed"))

        if report.ais_catcher_running:
            catcher_parts.append(tr("Running"))
        else:
            catcher_parts.append(tr("Stopped"))

        catcher_parts.append(f"{report.host}:{report.port}")
        self._catcher_label.setText(" · ".join(catcher_parts))

        if report.tcp_connected:
            self._tcp_label.setText(f"✓ {tr('Connected')}")
        else:
            self._tcp_label.setText(f"✗ {tr('Disconnected')}")

        quality_labels = {
            "weak": tr("Weak"),
            "fair": tr("Fair"),
            "good": tr("Good"),
            "none": tr("No signal"),
        }
        self._signal_label.setText(
            quality_labels.get(report.signal_quality, tr("No signal"))
        )
        self._messages_label.setText(str(report.message_count))
        self._ships_label.setText(str(report.ships_detected))
        self._last_message_label.setText(report.last_message or "—")

    def showEvent(self, event) -> None:

        super().showEvent(event)
        self._refresh_values()
